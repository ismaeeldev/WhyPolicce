from pydantic import BaseModel, Field, field_validator


class SearchStreamRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    sessionId: str | None = None
    deepSearch: bool = False

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, v: str) -> str:
        # min_length=1 alone lets a whitespace-only string through — the
        # frontend's SearchBar already disables submit for this case, but the
        # backend must not rely on that (found via Step 5's own bug sweep).
        if not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v
