from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UploadUrlRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=500)
    content_type: str = Field(min_length=1, max_length=100)


class UploadUrlResponse(BaseModel):
    document_id: UUID
    upload_url: str
    storage_path: str
    expires_in_seconds: int
    required_headers: dict[str, str]


class DocumentResponse(BaseModel):
    id: UUID
    file_name: str
    file_type: str
    file_size: int | None
    status: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    document_id: UUID
    status: str
