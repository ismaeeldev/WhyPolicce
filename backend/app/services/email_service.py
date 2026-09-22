"""Transactional email — forum rebuild, Milestone 3 Step M3.3
(WhyPoliceForum_MasterGuide.md).

Resend (developer's own choice per the Manual Step's "agent's/developer's
choice" instruction). Real Resend SDK calls, no mocked "email sent"
response — when RESEND_API_KEY is empty, sending is skipped with an
honest log line (this project's established GCS/Stripe
not-configured pattern), never a fake success.

Both templates are plain-text-forward with a single accent-colored CTA
link, per this step's own explicit UI Details guidance: most email
clients strip complex CSS, so this doesn't attempt the full
ThemeGuideline system in HTML email — a clean, mostly-plain-text email
is the right target.
"""

import logging

import resend

from app.core.config import settings

logger = logging.getLogger("whypolice.email")

_ACCENT_COLOR = "#c9a15a"


def is_configured() -> bool:
    return bool(settings.RESEND_API_KEY)


def _wrap_html(body_html: str, cta_url: str, cta_label: str) -> str:
    return f"""
<div style="font-family: -apple-system, Helvetica, Arial, sans-serif; color: #1a1a1a; max-width: 480px; margin: 0 auto; padding: 24px;">
  <p style="font-size: 20px; font-weight: 600; margin: 0 0 24px;">WhyPolice<span style="color: {_ACCENT_COLOR};">.</span></p>
  {body_html}
  <p style="margin: 24px 0 0;">
    <a href="{cta_url}" style="color: {_ACCENT_COLOR}; text-decoration: none; font-weight: 500;">{cta_label} &rarr;</a>
  </p>
  <p style="margin: 32px 0 0; font-size: 12px; color: #888;">
    WhyPolice.com is an independent public archive &amp; forum. Not 911.
  </p>
</div>
""".strip()


def send_email(*, to: str, subject: str, body_html: str, cta_url: str, cta_label: str) -> None:
    """A side effect, not a dependency of the caller's own success — the
    caller (a BackgroundTasks-scheduled function) should never let an
    email failure propagate back into the request that triggered it
    (M3.3's own explicit Bug Fix requirement: "simulate the email
    provider being temporarily down... confirm this doesn't crash or
    fail the underlying API request")."""
    if not is_configured():
        logger.info("Email skipped (Resend not configured): to=%s subject=%r", to, subject)
        return
    if not to:
        logger.warning("Email skipped: no recipient address for subject=%r", subject)
        return

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": _wrap_html(body_html, cta_url, cta_label),
            }
        )
    except Exception:
        # Never let a real provider outage/error propagate into the
        # request that triggered this — logged loudly, not raised.
        logger.exception("Failed to send email to %s (subject=%r)", to, subject)


def send_consultation_requested_email(*, to: str, inquiry_title: str, inquiry_url: str) -> None:
    """Never includes the attorney's direct contact info (Milestone 1's
    privacy rule) — the actual "connect" mechanism stays inside the
    product's own gated flow (accept/decline), not leaked into an email
    body."""
    send_email(
        to=to,
        subject="A verified attorney reviewed your case",
        body_html=(
            f"<p style=\"margin: 0 0 16px;\">A verified attorney has reviewed your inquiry "
            f"&mdash; <strong>{inquiry_title}</strong> &mdash; and requested a consultation.</p>"
            f"<p style=\"margin: 0;\">You can accept or decline the request from your inquiry's page.</p>"
        ),
        cta_url=inquiry_url,
        cta_label="View the request",
    )


def send_new_comment_email(*, to: str, inquiry_title: str, inquiry_url: str) -> None:
    send_email(
        to=to,
        subject=f"New reply on \"{inquiry_title}\"",
        body_html=(
            f"<p style=\"margin: 0;\">There's a new comment on an inquiry you're following "
            f"&mdash; <strong>{inquiry_title}</strong>.</p>"
        ),
        cta_url=inquiry_url,
        cta_label="Read the thread",
    )
