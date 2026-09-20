"""Request/response schemas for app/routers/inquiries.py — forum rebuild,
Milestone 1 Step M1.4 (WhyPoliceForum_MasterGuide.md).
"""

from pydantic import BaseModel, Field, field_validator

from app.models.inquiry import StatusTag


def _validate_state(v: str) -> str:
    """Real 2-letter USPS code. Deliberately NOT validated against the old
    RAG product's supported_states()/CITY_TO_STATE coverage list (see
    app/models/inquiry.py's own docstring on `state`, and
    WhyPoliceForum_MasterGuide.md M2.3's explicit warning) — that list
    only covers the states the OLD product ingested data for, and this
    new product is nationwide from day one. Just a real 2-letter
    uppercase code shape check, nothing narrower."""
    normalized = v.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise ValueError(f"{v!r} is not a valid 2-letter state code")
    return normalized


def _validate_nonblank(v: str, field_name: str) -> str:
    if not v.strip():
        raise ValueError(f"{field_name} must not be empty or whitespace-only")
    return v


class InquiryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    state: str = Field(min_length=2, max_length=2)
    city: str = Field(min_length=1, max_length=200)
    precinct: str | None = Field(default=None, max_length=200)
    status_tag: StatusTag
    # Accepted here but NOT itself sufficient to unlock the 250-char cap —
    # see the router's own real enforcement logic. A client claiming
    # tier="expanded" without a real, webhook-confirmed upgrade on file is
    # rejected, not trusted at face value (M1.4's own explicit
    # "do not silently trust an unverified expanded claim" requirement).
    tier: str = Field(default="free")

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        return _validate_nonblank(v, "title")

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        return _validate_nonblank(v, "description")

    @field_validator("city")
    @classmethod
    def city_not_blank(cls, v: str) -> str:
        return _validate_nonblank(v, "city")

    @field_validator("state")
    @classmethod
    def state_valid(cls, v: str) -> str:
        return _validate_state(v)


class InquiryUpdate(BaseModel):
    """PATCH — every field optional, only supplied fields are changed.
    Same "no time limit" edit policy as the client's own explicit answer
    (WhyPolice-Scope-Realignment.pdf)."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=20000)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    city: str | None = Field(default=None, min_length=1, max_length=200)
    precinct: str | None = Field(default=None, max_length=200)
    status_tag: StatusTag | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        return _validate_nonblank(v, "title") if v is not None else v

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str | None) -> str | None:
        return _validate_nonblank(v, "description") if v is not None else v

    @field_validator("city")
    @classmethod
    def city_not_blank(cls, v: str | None) -> str | None:
        return _validate_nonblank(v, "city") if v is not None else v

    @field_validator("state")
    @classmethod
    def state_valid(cls, v: str | None) -> str | None:
        return _validate_state(v) if v is not None else v


class ThreadCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def body_not_blank(cls, v: str) -> str:
        return _validate_nonblank(v, "body")


class ThreadCommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)

    @field_validator("body")
    @classmethod
    def body_not_blank(cls, v: str) -> str:
        return _validate_nonblank(v, "body")


class ConsultationDecision(BaseModel):
    decision: str  # "accepted" | "declined" — validated in the router
    # against AttorneyRequestStatus's real member set, matching this
    # project's existing pattern (search.py's SearchStreamRequest.state)
    # of validating against a real, live source rather than trusting an
    # arbitrary string blind.


class ReportCreate(BaseModel):
    target_type: str  # "inquiry" | "thread_comment"
    target_id: str  # UUID string, parsed in the router
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def reason_not_blank(cls, v: str) -> str:
        return _validate_nonblank(v, "reason")
