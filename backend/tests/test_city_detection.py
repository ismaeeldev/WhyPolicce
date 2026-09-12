"""Tests for _detect_named_city/_detect_named_cities — vector_search_
service.py's real city-name detection logic (plan.md "Test similar
client questions", the multi-city retrieval fix).

Pure string-matching logic, no database/embeddings needed — closes a
real gap found during a project gap-audit: the real bug this exact
function had (silently only ever detecting the FIRST named city, which
caused "Compare crime between Chicago and Los Angeles" to only retrieve
Los Angeles) was found and fixed via live testing, then never captured
as a permanent regression test.
"""

from app.services.vector_search_service import _detect_named_city, _detect_named_cities


def test_no_city_named_returns_empty():
    assert _detect_named_cities("What is the weather like today?") == []
    assert _detect_named_city("What is the weather like today?") is None


def test_single_city_named():
    assert _detect_named_cities("Any crime reports in Chicago?") == ["Chicago"]
    assert _detect_named_city("Any crime reports in Chicago?") == "Chicago"


def test_two_cities_named_both_detected():
    # The exact real bug this function's plural version was built to fix
    # (plan.md): the singular _detect_named_city only ever finds the
    # first — _detect_named_cities must find both.
    cities = _detect_named_cities("Compare crime between Chicago and Los Angeles")
    assert "Chicago" in cities
    assert "Los Angeles" in cities
    assert len(cities) == 2


def test_singular_still_returns_only_first_of_multiple():
    # _detect_named_city is deliberately kept as the single-first-match
    # version for any caller that only ever wanted that — confirm it
    # still behaves that way, not silently changed to return a list.
    result = _detect_named_city("Compare crime between Chicago and Los Angeles")
    assert result in ("Chicago", "Los Angeles")  # whichever KNOWN_CITIES lists first
    assert isinstance(result, str)


def test_washington_dc_alias_variants_all_detected():
    # Real bug found and fixed (Revision 3 Step 9 Phase 7): a flat
    # string-match against KNOWN_CITIES would never match "Washington, DC"
    # for how people actually phrase it.
    assert _detect_named_cities("What is the curfew in DC tonight?") == ["Washington, DC"]
    assert _detect_named_cities("Any crime in Washington DC?") == ["Washington, DC"]
    assert _detect_named_cities("What happened in Washington, D.C.?") == ["Washington, DC"]


def test_case_insensitive():
    assert _detect_named_cities("any crime in CHICAGO?") == ["Chicago"]
    assert _detect_named_cities("any crime in chicago?") == ["Chicago"]


def test_city_not_in_known_cities_returns_empty():
    assert _detect_named_cities("Any crime reports in Cedar Lake, Indiana?") == []
