"""Repos Git internos por proyecto de desarrollo (pestaña Código).

Diseño: un repo BARE por proyecto en `settings.repos_path/{project_id}.git`.
- Lecturas (historial, archivos, diff, ZIP) van directo al bare.
- Escrituras (subida=commit, restauración, merge) usan un CLON temporal local
  (barato en el mismo filesystem) que hace push de vuelta; así el repo central
  nunca queda en estados intermedios.
- Concurrencia: lock asyncio por proyecto (un solo proceso de backend).
- Todas las operaciones son "sin comandos" para el usuario: los conceptos se
  traducen (borrador=rama, publicar=merge, restaurar=commit que revierte).
"""
import asyncio
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.project import Project
from app.models.user import User

DEFAULT_BRANCH = "main"


class CodeRepoError(Exception):
    """Error de operación sobre el repo (mensaje apto para el usuario)."""


class NoChanges(CodeRepoError):
    pass


class BranchExists(CodeRepoError):
    pass


class BranchNotFound(CodeRepoError):
    pass


class MergeConflicts(Exception):
    """El merge tiene conflictos; el usuario debe resolver por archivo."""

    def __init__(self, files: list[str]):
        self.files = files
        super().__init__("merge con conflictos")


# ─────────────────────────── infraestructura ───────────────────────────

_locks: dict[int, asyncio.Lock] = {}


def _lock(project_id: int) -> asyncio.Lock:
    if project_id not in _locks:
        _locks[project_id] = asyncio.Lock()
    return _locks[project_id]


def _repo_path(project_id: int) -> Path:
    return Path(settings.repos_path) / f"{project_id}.git"


