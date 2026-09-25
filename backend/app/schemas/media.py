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
    # Display-only — never used to build the storage path (see
    # generate_upload_url's own comment on why that's always a random
    # UUID). Optional so an older client that hasn't been redeployed yet
    # still works; the UI falls back to the UUID when absent.
    original_filename: str | None = Field(default=None, max_length=255)
