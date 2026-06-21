from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import get_embedding_provider


async def ingest_document(
    db: AsyncSession,
    project_id: int,
    title: str,
    content: str,
    source: str = "manual",
    file_name: str | None = None,
    mime_type: str | None = None,
    file_data: bytes | None = None,
) -> Document:
    document = Document(
        project_id=project_id,
        title=title.strip(),
        source=source,
        file_name=file_name,
        mime_type=mime_type,
        content_text=content,
        file_data=file_data,
    )
    db.add(document)
    await db.flush()
    provider = get_embedding_provider()
    for index, chunk in enumerate(chunk_text(content)):
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                embedding=provider.embed(chunk),
            )
        )
    await db.commit()
    await db.refresh(document)
    return document


async def list_documents(db: AsyncSession, project_id: int) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.project_id == project_id).order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, document_id: int) -> Document | None:
    return await db.get(Document, document_id)


async def delete_document(db: AsyncSession, document: Document) -> None:
    await db.delete(document)
    await db.commit()


async def search(
    db: AsyncSession, query: str, project_ids: list[int], k: int = 5
) -> list[dict[str, Any]]:
    if not project_ids:
        return []
    query_vector = get_embedding_provider().embed(query)
    distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
    rows = (
        await db.execute(
            select(DocumentChunk.content, Document.title, Document.project_id, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.project_id.in_(project_ids))
            .order_by(distance)
            .limit(k)
        )
    ).all()
    return [
        {
            "content": content,
            "document_title": title,
            "project_id": project_id,
            "distance": float(dist),
        }
        for (content, title, project_id, dist) in rows
    ]
