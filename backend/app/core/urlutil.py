"""URL hygiene for user-supplied links that are later rendered as hrefs."""
from urllib.parse import urlparse


def normalize_website(value: str | None) -> str | None:
    """Returns an absolute http(s) URL, or None if `value` is empty or not a
    safe web address. A bare "yourfirm.com" gets https:// prepended; any other
    scheme (javascript:, data:, file:, ...) is rejected so the stored value can
    never execute script when rendered as a link."""
    if not value or not value.strip():
        return None
    candidate = value.strip()
    if "://" not in candidate:
        # "javascript:alert(1)" has a scheme but no "://" — don't treat it as a host.
        head = candidate.split("/", 1)[0]
        if ":" in head and not head.rsplit(":", 1)[1].isdigit():
            return None
        candidate = f"https://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or " " in candidate:
        return None
    return candidate
