import re


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """Divide el texto en chunks por párrafos, agrupando hasta `max_chars`."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 1 > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n{paragraph}".strip() if current else paragraph
    if current:
        chunks.append(current)
    if not chunks and text.strip():
        chunks = [text.strip()]
    return chunks
