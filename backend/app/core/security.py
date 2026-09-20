"""Auth0 JWT verification — AgentGuide/03_MasterPromptGuide.md Step 4.

Verifies the signature (against Auth0's published JWKS for AUTH0_DOMAIN),
issuer, and audience of an incoming Bearer token, and extracts auth0_sub/email.
"""

import time
from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException
from jose import jwt
from jose.exceptions import JOSEError

from app.core.config import settings


class AuthError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


@dataclass
class AuthenticatedUser:
    auth0_sub: str
    email: str | None


_jwks_cache: dict | None = None
_jwks_cache_at: float = 0.0

# Found during hardening: the previous cache never expired for the entire
# process lifetime (only fetched once, ever, on first use). Auth0
# periodically rotates its signing keys — a real, documented operational
# event, not hypothetical — and once that happens, every new token signed
# with the new key would fail "Signing key not found for this token" until
# the backend process happened to restart. 1 hour balances not hammering
# Auth0's JWKS endpoint on every request against not staying stale for
# days after a real rotation.
_JWKS_CACHE_TTL_SECONDS = 3600


def _fetch_jwks() -> dict:
    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=5.0)
    resp.raise_for_status()
    return resp.json()


def _get_jwks(force_refresh: bool = False) -> dict:
    global _jwks_cache, _jwks_cache_at
    is_stale = _jwks_cache is None or (time.monotonic() - _jwks_cache_at) > _JWKS_CACHE_TTL_SECONDS
    if is_stale or force_refresh:
        _jwks_cache = _fetch_jwks()
        _jwks_cache_at = time.monotonic()
    return _jwks_cache


def verify_token(token: str) -> AuthenticatedUser:
    """Raises AuthError on any verification failure — signature, issuer,
    audience, or expiry. Never raises a raw exception past this boundary."""
    if not settings.AUTH0_DOMAIN:
        raise AuthError("Auth0 is not configured")

    try:
        unverified_header = jwt.get_unverified_header(token)
    except JOSEError as exc:
        raise AuthError("Malformed token") from exc

    # Found during hardening: a real JWKS-fetch failure (Auth0 outage,
    # network issue, DNS problem — httpx.HTTPError and its subclasses, not
    # a JOSEError) was previously left uncaught here, leaking a raw
    # exception straight past this function's own documented contract
    # ("never raises a raw exception past this boundary") and surfacing
    # as an unhandled 500 to the user instead of a clean 401 — verified
    # by forcing a real ConnectTimeout through _get_jwks() and confirming
    # it leaked unhandled before this fix. This is a genuinely different
    # failure than "malformed token" (which fails the block above, before
    # any network call happens), so it gets its own distinct message —
    # useful for whoever investigates a real spike of these, so they look
    # at Auth0/network connectivity, not token formatting.
    try:
        jwks = _get_jwks()
    except httpx.HTTPError as exc:
        raise AuthError("Could not verify token — identity provider unreachable") from exc

    def _find_key(keys: list[dict]) -> dict | None:
        return next(
            (
                {"kty": k["kty"], "kid": k["kid"], "use": k["use"], "n": k["n"], "e": k["e"]}
                for k in keys
                if k.get("kid") == unverified_header.get("kid")
            ),
            None,
        )

    rsa_key = _find_key(jwks.get("keys", []))
    if rsa_key is None:
        # A key genuinely missing from an up-to-TTL cache is itself a
        # strong signal a real Auth0 key rotation just happened (not just
        # a malformed/forged token — those fail signature verification
        # below, not this lookup) — force one immediate refresh before
        # giving up, rather than waiting up to _JWKS_CACHE_TTL_SECONDS for
        # the normal refresh to happen on its own. Same httpx.HTTPError
        # protection as the first _get_jwks() call above — this refresh
        # attempt can fail for the same real network/outage reasons.
        try:
            jwks = _get_jwks(force_refresh=True)
        except httpx.HTTPError as exc:
            raise AuthError("Could not verify token — identity provider unreachable") from exc
        rsa_key = _find_key(jwks.get("keys", []))
    if rsa_key is None:
        raise AuthError("Signing key not found for this token")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE or None,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
            options={"verify_aud": bool(settings.AUTH0_AUDIENCE)},
        )
    except JOSEError as exc:
        raise AuthError(f"Token verification failed: {exc}") from exc

    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token missing sub claim")

    # A verified live token (2026-08-26) confirmed Auth0's actual, standard
    # behavior: an access token issued for a custom API audience never
    # includes profile claims like `email` just because "profile email" was
    # requested in scope — those scopes only affect the ID token and the
    # /userinfo endpoint, not a resource-server access token. To get email
    # into THIS token, the tenant needs an Auth0 Action adding it as a
    # namespaced custom claim (see AgentGuide/05_PROJECT_STATE.md for the
    # exact Action code and manual-task instructions given to the client).
    # Reads the namespaced claim first, with a plain "email" fallback in case
    # the tenant is ever configured to include it directly (e.g. a
    # first-party/trusted-client exception) — never assumes only one shape.
    email = payload.get(f"{settings.AUTH0_AUDIENCE}/email") or payload.get("email")

    return AuthenticatedUser(auth0_sub=sub, email=email)


async def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    """FastAPI dependency — extracts and verifies the Bearer token, raising a
    401 with the standard {error, message} shape (via HTTPException, caught by
    the global handler's sibling logic) on any failure."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "unauthorized", "message": "Missing or malformed Authorization header"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_token(token)
    except AuthError as exc:
        raise HTTPException(
            status_code=401, detail={"error": "unauthorized", "message": exc.message}
        ) from exc


async def get_optional_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser | None:
    """Forum rebuild, Milestone 2 Step M2.2 (WhyPoliceForum_MasterGuide.md) —
    real gap found while building the home feed: GET /api/v1/inquiries (and
    its sibling read endpoints, get_inquiry/get_thread) used get_current_user,
    which unconditionally 401s a request with no Bearer token. The scope PDF
    and M2.0's own proxy.ts both treat reading the forum as public — a
    logged-out visitor landing on the feed should see it, not a 401. This
    dependency makes auth OPTIONAL for those routes: returns a real
    AuthenticatedUser when a valid token is present (so isFollowing/other
    per-viewer fields still work for a logged-in visitor), None when no
    token is given at all, and still raises 401 for a token that IS present
    but invalid/expired/malformed — a bad token should never be silently
    treated the same as "anonymous," since that would mask a real client-side
    auth bug as if the user were simply logged out."""
    if not authorization:
        return None
    return await get_current_user(authorization)
