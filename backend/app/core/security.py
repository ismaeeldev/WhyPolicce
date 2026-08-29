"""Auth0 JWT verification — AgentGuide/03_MasterPromptGuide.md Step 4.

Verifies the signature (against Auth0's published JWKS for AUTH0_DOMAIN),
issuer, and audience of an incoming Bearer token, and extracts auth0_sub/email.
"""

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


def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
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

    jwks = _get_jwks()
    rsa_key = next(
        (
            {"kty": k["kty"], "kid": k["kid"], "use": k["use"], "n": k["n"], "e": k["e"]}
            for k in jwks.get("keys", [])
            if k.get("kid") == unverified_header.get("kid")
        ),
        None,
    )
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
