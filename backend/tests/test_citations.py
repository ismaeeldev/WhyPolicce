"""Tests for _build_citations() — search_service.py's real citation
de-duplication logic (plan.md "Source citation UI feature").

Pure logic, no database/embeddings needed, unlike find_relevant_records()
itself (covered separately in test_retrieval_live.py, which needs a real
live database and is gated accordingly) — this locks in the actual
de-duplication/ordering behavior with fixture PublicRecord-shaped data,
closing a real gap found during a project gap-audit: every real bug this
session found in the citation/retrieval pipeline was verified once, by
hand, live, and never captured as a permanent regression test.
"""

from app.models.public_record import PublicRecord
from app.services.search_service import _build_citations


def _record(city: str, source: str) -> PublicRecord:
    # Only city/source matter to _build_citations — the other required
    # fields get harmless placeholder values.
    return PublicRecord(
        source=source,
        external_id=f"{source}-{city}",
        city=city,
        raw_text="placeholder",
        raw_json={},
        embedding=[0.0] * 1536,
    )


def test_empty_records_returns_empty_list():
    assert _build_citations([]) == []


def test_single_record_returns_one_citation():
    records = [_record("Chicago", "chicago_crimes")]
    assert _build_citations(records) == [{"city": "Chicago", "source": "chicago_crimes"}]


def test_duplicate_city_and_source_collapses_to_one_citation():
    # Real scenario this project's own retrieval logic produces: multiple
    # retrieved records from the exact same (city, source) pair.
    records = [
        _record("Chicago", "chicago_crimes"),
        _record("Chicago", "chicago_crimes"),
        _record("Chicago", "chicago_crimes"),
    ]
    assert _build_citations(records) == [{"city": "Chicago", "source": "chicago_crimes"}]


def test_same_city_different_source_stays_two_citations():
    # Real, live-verified scenario from plan.md's own history: NYC's
    # nyc_nypd_arrest and nyc_nypd_complaint are two genuinely distinct
    # datasets for the same city — the backend must keep them as two
    # separate citations (the frontend's own display-layer de-duplication
    # is a deliberately separate concern, not this function's job).
    records = [
        _record("New York City", "nyc_nypd_arrest"),
        _record("New York City", "nyc_nypd_complaint"),
    ]
    assert _build_citations(records) == [
        {"city": "New York City", "source": "nyc_nypd_arrest"},
        {"city": "New York City", "source": "nyc_nypd_complaint"},
    ]


def test_multi_city_preserves_first_seen_order():
    # Real scenario from the State Selector's multi-city retrieval fix:
    # results from several cities, interleaved by relevance — citation
    # order must match retrieval order, not get re-sorted alphabetically
    # or by city name.
    records = [
        _record("Los Angeles", "la_crime"),
        _record("Chicago", "chicago_crimes"),
        _record("Los Angeles", "la_crime"),
        _record("Chicago", "chicago_crimes"),
    ]
    assert _build_citations(records) == [
        {"city": "Los Angeles", "source": "la_crime"},
        {"city": "Chicago", "source": "chicago_crimes"},
    ]
