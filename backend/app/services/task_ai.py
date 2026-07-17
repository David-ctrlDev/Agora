"""Propuesta de tareas a partir del levantamiento de requerimientos.

La IA solo propone TÍTULO, DESCRIPCIÓN y PRIORIDAD; el humano decide cuáles
aceptar y luego asigna responsables/fechas (server-authoritative: el modelo no
teclea nombres ni correos). Con GEMINI_PROVIDER=mock se usa una heurística
determinista (sin red) para desarrollo.
"""
import json
import re
from typing import Any

from app.core.config import settings
from app.models.user import User

_PRIORITIES = {"low", "medium", "high"}
_MAX_PROPOSALS = 15
_MAX_TEXT = 24_000  # caracteres de requerimientos enviados al modelo


def _clean(proposals: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(proposals, list):
        return out
    for item in proposals[:_MAX_PROPOSALS]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:300]
        if not title:
            continue
        priority = str(item.get("priority") or "medium").strip().lower()
        out.append(
            {
                "title": title,
                "description": str(item.get("description") or "").strip()[:2000],
                "priority": priority if priority in _PRIORITIES else "medium",
            }
        )
    return out


def _mock_proposals(text: str) -> list[dict[str, str]]:
    """Heurística sin red: una tarea por línea/viñeta significativa."""
    lines = [
        re.sub(r"^[\s\-\*\d\.\)]+", "", line).strip()
        for line in text.splitlines()
    ]
    lines = [line for line in lines if len(line) > 8][:_MAX_PROPOSALS]
    return [
        {
            "title": line[:120],
            "description": "Propuesta generada a partir del levantamiento de requerimientos.",
            "priority": "medium",
        }
        for line in lines
    ]


async def propose_tasks(user: User, project_name: str, text: str) -> list[dict[str, str]]:
    text = (text or "").strip()[:_MAX_TEXT]
    if len(text) < 20:
        raise ValueError("El levantamiento está muy corto para proponer tareas")

    if settings.gemini_provider != "real":
        return _mock_proposals(text)

    import asyncio

    from google.genai import types

    from app.agent.gemini_client import get_gemini_client
    from app.agent.gemini_runner import _record_usage

    prompt = (
        "Eres un PM experto. A partir del siguiente LEVANTAMIENTO DE REQUERIMIENTOS del "
        f"proyecto «{project_name}», propone las tareas de trabajo concretas.\n"
        "Reglas: entre 3 y 15 tareas; títulos cortos y accionables en español; una "
        "descripción de 1-3 frases; prioridad low|medium|high según impacto. NO inventes "
        "responsables ni fechas. Responde SOLO un arreglo JSON de objetos con las claves "
        'exactas: "title", "description", "priority".\n\n'
        f"REQUERIMIENTOS:\n{text}"
    )
    client = get_gemini_client()
    response = await asyncio.to_thread(
        client.models.generate_content,
        model=settings.gemini_chat_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2, response_mime_type="application/json"
        ),
    )
    um = getattr(response, "usage_metadata", None)
    if um is not None:
        await _record_usage(
            user.id,
            settings.gemini_chat_model,
            int(getattr(um, "prompt_token_count", 0) or 0),
            int(getattr(um, "candidates_token_count", 0) or 0),
            int(getattr(um, "total_token_count", 0) or 0),
            thoughts=int(getattr(um, "thoughts_token_count", 0) or 0),
            cached=int(getattr(um, "cached_content_token_count", 0) or 0),
            tool_use=int(getattr(um, "tool_use_prompt_token_count", 0) or 0),
        )
    raw = (response.text or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.S)
        data = json.loads(match.group(0)) if match else []
    proposals = _clean(data)
    if not proposals:
        raise ValueError("El modelo no devolvió tareas utilizables; intenta de nuevo")
    return proposals
