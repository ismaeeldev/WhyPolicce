"""Forum billing — Stripe Checkout + Webhooks for both billing shapes —
forum rebuild, Milestone 3 Step M3.2 (WhyPoliceForum_MasterGuide.md).

A BRAND-NEW Stripe account per the Manual Step's own explicit
instruction ("not the client's existing account"), deliberately
separate from app/routers/billing.py's STRIPE_SECRET_KEY/STRIPE_PRICE_ID
(the OLD product's single Pro-plan subscription on a different Stripe
account) — see app/core/config.py's own FORUM_STRIPE_* fields for why.

Checkout endpoints return an honest 501 (this codebase's own established
"not configured yet" pattern, see billing.py) until
FORUM_STRIPE_SECRET_KEY + both price ids are configured — never a mocked
Checkout URL.
"""

import json
import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.models.inquiry import Inquiry, InquiryTier
from app.models.processed_stripe_event import ProcessedStripeEvent
from app.models.user import Role, User, VerificationStatus

router = APIRouter(prefix="/api/v1/billing")
logger = logging.getLogger("whypolice.forum_billing")

_NOT_CONFIGURED = HTTPException(
    status_code=501,
    detail={
        "error": "not_implemented",
        "message": "Payments aren't fully set up yet — check back soon.",
    },
)


def _get_or_create_user(session: Session, current: AuthenticatedUser) -> User:
    """Duplicated per this codebase's own established per-router pattern."""
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        user = User(auth0_sub=current.auth0_sub, email=current.email or "")
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _event_type(event: object) -> str:
    if isinstance(event, dict):
        return event["type"]
    return event["type"]  # type: ignore[index]


def _event_id(event: object) -> str:
    if isinstance(event, dict):
        return event["id"]
    return event["id"]  # type: ignore[index]


def _event_object(event: object) -> dict | None:
    """Same real StripeObject-vs-dict handling as billing.py's own
    _event_object — see that function's docstring for the real bug
    (a WHOLE-object str() producing a broken non-dict) this pattern
    avoids. Duplicated here rather than imported since the two billing
    routers are deliberately independent (separate Stripe accounts)."""
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
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return json.loads(json.dumps(obj, default=str))


def _already_processed(session: Session, event_id: str) -> bool:
    """Real, DB-backed idempotency guard (Bug Fix's own explicit "replay
    the same webhook event twice" adversarial requirement) — Stripe's own
    docs warn the same event can be delivered more than once.

    Real bug found during a full-scope re-audit: this used to insert AND
    commit the marker row up front, before the handler did its own real
    work (flipping tier/subscription state) in a SEPARATE, later commit.
    If that second commit failed for any reason (a dropped Neon
    connection, a lock timeout — this app's own db.py already documents
    Neon silently dropping connections), the marker row was already
    durable, so Stripe's automatic retry of the same event would be
    skipped as a "duplicate" forever — a customer could pay and the
    inquiry/subscription would never actually update, with no recovery
    path. Now this only checks; the marker insert and the handler's own
    writes are staged together and committed exactly once, atomically,
    by the caller — so a mid-handler failure rolls back the marker too
    and Stripe's retry gets a genuine second attempt."""
    existing = session.exec(
        select(ProcessedStripeEvent).where(ProcessedStripeEvent.stripe_event_id == event_id)
    ).first()
    return existing is not None


