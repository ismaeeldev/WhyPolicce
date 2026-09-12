"""Live regression tests for find_relevant_records()'s real, already-
found citation-integrity bugs and known-good calibration cases —
plan.md's "Sample-question testing" / "Test similar client questions" /
"State Selector" sections have the full history and evidence for each
case asserted here.

Needs a real database (real pgvector data, real OpenAI embeddings) —
see this directory's own conftest.py for why these live in a separate
tests_live/ directory, not tests/, and how they're skipped when no real
DATABASE_URL is configured.

Run with: cd backend && pytest tests_live/ -v
"""

import asyncio

import pytest
from sqlmodel import Session

from app.core.db import engine
from app.services.vector_search_service import find_relevant_records


def _run(coro):
    return asyncio.run(coro)


class TestKnownFalsePositives:
    """Both of these are REAL bugs found via live testing this session,
    already fixed — these tests exist to catch a regression if either
    threshold/logic fix is ever accidentally reverted or loosened."""

    def test_fictional_city_question_has_no_sources(self):
        # Real bug (plan.md "Sample-question testing"): this query used
        # to retrieve two real Miami "False Pretenses/Swindle/Confidence
        # Game" records at distance 0.5974 — the embedding model
        # associates "made up"/fictional framing with fraud/swindle
        # semantics. Fixed by tightening MAX_RELEVANT_DISTANCE.
        with Session(engine) as session:
            records = _run(
                find_relevant_records(session, "What is going on in a made up city Fakesburg?")
            )
        assert records == [], (
            "Fakesburg-class false positive regressed — a fictional-city "
            "question retrieved real records again. See plan.md's "
            "MAX_RELEVANT_DISTANCE history before changing that threshold."
        )

    def test_wall_street_case_question_has_no_sources(self):
        # Real bug (plan.md "Client-provided sample questions"): this
        # query used to retrieve an unrelated real Brooklyn robbery
        # arrest at distance 0.5234 via the city-scoped path (NYC is a
        # named city). Required TWO fixes: a stricter
        # _CITY_SCOPED_MAX_DISTANCE AND lowering MAX_RELEVANT_DISTANCE
        # itself, since the city-scoped path's own fallback re-surfaced
        # the same record through the general search.
        with Session(engine) as session:
            records = _run(
                find_relevant_records(session, "Why did the NYPD close the case on Wall Street?")
            )
        assert records == [], (
            "Wall Street-class false positive regressed — an unrelated "
            "NYC record was retrieved again for a case that doesn't "
            "exist in the data. See plan.md's _CITY_SCOPED_MAX_DISTANCE "
            "history before changing either threshold."
        )

    def test_state_scoped_fictional_city_question_has_no_sources(self):
        # Real bug (plan.md "State Selector" Step 5): the state-scoped
        # path's own more-permissive threshold (needed for legitimate
        # vague queries to work at all) re-introduced the exact same
        # fraud/swindle false-positive class via a real Long Beach
        # record, once state=CA was selected. Fixed by tightening
        # _STATE_SCOPED_MAX_DISTANCE.
        with Session(engine) as session:
            records = _run(
                find_relevant_records(
                    session, "What is going on in a made up city Fakesburg?", state="CA"
                )
            )
        assert records == [], (
            "Fakesburg-class false positive regressed for a state-scoped "
            "query — see plan.md's _STATE_SCOPED_MAX_DISTANCE history."
        )


class TestKnownGoodRetrieval:
    """Real, legitimate queries that MUST keep returning real data —
    guards against the thresholds above ever being tightened so far they
    start producing false NEGATIVES (the opposite failure, an honest
    question wrongly declined) instead of just fixing false positives."""

    def test_single_city_named_returns_that_citys_data(self):
        with Session(engine) as session:
            records = _run(find_relevant_records(session, "Any crime reports in Chicago?"))
        assert records, "A direct, real Chicago question must retrieve real Chicago data."
        assert all(r.city == "Chicago" for r in records)

    def test_two_cities_named_returns_data_for_both(self):
        # Real fix (plan.md "Test similar client questions"): a genuine
        # two-city question must retrieve real data for BOTH cities, not
        # silently only the first one KNOWN_CITIES happens to list.
        with Session(engine) as session:
            records = _run(
                find_relevant_records(session, "Any crime in Chicago or Los Angeles?")
            )
        cities = {r.city for r in records}
        assert "Chicago" in cities
        assert "Los Angeles" in cities

    def test_state_scoped_vague_query_returns_real_data(self):
        # Real fix (plan.md "State Selector" Step 5): a vague, no-city
        # query with a state selected must still retrieve real data for
        # that state — this was the exact case that came back empty
        # (twice, for two different real reasons) before both fixes.
        with Session(engine) as session:
            records = _run(find_relevant_records(session, "Any recent crime?", state="IL"))
        assert records, "A vague query scoped to a real, covered state must retrieve real data."
        assert all(r.city in ("Chicago", "Aurora, IL", "Rockford, IL", "Winnebago County, IL") for r in records)

    def test_explicit_city_name_overrides_state_selector(self):
        # Real fix (plan.md "State Selector" Step 5): an explicit city
        # name in the question always wins over a selected state that
        # doesn't contain that city.
        with Session(engine) as session:
            records = _run(
                find_relevant_records(session, "crime in Chicago?", state="CA")
            )
        assert records, "An explicit city name must still retrieve that city's data."
        assert all(r.city == "Chicago" for r in records)
