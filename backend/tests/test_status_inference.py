import pytest

from app.models.inquiry import StatusTag
from app.services.status_inference import infer_status_tag

AWAITING = StatusTag.awaiting_police_statement
TRACE = StatusTag.community_trace


@pytest.mark.parametrize(
    "title",
    [
        "Awaiting police statement on Main St incident",
        "Still waiting for an answer from the 104th precinct",
        "No response from the department after 3 weeks",
        "Requesting a statement about the traffic stop",
        "Police have not responded to our complaint",
        "Unresolved: officer conduct on 5th Ave",
    ],
)
def test_title_signals_awaiting(title):
    assert infer_status_tag(title) == AWAITING


@pytest.mark.parametrize(
    "title",
    [
        "Witnessed an arrest outside the subway station",
        "Footage of the incident near City Hall",
        "Community meeting about patrol hours",
        "Police Brutality",
    ],
)
def test_other_titles_are_community_trace(title):
    assert infer_status_tag(title, "We saw what happened and filmed it.") == TRACE


def test_description_only_counts_for_explicit_statement_phrases():
    assert infer_status_tag("Incident on Elm St", "We are still waiting and tired.") == TRACE
    assert infer_status_tag("Incident on Elm St", "We requested an official statement last week.") == AWAITING


def test_create_without_status_assigns_it(client, session):
    r = client.post(
        "/api/v1/inquiries",
        json={"title": "Awaiting police statement", "description": "short", "state": "NY", "city": "NYC"},
    )
    assert r.status_code == 201 and r.json()["statusTag"] == "awaiting_police_statement"
    r = client.post(
        "/api/v1/inquiries",
        json={"title": "Saw an incident", "description": "short", "state": "NY", "city": "NYC"},
    )
    assert r.status_code == 201 and r.json()["statusTag"] == "community_trace"


def test_edit_title_reassigns_status(client, session):
    created = client.post(
        "/api/v1/inquiries",
        json={"title": "Saw an incident", "description": "short", "state": "NY", "city": "NYC"},
    ).json()
    r = client.patch(f"/api/v1/inquiries/{created['id']}", json={"title": "No response from police"})
    assert r.status_code == 200 and r.json()["statusTag"] == "awaiting_police_statement"
