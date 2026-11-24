from datetime import timedelta

import google.auth
from google.auth.transport.requests import Request
from google.cloud import storage
from google.api_core.exceptions import NotFound

from app.core.config import settings
from app.services.extraction import InvalidDocumentError


def _bucket():
    return storage.Client().bucket(settings.GCS_BUCKET_NAME)


def create_signed_upload_url(
    storage_path: str,
    content_type: str,
) -> str:
    """Create a short-lived V4 signed URL for a direct GCS PUT upload."""
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())

    service_account_email = (
        settings.GCS_SIGNING_SERVICE_ACCOUNT
        or getattr(credentials, "service_account_email", None)
    )
    if not service_account_email:
        raise RuntimeError(
            "Set GCS_SIGNING_SERVICE_ACCOUNT to the API service account email."
        )

    blob = _bucket().blob(storage_path)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(
            minutes=settings.UPLOAD_URL_EXPIRES_MINUTES
        ),
        method="PUT",
        content_type=content_type,
        headers={"x-goog-if-generation-match": "0"},
        service_account_email=service_account_email,
        access_token=credentials.token,
    )


def get_blob_metadata(storage_path: str) -> tuple[int, str | None]:
    blob = _bucket().blob(storage_path)
    blob.reload()
    return int(blob.size or 0), blob.content_type


def download_blob(storage_path: str) -> bytes:
    """Download a confirmed object after checking its size metadata."""
    blob = _bucket().blob(storage_path)
    try:
        blob.reload()
    except NotFound as exc:
        raise InvalidDocumentError("Uploaded object no longer exists in storage.") from exc

    size = int(blob.size or 0)
    if size <= 0 or size > settings.MAX_DOCUMENT_SIZE_BYTES:
        raise InvalidDocumentError("Stored object has an invalid size.")
    return blob.download_as_bytes(checksum="auto", raw_download=True)


def delete_blob(storage_path: str) -> None:
    """Delete an object; a missing object is already in the desired state."""
    try:
        _bucket().blob(storage_path).delete()
    except NotFound:
        pass
