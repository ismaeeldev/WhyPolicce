"""GCS signed-URL generation — forum rebuild, Milestone 3 Step M3.1
(WhyPoliceForum_MasterGuide.md).

Real google-cloud-storage SDK calls, no mocked signed URLs. Returns None
when GCS_BUCKET_NAME/GCS_SERVICE_ACCOUNT_JSON_PATH aren't configured, so
the router can return an honest 501 (app/routers/billing.py's own
established "not configured yet" pattern) rather than faking a working
upload flow with credentials that don't exist.
"""

import datetime
import logging
import uuid

from google.cloud import storage

from app.core.config import settings

logger = logging.getLogger("whypolice.media")

_SIGNED_URL_EXPIRY = datetime.timedelta(minutes=15)


def is_configured() -> bool:
    return bool(settings.GCS_BUCKET_NAME and settings.GCS_SERVICE_ACCOUNT_JSON_PATH)


def generate_upload_url(*, inquiry_id: uuid.UUID, file_type: str, content_type: str) -> tuple[str, str]:
    """Returns (signed_put_url, public_file_url). Raises if not configured
    — callers must check is_configured() first and return the router's own
    honest 501, not let this raise turn into an unhandled 500."""
    if not is_configured():
        raise RuntimeError("GCS is not configured — call is_configured() first")

    client = storage.Client.from_service_account_json(settings.GCS_SERVICE_ACCOUNT_JSON_PATH)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)

    # Real random object name, not the client-supplied filename — never
    # trust a client-controlled path/filename to build a storage object
    # key (path traversal / collision risk). file_type prefixes the path
    # for easier bucket browsing/future lifecycle rules per type.
    object_name = f"evidence/{file_type}/{inquiry_id}/{uuid.uuid4()}"
    blob = bucket.blob(object_name)

    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=_SIGNED_URL_EXPIRY,
        method="PUT",
        content_type=content_type,
    )
    public_url = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/{object_name}"
    return signed_url, public_url


def blob_exists_for_bucket(file_url: str) -> bool:
    """A real GCS existence check, not a client-side promise — the
    attachments-registration endpoint calls this to confirm the file was
    genuinely uploaded to OUR bucket before creating a DB row for it.
    Rejects any file_url that isn't even shaped like our own bucket's
    public URL (e.g. an attacker passing an arbitrary external URL)
    before making a real API call."""
    if not is_configured():
        raise RuntimeError("GCS is not configured — call is_configured() first")

    prefix = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/"
    if not file_url.startswith(prefix):
        return False
    object_name = file_url[len(prefix):]

    client = storage.Client.from_service_account_json(settings.GCS_SERVICE_ACCOUNT_JSON_PATH)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    return bucket.blob(object_name).exists()


# M3.1 Bug Fix decision (user-confirmed, in scope): verify the uploaded
# file's REAL bytes match the claimed file_type before trusting it, not
# just the client-declared value — catches a spoofed upload (e.g.
# claiming "image" for an actual video file). A minimal, dependency-free
# magic-byte signature table for the file types this app actually
# accepts, rather than pulling in python-magic/libmagic (a real
# cross-platform packaging headache, especially on Windows dev machines,
# for a check this narrow in scope).
_MAGIC_BYTES: dict[str, list[bytes]] = {
    "image": [
        b"\xff\xd8\xff",  # JPEG
        b"\x89PNG\r\n\x1a\n",  # PNG
        b"GIF87a",
        b"GIF89a",
        b"RIFF",  # WebP (RIFF....WEBP — checked further below)
    ],
    "video": [
        b"\x00\x00\x00\x18ftyp",  # MP4 (common offset)
        b"\x00\x00\x00\x1cftyp",
        b"\x00\x00\x00\x20ftyp",
        b"\x1aE\xdf\xa3",  # WebM/Matroska
        b"RIFF",  # AVI (RIFF....AVI  — checked further below)
    ],
    "document": [
        b"%PDF-",
    ],
}
_SNIFF_BYTES = 32


def sniff_matches_claimed_type(file_url: str, claimed_file_type: str) -> bool:
    """Downloads only the first _SNIFF_BYTES of the real uploaded blob
    (a ranged GCS read, not the whole file) and checks its real magic-byte
    signature against the claimed file_type. Returns False for a genuine
    mismatch (spoofed upload) or a file too short/unrecognized to verify
    — the caller decides whether an unrecognized-but-plausible format
    should still be allowed or rejected; this function only answers
    "does this look like what it claims to be," it never guesses."""
    if not is_configured():
        raise RuntimeError("GCS is not configured — call is_configured() first")

    prefix = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/"
    if not file_url.startswith(prefix):
        return False
    object_name = file_url[len(prefix):]

    client = storage.Client.from_service_account_json(settings.GCS_SERVICE_ACCOUNT_JSON_PATH)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)
    header = blob.download_as_bytes(start=0, end=_SNIFF_BYTES - 1)

    signatures = _MAGIC_BYTES.get(claimed_file_type, [])
    for sig in signatures:
        if sig == b"RIFF":
            # WebP/AVI both start with RIFF, differentiated by a format
            # tag at byte offset 8 — check that explicitly rather than
            # matching any RIFF container as a false positive.
            if header.startswith(b"RIFF") and len(header) >= 12:
                tag = header[8:12]
                if claimed_file_type == "image" and tag == b"WEBP":
                    return True
                if claimed_file_type == "video" and tag == b"AVI ":
                    return True
            continue
        if header.startswith(sig):
            return True
    return False
