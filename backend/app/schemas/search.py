from pydantic import BaseModel, Field, field_validator


class SearchStreamRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    sessionId: str | None = None
    deepSearch: bool = False
    # State Selector, Step 4 (real client-requested feature — their own
    # pasted request body already included this exact field name: `state:
    # params.state`). Optional, defaults to None (existing callers/tests
    # that don't send it are unaffected) — a real 2-letter USPS code,
    # validated against vector_search_service's own real supported-state
    # list (not just "looks like 2 letters") so an invalid/unsupported
    # code fails loudly at the API boundary rather than silently doing
    # nothing useful three layers deeper in retrieval.
    state: str | None = Field(default=None, max_length=2)

    @field_validator("state")
    @classmethod
    def state_must_be_supported(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Imported inside the validator, not at module level — avoids a
        # real circular-import risk (vector_search_service doesn't import
        # this schemas module, but keeping schema validation logic from
        # depending on service-layer internals at import time is the
        # safer default for a schemas/ module).
        from app.services.vector_search_service import CITY_TO_STATE

        normalized = v.strip().upper()
        if normalized not in set(CITY_TO_STATE.values()):
            raise ValueError(
                f"{v!r} is not a state WhyPolice currently has real data for "
                "— see GET /api/search/states for the real, current list."
            )
        return normalized

    @field_validator("prompt")
    @classmethod
    def prompt_must_not_be_blank(cls, v: str) -> str:
        # min_length=1 alone lets a whitespace-only string through — the
        # frontend's SearchBar already disables submit for this case, but the
        # backend must not rely on that (found via Step 5's own bug sweep).
        if not v.strip():
            raise ValueError("must not be empty or whitespace-only")
        return v
