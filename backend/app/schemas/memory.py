from pydantic import BaseModel, Field, field_validator


class MemoryNoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, v: str) -> str:
        # Same whitespace-only gap as SearchStreamRequest.prompt (Step 5) —
        # min_length=1 alone lets "   " through.
        if not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v


class MemoryNoteUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v
