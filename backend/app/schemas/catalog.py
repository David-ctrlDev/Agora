from pydantic import BaseModel, ConfigDict, Field

CATALOG_KINDS = ("process", "category", "project_type", "initiative")


class CatalogTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    name: str
    is_active: bool


class CatalogTermCreate(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=120)
