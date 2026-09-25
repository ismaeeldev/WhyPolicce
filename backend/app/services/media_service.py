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
import os
import uuid

from google.cloud import storage

from app.core.config import settings

logger = logging.getLogger("whypolice.media")

_SIGNED_URL_EXPIRY = datetime.timedelta(minutes=15)


def is_configured() -> bool:
    """Real gap found during a credential-activation readiness audit: this
    used to only check that GCS_SERVICE_ACCOUNT_JSON_PATH was a non-empty
    string, never that the file actually exists at that path. The moment
    real credentials are attached, a wrong/missing path (a very easy
    mistake in a container deploy — see the Dockerfile note on
    generate_upload_url below) would pass this check, open the 501 gate,
    and then every upload/register/delete call would raise a raw
    FileNotFoundError from from_service_account_json, swallowed by the
    global exception handler into a generic 500 with zero indication the
    real cause is a missing credentials file. Checking os.path.exists
    here means a misconfigured deploy fails this same honest 501 instead
    of a confusing 500, and the real cause is loggable right here."""
    if not settings.GCS_BUCKET_NAME or not settings.GCS_SERVICE_ACCOUNT_JSON_PATH:
        return False
    if not os.path.isfile(settings.GCS_SERVICE_ACCOUNT_JSON_PATH):
        logger.warning(
            "GCS_SERVICE_ACCOUNT_JSON_PATH is set to %r but no file exists there — treating GCS as unconfigured",
            settings.GCS_SERVICE_ACCOUNT_JSON_PATH,
        )
        return False
    return True


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


def get_blob_size(file_url: str) -> int | None:
    """The real, authoritative byte size of the uploaded blob — the
    attachments-registration endpoint uses this instead of trusting the
    client-reported size_bytes, which a malicious or buggy client could
    under-report to slip a much larger file past the free/expanded tier's
    cumulative-byte cap. Returns None if the URL isn't shaped like our
    own bucket's public URL or the blob metadata can't be read (caller
    treats that the same as blob_exists_for_bucket returning False)."""
    if not is_configured():
        raise RuntimeError("GCS is not configured — call is_configured() first")

    prefix = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/"
    if not file_url.startswith(prefix):
        return None
    object_name = file_url[len(prefix):]

    client = storage.Client.from_service_account_json(settings.GCS_SERVICE_ACCOUNT_JSON_PATH)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)
    blob.reload()
    return blob.size


def list_evidence_blobs(*, older_than: "datetime.datetime | None" = None) -> list[str]:
    """Lists every object under the evidence/ prefix (every uploaded
    file, across every inquiry/file-type subfolder), returned as full
    public file_urls in the exact shape evidence_attachments.file_url
    stores them — so callers can diff this list against real DB rows.

    older_than optionally filters to only blobs whose creation time is
    at or before that timestamp — used by the orphan-cleanup job to
    apply a grace period, so a genuinely in-flight upload (GCS PUT
    already succeeded, but the client hasn't called the register-
    attachment endpoint yet, which is exactly the window
    EvidenceUploadField's own progress bar spans) is never mistaken for
    an orphan."""
    if not is_configured():
        raise RuntimeError("GCS is not configured — call is_configured() first")

    client = storage.Client.from_service_account_json(settings.GCS_SERVICE_ACCOUNT_JSON_PATH)
    bucket_name = settings.GCS_BUCKET_NAME
    urls = []
    for blob in client.list_blobs(bucket_name, prefix="evidence/"):
        if older_than is not None and blob.time_created is not None and blob.time_created > older_than:
            continue
        urls.append(f"https://storage.googleapis.com/{bucket_name}/{blob.name}")
    return urls


def delete_blob(file_url: str) -> None:
    """Real gap found during a full-scope re-audit: the attachments-
    delete endpoint used to only remove the DB row, deliberately leaving
    the GCS object in place (a documented, intentional scope decision at
    the time). The real consequence of that decision was never actually
    fully worked through: there is no background GC job anywhere in this
    codebase, so a "deleted" attachment's file stays publicly fetchable
    at its storage.googleapis.com URL forever. For a police-incident
    forum, where an uploaded file may show a citizen's own face, plate,
    or location, a "delete" that shows success while the file stays
    public is a real privacy failure, not just an unbounded storage-cost
    concern. Same file_url-shape validation as blob_exists_for_bucket —
    never accepts a URL that isn't shaped like our own bucket's object,
    and deleting a blob that's already gone (a retried request, a race
    with a previous delete) is treated as success, not an error."""
    if not is_configured():
        raise RuntimeError("GCS is not configured — call is_configured() first")

    prefix = f"https://storage.googleapis.com/{settings.GCS_BUCKET_NAME}/"
    if not file_url.startswith(prefix):
        return
    object_name = file_url[len(prefix):]

    client = storage.Client.from_service_account_json(settings.GCS_SERVICE_ACCOUNT_JSON_PATH)
    bucket = client.bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_name)
    try:
        blob.delete()
    except Exception as exc:
        if getattr(exc, "code", None) == 404:
            return
        raise


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
