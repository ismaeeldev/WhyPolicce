"""Stripe billing — AgentGuide/03_MasterPromptGuide.md Step 7.

Real Stripe SDK calls and webhook tier updates. Checkout returns an honest
501 until STRIPE_SECRET_KEY + STRIPE_PRICE_ID are configured."""

import json
import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.models.user import Tier, User

router = APIRouter(prefix="/api/billing")
logger = logging.getLogger("whypolice.billing")

_NOT_CONFIGURED = HTTPException(
    status_code=501,
    detail={
        "error": "not_implemented",
        "message": "Billing isn't fully set up yet — check back soon.",
    },
)


def _event_type(event: object) -> str:
    if isinstance(event, dict):
        return event["type"]
    return event["type"]  # type: ignore[index]


def _event_object(event: object) -> dict | None:
    if isinstance(event, dict):
        data = event.get("data")
        if not isinstance(data, dict):
            return None
        obj = data.get("object")
        return obj if isinstance(obj, dict) else None
    data = getattr(event, "data", None)
    obj = getattr(data, "object", None) if data is not None else None
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    # Stripe SDK object (StripeObject) — convert via its own to_dict(), not
    # json.dumps(obj, default=str): that previously called str(obj) on the
    # WHOLE object (since it isn't natively JSON-serializable), producing
    # its pretty-printed repr as a single string, then re-parsing that
    # string back into a plain `str`, not a dict — silently breaking every
    # real webhook event through this path. Found via a real signed
    # webhook test during Phase 4 (revision2.md): AttributeError: 'str'
    # object has no attribute 'get' in _handle_checkout_completed.
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return json.loads(json.dumps(obj, default=str))


def _handle_checkout_completed(session: Session, checkout_object: dict) -> None:
    """Upgrade user to Pro after a successful Stripe Checkout session."""
    ref = checkout_object.get("client_reference_id")
    if not ref:
        logger.warning("checkout.session.completed missing client_reference_id")
        return
    try:
        user_id = uuid.UUID(str(ref))
    except ValueError:
        logger.warning("checkout.session.completed has invalid client_reference_id: %s", ref)
        return

    user = session.get(User, user_id)
    if user is None:
        logger.warning("checkout.session.completed: no user for id %s", user_id)
        return

    user.tier = Tier.pro
    customer_id = checkout_object.get("customer")
    if customer_id:
        user.stripe_customer_id = str(customer_id)
    session.add(user)
    session.commit()
    logger.info("User %s upgraded to pro via Stripe checkout", user_id)


def _handle_subscription_deleted(session: Session, subscription_object: dict) -> None:
    """Downgrade user to Free when their Stripe subscription ends."""
    customer_id = subscription_object.get("customer")
    if not customer_id:
        logger.warning("customer.subscription.deleted missing customer id")
        return

    user = session.exec(
        select(User).where(User.stripe_customer_id == str(customer_id))
    ).first()
    if user is None:
        logger.warning("customer.subscription.deleted: no user for customer %s", customer_id)
        return

    user.tier = Tier.free
    session.add(user)
    session.commit()
    logger.info("User %s downgraded to free after subscription deleted", user.id)


def _get_or_create_user(session: Session, current: AuthenticatedUser) -> User:
    # IntegrityError guard matches users.py's own copy — a genuine
    # concurrent "first request ever" race for the same auth0_sub must
    # return the winner's row, not bubble up as a 500.
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        user = User(auth0_sub=current.auth0_sub, email=current.email or "")
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
            if user is None:
                raise
        else:
            session.refresh(user)
    elif current.email and not user.email:
        # Same self-heal as GET /api/me — see app/routers/users.py's comment.
        user.email = current.email
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.post("/create-checkout-session")
def create_checkout_session(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Auth required — rejects an unauthenticated request the same as every
    other protected route (get_current_user dependency), not just UI-gated.
    Returns a real Stripe Checkout URL once STRIPE_SECRET_KEY and
    STRIPE_PRICE_ID are both configured; until then, an honest 501 rather
    than a fake/broken checkout link."""
    user = _get_or_create_user(session, current)

    if user.tier == Tier.pro:
        raise HTTPException(
            status_code=400,
            detail={"error": "already_pro", "message": "You're already on the Pro plan."},
        )

    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_PRICE_ID:
        raise _NOT_CONFIGURED

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
            client_reference_id=str(user.id),
            customer_email=user.email or None,
            success_url=f"{settings.FRONTEND_URL}/account?upgraded=1",
            cancel_url=f"{settings.FRONTEND_URL}/upgrade",
        )
    except stripe.StripeError as exc:
        logger.exception("Stripe checkout session creation failed")
        raise HTTPException(
            status_code=502,
            detail={"error": "stripe_error", "message": "Couldn't start checkout — try again shortly."},
        ) from exc

    return {"checkoutUrl": checkout_session.url}


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """No JWT auth — Stripe calls this directly, authenticated by signature
    when STRIPE_WEBHOOK_SECRET is configured."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_signature", "message": "Invalid webhook signature."},
            ) from exc
    else:
        # No signing secret configured yet — accept unverified in dev only,
        # loudly logged so this is never silently insecure in production.
        logger.warning("Stripe webhook received with no STRIPE_WEBHOOK_SECRET configured — signature NOT verified.")
        try:
            event = json.loads(payload)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_payload", "message": "Malformed webhook payload."},
            ) from exc

    event_type = _event_type(event)

    if event_type == "checkout.session.completed":
        checkout_object = _event_object(event)
        if checkout_object:
            _handle_checkout_completed(session, checkout_object)
    elif event_type == "customer.subscription.deleted":
        subscription_object = _event_object(event)
        if subscription_object:
            _handle_subscription_deleted(session, subscription_object)

    return {"received": True}
