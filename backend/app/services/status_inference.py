"""Assigns an inquiry's status tag from its own text, so posters never pick one.

"Awaiting Police Statement" = the post is about an incident where the poster is
waiting on / asking for an official police response. Everything else is a
"Community Trace" (community-reported incident, evidence or observation).
Title is the primary signal; the description only counts for explicit
statement phrases, so an offhand "waiting" in a long story doesn't flip it.
"""
import re

from app.models.inquiry import StatusTag

_TITLE_PATTERNS = re.compile(
    r"\b("
    r"awaiting|waiting|await|pending|unanswered|unresolved|no (response|reply|update|answer|comment)|"
    r"not (responded|answered|replied|released|provided)|"
    r"(police|official|public|written|press) (statement|response|report|explanation|comment)|"
    r"statement (needed|requested|requested|requested|pending)|"
    r"request(ed|ing)? (a |an |the )?(statement|response|report|explanation|update)|"
    r"(demand|need|want|seeking)\w* (a |an |the )?(statement|response|answer|explanation)|"
    r"still (no|waiting)|where is the (statement|report)|why (hasn't|haven't|has not|have not)"
    r")\b",
    re.IGNORECASE,
)
_DESCRIPTION_PATTERNS = re.compile(
    r"\b("
    r"(awaiting|waiting for|requested|requesting|demand(ed|ing)?|still no) (a |an |the |any )?"
    r"(police|official|department'?s?) (statement|response|report|explanation)|"
    r"police (have|has) not (responded|released|issued|commented)|"
    r"no (police|official) (statement|response)"
    r")\b",
    re.IGNORECASE,
)


def infer_status_tag(title: str, description: str = "") -> StatusTag:
    if _TITLE_PATTERNS.search(title or ""):
        return StatusTag.awaiting_police_statement
    if _DESCRIPTION_PATTERNS.search(description or ""):
        return StatusTag.awaiting_police_statement
    return StatusTag.community_trace