def _handle_inquiry_upgrade_completed(session: Session, checkout_object: dict) -> None:
    # Real gap found during a full-scope re-audit: Stripe fires
    # checkout.session.completed for delayed-notification payment
    # methods (ACH, Bacs, some bank redirects) BEFORE the payment has
    # actually settled — payment_status is "unpaid" at that point, only
    # becoming "paid" later via a separate checkout.session.async_
    # payment_succeeded event this app doesn't listen for. Without this
    # check, a user starting (but not yet completing) an ACH payment got
    # the unlimited-length/5-file upgrade immediately, permanently, with
    # no automated path to revert it if the ACH debit later bounced.
    # "no_payment_required" (e.g. a 100%-off coupon) is also legitimate
    # and should still upgrade.
    payment_status = checkout_object.get("payment_status")
    if payment_status not in ("paid", "no_payment_required"):
        logger.info(
            "checkout.session.completed (inquiry upgrade) payment_status=%s — not yet paid, ignoring until a real payment-succeeded event",
            payment_status,
        )
        return

    metadata = checkout_object.get("metadata") or {}
    inquiry_id_raw = metadata.get("inquiry_id")
    if not inquiry_id_raw:
        logger.warning("checkout.session.completed (inquiry upgrade) missing inquiry_id metadata")
        return
    try:
        inquiry_id = uuid.UUID(str(inquiry_id_raw))
    except ValueError:
        logger.warning("checkout.session.completed (inquiry upgrade) invalid inquiry_id: %s", inquiry_id_raw)
        return

    inquiry = session.get(Inquiry, inquiry_id)
    if inquiry is None:
        logger.warning("checkout.session.completed (inquiry upgrade): no inquiry for id %s", inquiry_id)
        return

    inquiry.tier = InquiryTier.expanded
    session.add(inquiry)
    logger.info("Inquiry %s upgraded to expanded via Stripe checkout", inquiry_id)


def _handle_attorney_subscription_completed(session: Session, checkout_object: dict) -> None:
    metadata = checkout_object.get("metadata") or {}
    user_id_raw = metadata.get("user_id")
    if not user_id_raw:
        logger.warning("checkout.session.completed (attorney subscription) missing user_id metadata")
        return
    try:
        user_id = uuid.UUID(str(user_id_raw))
    except ValueError:
        logger.warning("checkout.session.completed (attorney subscription) invalid user_id: %s", user_id_raw)
        return

    user = session.get(User, user_id)
    if user is None:
        logger.warning("checkout.session.completed (attorney subscription): no user for id %s", user_id)
        return

    user.attorney_subscription_active = True
    customer_id = checkout_object.get("customer")
    if customer_id:
        user.forum_stripe_customer_id = str(customer_id)
    session.add(user)
    logger.info("Attorney %s subscription activated via Stripe checkout", user_id)


def _handle_attorney_subscription_lapsed(session: Session, object_body: dict) -> None:
    """Handles both customer.subscription.deleted and
    invoice.payment_failed — both mean the attorney no longer has an
    active paid subscription, re-locking M2.4's portal paywall for real
    (previously always-locked via the ATTORNEY_SUBSCRIPTION_ACTIVE_STUB
    placeholder)."""
    customer_id = object_body.get("customer")
    if not customer_id:
        logger.warning("subscription-lapsed event missing customer id")
        return

    user = session.exec(
        select(User).where(User.forum_stripe_customer_id == str(customer_id))
    ).first()
    if user is None:
        logger.warning("subscription-lapsed event: no user for customer %s", customer_id)
        return

    user.attorney_subscription_active = False
    session.add(user)
    logger.info("Attorney %s subscription lapsed — portal re-locked", user.id)


@router.post("/checkout/inquiry-upgrade")
def create_inquiry_upgrade_checkout(
    body: dict,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """One-time $2.99 citizen inquiry-upgrade checkout. body: {inquiry_id}."""
    user = _get_or_create_user(session, current)

    inquiry_id_raw = body.get("inquiry_id")
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    try:
        inquiry_id = uuid.UUID(str(inquiry_id_raw))
    except (ValueError, TypeError):
        raise not_found from None
    inquiry = session.get(Inquiry, inquiry_id)
    if inquiry is None:
        raise not_found
    if inquiry.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "You can only upgrade your own inquiries."},
        )

    if not settings.FORUM_STRIPE_SECRET_KEY or not settings.FORUM_STRIPE_INQUIRY_UPGRADE_PRICE_ID:
        raise _NOT_CONFIGURED

    stripe.api_key = settings.FORUM_STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": settings.FORUM_STRIPE_INQUIRY_UPGRADE_PRICE_ID, "quantity": 1}],
            metadata={"inquiry_id": str(inquiry.id), "user_id": str(user.id)},
            customer_email=user.email or None,
            success_url=f"{settings.FRONTEND_URL}/inquiries/{inquiry.id}?upgraded=1",
            cancel_url=f"{settings.FRONTEND_URL}/inquiries/{inquiry.id}",
        )
    except stripe.StripeError as exc:
        logger.exception("Forum Stripe inquiry-upgrade checkout session creation failed")
        raise HTTPException(
            status_code=502,
            detail={"error": "stripe_error", "message": "Couldn't start checkout — try again shortly."},
        ) from exc

    return {"checkoutUrl": checkout_session.url}


