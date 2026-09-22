"""Request/response schemas for app/routers/media.py — forum rebuild,
Milestone 3 Step M3.1 (WhyPoliceForum_MasterGuide.md).
"""

from pydantic import BaseModel, Field

from app.models.evidence_attachment import FileType


class UploadUrlRequest(BaseModel):
    inquiry_id: str
    file_type: FileType
    size_bytes: int = Field(gt=0)
    content_type: str = Field(min_length=1, max_length=200)


class AttachmentCreate(BaseModel):
    file_url: str = Field(min_length=1)
    file_type: FileType
    size_bytes: int = Field(gt=0)
