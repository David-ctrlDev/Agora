from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)
    source: str = "manual"


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str
    source: str
    file_name: str | None = None
    mime_type: str | None = None
    created_at: datetime


class DocumentDetail(DocumentRead):
    content_text: str | None = None


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    version_no: int
    title: str
    source: str
    file_name: str | None = None
    mime_type: str | None = None
    created_at: datetime


class SearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class SearchResult(BaseModel):
    content: str
    document_title: str
    project_id: int
    distance: float