def _run(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    """Ejecuta git y devuelve stdout; en error levanta CodeRepoError con el stderr."""
    import os

    full_env = dict(os.environ)
    # Identidad por defecto (los commits reales la sobreescriben con el usuario).
    full_env.setdefault("GIT_AUTHOR_NAME", "Ágora")
    full_env.setdefault("GIT_AUTHOR_EMAIL", "agora@invesa.local")
    full_env.setdefault("GIT_COMMITTER_NAME", "Ágora")
    full_env.setdefault("GIT_COMMITTER_EMAIL", "agora@invesa.local")
    if env:
        full_env.update(env)
    result = subprocess.run(
        ["git", *args], cwd=cwd, env=full_env, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise CodeRepoError((result.stderr or result.stdout or "error de git").strip()[:500])
    return result.stdout


def _run_bytes(args: list[str], cwd: Path) -> bytes:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if result.returncode != 0:
        raise CodeRepoError((result.stderr.decode(errors="ignore") or "error de git").strip()[:500])
    return result.stdout


def _author_env(user: User) -> dict[str, str]:
    name = (user.name or "").strip() or f"Usuario {user.id}"
    email = (user.email or "").strip() or f"user{user.id}@invesa.local"
    return {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
    }


def _ensure_repo_sync(project_id: int) -> Path:
    path = _repo_path(project_id)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        _run(["init", "--bare", "-b", DEFAULT_BRANCH, str(path)])
    return path


def _has_commits(bare: Path, branch: str = DEFAULT_BRANCH) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=bare,
        capture_output=True,
    )
    return result.returncode == 0


def _clone(bare: Path, branch: str, tmp: Path) -> Path:
    """Clona el bare y deja el worktree en `branch` (creándola local si el repo está vacío)."""
    work = tmp / "work"
    _run(["clone", "--quiet", str(bare), str(work)])
    if _has_commits(bare, branch):
        _run(["checkout", "--quiet", "-B", branch, f"origin/{branch}"], cwd=work)
    elif branch == DEFAULT_BRANCH:
        _run(["checkout", "--quiet", "-b", branch], cwd=work)
    else:
        raise BranchNotFound(f"el borrador «{branch}» no existe")
    return work


# ─────────────────────────── validaciones ───────────────────────────

_SECRET_EXTS = {".pem", ".key", ".p12", ".pfx", ".ppk"}
_SECRET_NAMES = {"credentials.json", "service-account.json", "secrets.json", "secret.json"}


def _is_secret(path: str) -> bool:
    base = path.rsplit("/", 1)[-1].lower()
    if base == ".env" or (base.startswith(".env.") and not base.endswith(".example")):
        return True
    if any(base.endswith(ext) for ext in _SECRET_EXTS):
        return True
    if base.startswith(("id_rsa", "id_ed25519", "id_ecdsa", "id_dsa")):
        return True
    return base in _SECRET_NAMES


def _safe_rel_path(name: str) -> str:
    """Normaliza una ruta relativa subida y rechaza rutas peligrosas."""
    path = (name or "").replace("\\", "/").strip().lstrip("/")
    while path.startswith("./"):
        path = path[2:]
    if not path or path.endswith("/"):
        raise CodeRepoError(f"nombre de archivo inválido: «{name}»")
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise CodeRepoError(f"ruta no permitida: «{name}»")
    if parts[0] == ".git" or ":" in path or "\x00" in path:
        raise CodeRepoError(f"ruta no permitida: «{name}»")
    return path


def validate_files(files: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Sanea rutas y aplica guardas de secretos y tamaño. Devuelve (ruta_limpia, data)."""
    if not files:
        raise CodeRepoError("no llegó ningún archivo")
    max_file = settings.code_max_file_mb * 1024 * 1024
    max_batch = settings.code_max_batch_mb * 1024 * 1024
    cleaned: list[tuple[str, bytes]] = []
    secrets_found: list[str] = []
    total = 0
    for name, data in files:
        path = _safe_rel_path(name)
        if _is_secret(path):
            secrets_found.append(path)
            continue
        if len(data) > max_file:
            raise CodeRepoError(
                f"«{path}» pesa más de {settings.code_max_file_mb} MB (límite por archivo)"
            )
        total += len(data)
        cleaned.append((path, data))
    if secrets_found:
        raise CodeRepoError(
            "por seguridad no se suben archivos con secretos o llaves: "
            + ", ".join(secrets_found[:5])
            + ". Sácalos de la carpeta (o usa un .env.example sin valores reales)."
        )
    if total > max_batch:
        raise CodeRepoError(f"la subida supera {settings.code_max_batch_mb} MB en total")
    if not cleaned:
        raise CodeRepoError("no quedó ningún archivo válido para subir")
    return cleaned


# ─────────────────────────── lecturas ───────────────────────────

def _log_entries(bare: Path, branch: str, limit: int) -> list[dict[str, Any]]:
    if not _has_commits(bare, branch):
        return []
    out = _run(
        ["log", branch, f"-n{limit}", "--format=%H%x1f%an%x1f%aI%x1f%s%x1e"], cwd=bare
    )
    entries: list[dict[str, Any]] = []
    for chunk in out.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        commit_hash, author, date, subject = chunk.split("\x1f", 3)
        entries.append(
            {
                "hash": commit_hash,
                "short": commit_hash[:7],
                "author": author,
                "date": date,
                "message": subject,
            }
        )
    # Archivos tocados por commit (una pasada).
    files_out = _run(
        ["log", branch, f"-n{limit}", "--format=%x01%H", "--name-only"], cwd=bare
    )
    files_map: dict[str, list[str]] = {}
    current: str | None = None
    for line in files_out.splitlines():
        if line.startswith("\x01"):
            current = line[1:].strip()
            files_map[current] = []
        elif line.strip() and current:
            files_map[current].append(line.strip())
    for entry in entries:
        entry["files"] = files_map.get(entry["hash"], [])
    return entries


async def history(project_id: int, branch: str = DEFAULT_BRANCH, limit: int = 30) -> list[dict]:
    bare = _repo_path(project_id)
    if not bare.exists():
        return []
    return await asyncio.to_thread(_log_entries, bare, branch, limit)


async def commit_detail(project_id: int, ref: str) -> list[dict[str, str]]:
    """Archivos cambiados por un commit (status + ruta)."""
    bare = _repo_path(project_id)

    def _detail() -> list[dict[str, str]]:
        out = _run(["show", "--name-status", "--format=", ref], cwd=bare)
        rows = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                rows.append({"status": parts[0][:1], "path": parts[-1]})
        return rows

    return await asyncio.to_thread(_detail)


async def archive_zip(project_id: int, ref: str) -> bytes:
    bare = _repo_path(project_id)
    return await asyncio.to_thread(_run_bytes, ["archive", "--format=zip", ref], bare)


def _branch_rows(bare: Path) -> list[dict[str, Any]]:
    if not bare.exists() or not _has_commits(bare, DEFAULT_BRANCH):
        return []
    out = _run(
        [
            "for-each-ref",
            "refs/heads",
            "--format=%(refname:short)%1f%(objectname:short)%1f%(authorname)%1f%(committerdate:iso8601-strict)%1f%(subject)".replace(
                "%1f", "\x1f"
            ),
        ],
        cwd=bare,
    )
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        name, short, author, date, subject = line.split("\x1f", 4)
        row: dict[str, Any] = {
            "name": name,
            "is_default": name == DEFAULT_BRANCH,
            "last": {"short": short, "author": author, "date": date, "message": subject},
            "ahead": 0,
        }
        if name != DEFAULT_BRANCH:
            counts = _run(
                ["rev-list", "--left-right", "--count", f"{DEFAULT_BRANCH}...{name}"], cwd=bare
            ).split()
            if len(counts) == 2:
                row["ahead"] = int(counts[1])  # commits del borrador que main no tiene
        rows.append(row)
    rows.sort(key=lambda r: (not r["is_default"], r["name"]))
    return rows


async def status(project_id: int) -> dict[str, Any]:
    bare = _repo_path(project_id)
    initialized = bare.exists() and _has_commits(bare)
    branches = await asyncio.to_thread(_branch_rows, bare) if initialized else []
    return {
        "initialized": initialized,
        "default_branch": DEFAULT_BRANCH,
        "branches": branches,
    }


# ─────────────────────────── escrituras ───────────────────────────

async def commit_upload(
    project: Project,
    user: User,
    files: list[tuple[str, bytes]],
    message: str,
    branch: str = DEFAULT_BRANCH,
) -> dict[str, Any]:
    """Sube archivos como UN commit (autor = usuario de Ágora) en la rama dada."""
    cleaned = validate_files(files)
    message = (message or "").strip() or f"Actualización de {len(cleaned)} archivo(s)"

    def _do() -> dict[str, Any]:
        bare = _ensure_repo_sync(project.id)
        with tempfile.TemporaryDirectory(prefix="agora-git-") as tmp:
            work = _clone(bare, branch, Path(tmp))
            for rel, data in cleaned:
                dest = work / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            _run(["add", "--", *[rel for rel, _ in cleaned]], cwd=work)
            porcelain = _run(["status", "--porcelain"], cwd=work)
            if not porcelain.strip():
                raise NoChanges("los archivos subidos son idénticos a los actuales")
            _run(["commit", "-m", message], cwd=work, env=_author_env(user))
            _run(["push", "--quiet", "origin", f"HEAD:refs/heads/{branch}"], cwd=work)
            entries = _log_entries(bare, branch, 1)
            return entries[0] if entries else {}

    async with _lock(project.id):
        return await asyncio.to_thread(_do)


async def restore(
    project: Project, user: User, target: str, branch: str = DEFAULT_BRANCH
) -> dict[str, Any]:
    """Vuelve al estado de `target` creando un commit NUEVO (la historia no se toca)."""

    def _do() -> dict[str, Any]:
        bare = _repo_path(project.id)
        if not bare.exists() or not _has_commits(bare, branch):
            raise CodeRepoError("este proyecto aún no tiene versiones")
        short = _run(["rev-parse", "--short", target], cwd=bare).strip()
        with tempfile.TemporaryDirectory(prefix="agora-git-") as tmp:
            work = _clone(bare, branch, Path(tmp))
            _run(["rm", "-r", "-q", "--ignore-unmatch", "--", "."], cwd=work)
            _run(["checkout", target, "--", "."], cwd=work)
            porcelain = _run(["status", "--porcelain"], cwd=work)
            if not porcelain.strip():
                raise NoChanges("ya estás exactamente en esa versión")
            _run(
                ["commit", "-m", f"Restauración de la versión {short}"],
                cwd=work,
                env=_author_env(user),
            )
            _run(["push", "--quiet", "origin", f"HEAD:refs/heads/{branch}"], cwd=work)
            entries = _log_entries(bare, branch, 1)
            return entries[0] if entries else {}

    async with _lock(project.id):
        return await asyncio.to_thread(_do)


# ─────────────────────────── .gitignore asistido ───────────────────────────

GITIGNORE_CATEGORIES: list[dict[str, Any]] = [
    {
        "id": "secretos",
        "title": "Secretos y credenciales",
        "description": "Contraseñas, llaves y archivos .env. NUNCA deben subirse a un repositorio.",
        "patterns": [".env", ".env.*", "!.env.example", "*.pem", "*.key", "*.p12", "id_rsa*"],
        "recommended": True,
    },
    {
        "id": "dependencias",
        "title": "Dependencias",
        "description": "Librerías que se reinstalan solas (node_modules, venv…). Pesan mucho y no aportan.",
        "patterns": ["node_modules/", "venv/", ".venv/", "__pycache__/", "vendor/"],
        "recommended": True,
    },
    {
        "id": "compilados",
        "title": "Archivos compilados",
        "description": "Resultados de compilar o empaquetar (dist, build…). Se regeneran desde el código.",
        "patterns": ["dist/", "build/", "out/", "*.pyc", "*.class", "*.o"],
        "recommended": True,
    },
    {
        "id": "sistema",
        "title": "Basura del sistema",
        "description": "Archivos que crean Windows y macOS solos; no son parte del proyecto.",
        "patterns": [".DS_Store", "Thumbs.db", "desktop.ini"],
        "recommended": True,
    },
    {
        "id": "logs",
        "title": "Registros (logs)",
        "description": "Archivos de log que crecen sin parar; no sirven en el historial.",
        "patterns": ["*.log", "logs/"],
        "recommended": False,
    },
    {
        "id": "editor",
        "title": "Configuración del editor",
        "description": "Preferencias personales de VS Code u otros editores; cada quien tiene la suya.",
        "patterns": [".vscode/", ".idea/", "*.swp"],
        "recommended": False,
    },
]

_MARK_START = "# >>> agora:{id}"
_MARK_END = "# <<< agora:{id}"


def _build_gitignore(category_ids: list[str], extra: str) -> str:
    lines = ["# Generado desde Ágora (pestaña Código). Edita con el asistente.", ""]
    for cat in GITIGNORE_CATEGORIES:
        if cat["id"] not in category_ids:
            continue
        lines.append(_MARK_START.format(id=cat["id"]) + f" — {cat['title']}")
        lines.extend(cat["patterns"])
        lines.append(_MARK_END.format(id=cat["id"]))
        lines.append("")
    extra = (extra or "").strip()
    if extra:
        lines.append(_MARK_START.format(id="extra") + " — Reglas propias")
        lines.extend(extra.splitlines())
        lines.append(_MARK_END.format(id="extra"))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


async def get_gitignore(project_id: int, branch: str = DEFAULT_BRANCH) -> dict[str, Any]:
    bare = _repo_path(project_id)
    content = ""
    if bare.exists() and _has_commits(bare, branch):
        try:
            content = await asyncio.to_thread(
                _run, ["show", f"{branch}:.gitignore"], bare
            )
        except CodeRepoError:
            content = ""
    active = set(re.findall(r"# >>> agora:(\w+)", content))
    extra_match = re.search(
        r"# >>> agora:extra[^\n]*\n(.*?)# <<< agora:extra", content, re.S
    )
    return {
        "content": content,
        "active": [c for c in active if c != "extra"],
        "extra": (extra_match.group(1).strip() if extra_match else ""),
        "categories": GITIGNORE_CATEGORIES,
    }


async def set_gitignore(
    project: Project, user: User, category_ids: list[str], extra: str
) -> dict[str, Any]:
    content = _build_gitignore(category_ids, extra)
    return await commit_upload(
        project,
        user,
        [(".gitignore", content.encode())],
        "Actualización de archivos ignorados (.gitignore)",
    )


# ─────────────────────────── borradores (ramas) ───────────────────────────

def _slug_branch(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:40]
    if not slug:
        raise CodeRepoError("dale un nombre al borrador")
    if slug == DEFAULT_BRANCH:
        raise CodeRepoError("ese nombre está reservado")
    return slug


async def create_branch(project: Project, name: str) -> dict[str, Any]:
    branch = _slug_branch(name)

    def _do() -> dict[str, Any]:
        bare = _repo_path(project.id)
        if not bare.exists() or not _has_commits(bare):
            raise CodeRepoError("sube primero una versión inicial para poder crear borradores")
        exists = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=bare,
            capture_output=True,
        )
        if exists.returncode == 0:
            raise BranchExists(f"ya existe un borrador llamado «{branch}»")
        _run(["branch", branch, DEFAULT_BRANCH], cwd=bare)
        return {"name": branch}

    async with _lock(project.id):
        return await asyncio.to_thread(_do)


async def delete_branch(project: Project, branch: str) -> None:
    if branch == DEFAULT_BRANCH:
        raise CodeRepoError("la línea oficial no se puede eliminar")

    def _do() -> None:
        bare = _repo_path(project.id)
        _run(["branch", "-D", branch], cwd=bare)

    async with _lock(project.id):
        await asyncio.to_thread(_do)


_MAX_DIFF_CHARS = 20_000
_MAX_DIFF_FILES = 200


async def diff_vs_main(project_id: int, branch: str) -> dict[str, Any]:
    """Qué trae el borrador respecto a la línea oficial (archivos + diffs de texto)."""
    bare = _repo_path(project_id)

    def _do() -> dict[str, Any]:
        if not _has_commits(bare, branch):
            raise BranchNotFound(f"el borrador «{branch}» no existe")
        rng = f"{DEFAULT_BRANCH}...{branch}"
        names = _run(["diff", "--name-status", rng], cwd=bare)
        files = []
        for line in names.splitlines()[:_MAX_DIFF_FILES]:
            parts = line.split("\t")
            if len(parts) >= 2:
                files.append({"status": parts[0][:1], "path": parts[-1]})
        # Binarios: numstat marca "-\t-\truta".
        numstat = _run(["diff", "--numstat", rng], cwd=bare)
        binary = {
            line.split("\t")[-1]
            for line in numstat.splitlines()
            if line.startswith("-\t-\t")
        }
        diffs: dict[str, str] = {}
        for f in files:
            if f["path"] in binary:
                continue
            text = _run(["diff", rng, "--", f["path"]], cwd=bare)
            if text:
                diffs[f["path"]] = text[:_MAX_DIFF_CHARS]
        return {"files": files, "diffs": diffs, "binary": sorted(binary)}

    return await asyncio.to_thread(_do)


async def merge_branch(
    project: Project,
    user: User,
    branch: str,
    message: str | None = None,
    resolutions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Publica el borrador en la línea oficial. Si hay conflictos y no llegan
    resoluciones completas (ruta -> 'draft'|'main'), levanta MergeConflicts."""
    if branch == DEFAULT_BRANCH:
        raise CodeRepoError("ese ya es la línea oficial")
    msg = (message or "").strip() or f"Publicación del borrador «{branch}»"
    res = resolutions or {}

    def _do() -> dict[str, Any]:
        bare = _repo_path(project.id)
        if not _has_commits(bare, branch):
            raise BranchNotFound(f"el borrador «{branch}» no existe")
        with tempfile.TemporaryDirectory(prefix="agora-git-") as tmp:
            work = _clone(bare, DEFAULT_BRANCH, Path(tmp))
            merge = subprocess.run(
                ["git", "merge", "--no-ff", f"origin/{branch}", "-m", msg],
                cwd=work,
                capture_output=True,
                text=True,
                env={**__import__("os").environ, **_author_env(user)},
            )
            if merge.returncode != 0:
                conflicted = [
                    line.strip()
                    for line in _run(
                        ["diff", "--name-only", "--diff-filter=U"], cwd=work
                    ).splitlines()
                    if line.strip()
                ]
                if not conflicted:
                    raise CodeRepoError((merge.stderr or merge.stdout).strip()[:400])
                missing = [p for p in conflicted if res.get(p) not in ("draft", "main")]
                if missing:
                    _run(["merge", "--abort"], cwd=work)
                    raise MergeConflicts(conflicted)
                for path, choice in res.items():
                    if path not in conflicted:
                        continue
                    side = "--theirs" if choice == "draft" else "--ours"
                    try:
                        _run(["checkout", side, "--", path], cwd=work)
                        _run(["add", "--", path], cwd=work)
                    except CodeRepoError:
                        # Conflicto de borrado (el lado elegido no tiene el archivo).
                        _run(["rm", "--ignore-unmatch", "--", path], cwd=work)
                _run(["commit", "--no-edit", "-m", msg], cwd=work, env=_author_env(user))
            _run(["push", "--quiet", "origin", f"HEAD:refs/heads/{DEFAULT_BRANCH}"], cwd=work)
        _run(["branch", "-D", branch], cwd=bare)  # borrador publicado => desaparece
        entries = _log_entries(bare, DEFAULT_BRANCH, 1)
        return entries[0] if entries else {}

    async with _lock(project.id):
        return await asyncio.to_thread(_do)


async def ensure_repo(project_id: int) -> None:
    await asyncio.to_thread(_ensure_repo_sync, project_id)


def repo_exists(project_id: int) -> bool:
    return _repo_path(project_id).exists()


def remove_repo(project_id: int) -> None:
    """Borra el repo del disco (al eliminar el proyecto)."""
    path = _repo_path(project_id)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
