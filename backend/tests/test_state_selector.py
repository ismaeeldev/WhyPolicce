"""Tests for the State Selector feature — plan.md "State Selector" (real
client-requested feature, see the client's own pasted SearchBar draft).

Step 1: CITY_TO_STATE must stay in exact sync with KNOWN_CITIES — every
city has a real state, and there are no orphaned/stale entries left
behind if a city is ever renamed or removed. A future city-expansion
phase that adds to KNOWN_CITIES but forgets CITY_TO_STATE would otherwise
silently ship a state selector that can't find that city — this test
fails loudly instead.
"""

import re

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.schemas.search import SearchStreamRequest
from app.services.vector_search_service import CITY_TO_STATE, KNOWN_CITIES, supported_states

_VALID_USPS_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}


def test_every_known_city_has_a_state():
    missing = [city for city in KNOWN_CITIES if city not in CITY_TO_STATE]
    assert not missing, f"KNOWN_CITIES entries missing from CITY_TO_STATE: {missing}"


def test_no_orphaned_state_entries():
    orphaned = [city for city in CITY_TO_STATE if city not in KNOWN_CITIES]
    assert not orphaned, f"CITY_TO_STATE entries no longer in KNOWN_CITIES: {orphaned}"


def test_every_state_code_is_a_real_two_letter_code():
    for city, state in CITY_TO_STATE.items():
        assert re.fullmatch(r"[A-Z]{2}", state), f"{city!r} has a malformed state code: {state!r}"
        assert state in _VALID_USPS_CODES, f"{city!r} has an unrecognized state code: {state!r}"


def test_known_spot_checks_are_correct():
    """A few deliberately-ambiguous-by-name cities, confirmed against this
    project's own real ingestion module (not guessed) — see CITY_TO_STATE's
    own comment for the real evidence behind each."""
    assert CITY_TO_STATE["Kansas City"] == "MO"
    assert CITY_TO_STATE["Montgomery County"] == "MD"
    assert CITY_TO_STATE["Prince George's County"] == "MD"
    assert CITY_TO_STATE["St. Louis County"] == "MO"
    assert CITY_TO_STATE["Washington, DC"] == "DC"


def test_supported_states_matches_real_coverage():
    """Step 2: supported_states() must reflect exactly the states
    CITY_TO_STATE actually covers today — no more (not all 50), no less."""
    codes = {code for code, _ in supported_states()}
    assert codes == set(CITY_TO_STATE.values())


def test_supported_states_not_the_old_five_state_placeholder():
    """Real regression guard: the client's own draft hardcoded exactly
    NY/CA/TX/FL/IL as a 5-state placeholder. This feature exists
    specifically to replace that with real, live-derived coverage — if
    this ever again returns exactly those 5, something regressed back to
    a hardcoded list."""
    codes = {code for code, _ in supported_states()}
    assert codes != {"NY", "CA", "TX", "FL", "IL"}
    assert len(codes) > 5


def test_supported_states_returns_real_full_names_sorted():
    states = supported_states()
    assert states, "supported_states() must not be empty"
    names = [name for _, name in states]
    assert names == sorted(names)
    # Spot-check a couple of real, unambiguous full names.
    by_code = dict(states)
    assert by_code["CA"] == "California"
    assert by_code["IL"] == "Illinois"
    assert by_code["DC"] == "District of Columbia"


class TestGetSupportedStatesEndpoint:
    """Step 3: GET /api/search/states."""

    def test_requires_auth(self):
        with TestClient(app) as anon_client:
            res = anon_client.get("/api/search/states")
        assert res.status_code == 401

    def test_returns_real_states(self, client: TestClient):
        res = client.get("/api/search/states")
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        assert len(body) > 5  # not the old 5-state placeholder
        assert all(set(entry.keys()) == {"code", "name"} for entry in body)
        codes = {entry["code"] for entry in body}
        assert "CA" in codes
        assert "IL" in codes
        by_code = {entry["code"]: entry["name"] for entry in body}
        assert by_code["CA"] == "California"


class TestSearchStreamRequestState:
    """Step 4: SearchStreamRequest.state — optional, validated against
    real coverage, matching the client's own pasted request body's
    `state: params.state` field."""

    def test_state_defaults_to_none(self):
        req = SearchStreamRequest(prompt="Any crime in Chicago?")
        assert req.state is None

    def test_valid_state_accepted_and_normalized(self):
        req = SearchStreamRequest(prompt="Any crime in Chicago?", state="il")
        assert req.state == "IL"  # lowercase input normalized to uppercase

    def test_unsupported_state_rejected(self):
        with pytest.raises(ValidationError):
            SearchStreamRequest(prompt="Any crime in Chicago?", state="ZZ")

    def test_real_state_with_no_coverage_rejected(self):
        # Real, deliberate case: Wyoming (WY) is a genuine US state with a
        # genuine 2-letter code, but WhyPolice has zero integrated cities
        # there — this must be rejected the same as a nonsense code, not
        # silently accepted just because it's a real state.
        with pytest.raises(ValidationError):
            SearchStreamRequest(prompt="Any crime?", state="WY")

    def test_existing_callers_without_state_unaffected(self):
        # Regression guard: every pre-existing caller/test that never sent
        # `state` at all must still work exactly as before this feature.
        req = SearchStreamRequest(prompt="Any crime in Chicago?", deepSearch=True, sessionId="abc-123")
        assert req.state is None
        assert req.deepSearch is True
        assert req.sessionId == "abc-123"


# Step 5's real backend-scoping logic (find_relevant_records's `state`
# parameter) is NOT covered by an automated test here — it needs real
# pgvector embeddings against the live Neon database, which this
# project's offline SQLite-backed test suite deliberately never uses
# (matching every other retrieval-quality fix in this codebase — the
# MAX_RELEVANT_DISTANCE/_CITY_SCOPED_MAX_DISTANCE calibrations above it
# were all verified the same way: live ad-hoc scripts, not pytest).
#
# Live-verified directly (plan.md "State Selector" has the full record):
#   1. find_relevant_records(session, "Any recent crime?", state="IL")
#      -> real Chicago records (the actual bug this step fixed: the
#      first attempt reused MAX_RELEVANT_DISTANCE and returned nothing)
#   2. find_relevant_records(session, "...made up city Fakesburg?", state="IL")
#      -> [] (the Fakesburg-class false positive stays excluded even
#      with the new, more permissive _STATE_SCOPED_MAX_DISTANCE)
#   3. find_relevant_records(session, "crime in Miami?", state="IL")
#      -> real Miami records (an explicit city name in the question
#      always overrides the state selector, never silently ignored)
