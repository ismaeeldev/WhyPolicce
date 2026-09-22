"""Tests for app/services/email_service.py — forum rebuild, Milestone 3
Step M3.3 (WhyPoliceForum_MasterGuide.md).

No real Resend API key exists in this environment yet (Manual Step
still pending — the developer's own choice of provider, per the guide's
"agent's/developer's choice" instruction). Mirrors this project's own
established pattern: confirm the real, honest skip-and-log behavior
when not configured, then mock only resend.Emails.send itself.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import email_service


class TestSendEmailNotConfigured:
    def test_skips_silently_when_not_configured(self, caplog):
        with patch("app.services.email_service.settings.RESEND_API_KEY", ""):
            with caplog.at_level("INFO"):
                email_service.send_email(
                    to="citizen@test.example",
                    subject="Test",
                    body_html="<p>hi</p>",
                    cta_url="https://example.com",
                    cta_label="View",
                )
        assert "Email skipped" in caplog.text
        assert "citizen@test.example" in caplog.text


class TestSendEmailConfigured:
    def test_calls_resend_with_real_recipient_and_subject(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", "re_test_fake")
        monkeypatch.setattr("app.services.email_service.settings.RESEND_FROM_EMAIL", "WhyPolice <test@whypolice.com>")

        with patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_email(
                to="citizen@test.example",
                subject="A verified attorney reviewed your case",
                body_html="<p>details</p>",
                cta_url="https://whypolice.com/inquiries/abc",
                cta_label="View the request",
            )

        mock_send.assert_called_once()
        (call_arg,) = mock_send.call_args.args
        assert call_arg["to"] == ["citizen@test.example"]
        assert call_arg["from"] == "WhyPolice <test@whypolice.com>"
        assert call_arg["subject"] == "A verified attorney reviewed your case"
        assert "View the request" in call_arg["html"]
        assert "https://whypolice.com/inquiries/abc" in call_arg["html"]

    def test_missing_recipient_skips_without_calling_resend(self, monkeypatch: pytest.MonkeyPatch, caplog):
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", "re_test_fake")
        with patch("app.services.email_service.resend.Emails.send") as mock_send:
            with caplog.at_level("WARNING"):
                email_service.send_email(to="", subject="x", body_html="x", cta_url="x", cta_label="x")
        mock_send.assert_not_called()
        assert "no recipient" in caplog.text

    def test_provider_error_is_logged_not_raised(self, monkeypatch: pytest.MonkeyPatch, caplog):
        """M3.3's own explicit Bug Fix requirement: simulating the email
        provider being down must not crash or propagate into the caller —
        the caller (a BackgroundTasks job) has no way to handle an
        exception raised after the real HTTP response was already sent."""
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", "re_test_fake")
        with patch("app.services.email_service.resend.Emails.send", side_effect=RuntimeError("provider down")):
            with caplog.at_level("ERROR"):
                # Must not raise.
                email_service.send_email(
                    to="citizen@test.example", subject="x", body_html="x", cta_url="x", cta_label="x"
                )
        assert "Failed to send email" in caplog.text

    def test_attorney_email_never_includes_attorney_contact_info(self, monkeypatch: pytest.MonkeyPatch):
        """Milestone 1's privacy rule, re-applied here: the consultation-
        requested email tells the CITIZEN a verified attorney reviewed
        their case, but must never leak any attorney-identifying info
        (email, bar number) into the email body — the real "connect"
        mechanism is the product's own gated accept/decline flow."""
        monkeypatch.setattr("app.services.email_service.settings.RESEND_API_KEY", "re_test_fake")
        with patch("app.services.email_service.resend.Emails.send") as mock_send:
            email_service.send_consultation_requested_email(
                to="citizen@test.example",
                inquiry_title="Missing person report",
                inquiry_url="https://whypolice.com/inquiries/xyz",
            )
        (call_arg,) = mock_send.call_args.args
        assert "attorney@" not in call_arg["html"]
        assert "bar" not in call_arg["html"].lower() or "verified attorney" in call_arg["html"].lower()