@router.post("/checkout/attorney-subscription")
def create_attorney_subscription_checkout(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Recurring $149/month attorney-subscription checkout. Only a
    verification_status="approved" attorney may reach a payment screen
    for a subscription they can't yet use otherwise — real server-side
    check, not just a UI-level gate (M3.2's own explicit Bug Fix
    requirement: "attempt to trigger the attorney-subscription checkout
    as a still-pending attorney by calling the endpoint directly")."""
    user = _get_or_create_user(session, current)

    if user.role != Role.attorney or user.verification_status != VerificationStatus.approved:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "not_verified",
                "message": "Only approved attorneys can subscribe.",
            },
        )

    if not settings.FORUM_STRIPE_SECRET_KEY or not settings.FORUM_STRIPE_ATTORNEY_SUBSCRIPTION_PRICE_ID:
        raise _NOT_CONFIGURED

    stripe.api_key = settings.FORUM_STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": settings.FORUM_STRIPE_ATTORNEY_SUBSCRIPTION_PRICE_ID, "quantity": 1}],
            metadata={"user_id": str(user.id)},
            customer_email=user.email or None,
            success_url=f"{settings.FRONTEND_URL}/attorneys/dashboard?subscribed=1",
            cancel_url=f"{settings.FRONTEND_URL}/attorneys/dashboard",
        )
    except stripe.StripeError as exc:
        logger.exception("Forum Stripe attorney-subscription checkout session creation failed")
        raise HTTPException(
            status_code=502,
            detail={"error": "stripe_error", "message": "Couldn't start checkout — try again shortly."},
        ) from exc

    return {"checkoutUrl": checkout_session.url}


@router.post("/webhook")
async def forum_stripe_webhook(
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """No JWT auth — Stripe calls this directly, authenticated by
    signature when FORUM_STRIPE_WEBHOOK_SECRET is configured. A missing/
    invalid signature is rejected outright (M3.2's own explicit Bug Fix
    requirement), never processed."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.FORUM_STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=501,
            detail={"error": "not_implemented", "message": "Webhook isn't fully set up yet."},
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.FORUM_STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_signature", "message": "Invalid webhook signature."},
        ) from exc

    event_id = _event_id(event)
    if _already_processed(session, event_id):
        logger.info("Stripe event %s already processed — skipping duplicate delivery", event_id)
        return {"received": True, "duplicate": True}

    event_type = _event_type(event)
    object_body = _event_object(event)

    if event_type == "checkout.session.completed" and object_body:
        metadata = object_body.get("metadata") or {}
        if "inquiry_id" in metadata:
            _handle_inquiry_upgrade_completed(session, object_body)
        elif "user_id" in metadata:
            _handle_attorney_subscription_completed(session, object_body)
    elif event_type in ("customer.subscription.deleted", "invoice.payment_failed") and object_body:
        _handle_attorney_subscription_lapsed(session, object_body)

    # Real gap found during a full-scope re-audit: the marker row used
    # to be inserted AND committed up front, before any handler's own
    # work. If the handler's write then failed to commit (a dropped
    # Neon connection, a lock timeout), the marker was already durable
    # and Stripe's retry of the same event would be silently skipped as
    # a "duplicate" forever, with the real state change never applied.
    # Staging the marker here and committing everything together means
    # a failure anywhere rolls back the whole event — marker included —
    # so Stripe's automatic retry gets a genuine second attempt.
    session.add(ProcessedStripeEvent(stripe_event_id=event_id))
    session.commit()

    return {"received": True}
