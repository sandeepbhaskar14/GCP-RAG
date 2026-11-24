import uuid
from pathlib import PurePath

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_verified_email
from app.core.config import settings
from app.db.models import Document
from app.db.repositories.users import get_or_create_user_from_firebase
from app.db.session import get_db
from app.schemas.documents import (
    DocumentResponse,
    DocumentStatusResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.storage import (
    create_signed_upload_url,
    delete_blob,
    get_blob_metadata,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

ALLOWED_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ".txt": {"text/plain"},
    ".csv": {"text/csv", "application/csv"},
}


def _current_user(firebase_user: dict, db: Session):
    uid = firebase_user.get("uid")
    email = firebase_user.get("email")
    if not uid or not email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firebase account must have a valid UID and email.",
        )
    return get_or_create_user_from_firebase(
        db=db,
        firebase_uid=uid,
        email=email,
        name=firebase_user.get("name"),
    )


def _safe_filename(value: str) -> str:
    # Discard path components and reject control characters.
    name = PurePath(value.replace("\\", "/")).name.strip()
    if (
        not name
        or name in {".", ".."}
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file name.",
        )
    return name


def _owned_document(
    db: Session,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


@router.post(
    "/upload-url",
    response_model=UploadUrlResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document_upload_url(
    payload: UploadUrlRequest,
    firebase_user: dict = Depends(require_verified_email),
    db: Session = Depends(get_db),
):
    user = _current_user(firebase_user, db)
    file_name = _safe_filename(payload.file_name)
    suffix = PurePath(file_name).suffix.lower()

    if payload.content_type not in ALLOWED_TYPES.get(suffix, set()):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Allowed types: PDF, DOCX, TXT, CSV.",
        )

    document_id = uuid.uuid4()
    storage_path = (
        f"users/{user.id}/documents/{document_id}/{file_name}"
    )
    document = Document(
        id=document_id,
        user_id=user.id,
        file_name=file_name,
        file_type=payload.content_type,
        storage_path=storage_path,
        file_size=None,
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        upload_url = create_signed_upload_url(
            storage_path=storage_path,
            content_type=payload.content_type,
        )
    except Exception:
        db.delete(document)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Could not create an upload URL. Please try again.",
        )

    return UploadUrlResponse(
        document_id=document.id,
        upload_url=upload_url,
        storage_path=storage_path,
        expires_in_seconds=settings.UPLOAD_URL_EXPIRES_MINUTES * 60,
        required_headers={"Content-Type": payload.content_type},
    )


@router.post(
    "/{document_id}/confirm",
    response_model=DocumentStatusResponse,
)
def confirm_document_upload(
    document_id: uuid.UUID,
    firebase_user: dict = Depends(require_verified_email),
    db: Session = Depends(get_db),
):
    user = _current_user(firebase_user, db)
    document = _owned_document(db, document_id, user.id)

    # A confirmed upload has a persisted positive object size. This makes
    # repeated confirmation requests safe and avoids duplicate processing.
    if document.file_size is not None:
        return DocumentStatusResponse(
            document_id=document.id,
            status=document.status,
        )

    from google.api_core.exceptions import NotFound

    try:
        actual_size, actual_type = get_blob_metadata(document.storage_path)
    except NotFound:
        raise HTTPException(
            status_code=409,
            detail="Uploaded object was not found in storage.",
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not verify the uploaded object.",
        )

    if actual_size <= 0 or actual_size > settings.MAX_DOCUMENT_SIZE_BYTES:
        try:
            delete_blob(document.storage_path)
        finally:
            raise HTTPException(
                status_code=413,
                detail="File is empty or exceeds the maximum upload size.",
            )

    if actual_type != document.file_type:
        delete_blob(document.storage_path)
        raise HTTPException(
            status_code=415,
            detail="Uploaded file content type does not match the request.",
        )

    document.file_size = actual_size
    db.commit()
    db.refresh(document)

    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status,
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    firebase_user: dict = Depends(require_verified_email),
    db: Session = Depends(get_db),
):
    user = _current_user(firebase_user, db)
    statement = (
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.uploaded_at.desc())
    )
    return list(db.scalars(statement).all())


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_details(
    document_id: uuid.UUID,
    firebase_user: dict = Depends(require_verified_email),
    db: Session = Depends(get_db),
):
    user = _current_user(firebase_user, db)
    return _owned_document(db, document_id, user.id)


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
)
def get_document_status(
    document_id: uuid.UUID,
    firebase_user: dict = Depends(require_verified_email),
    db: Session = Depends(get_db),
):
    user = _current_user(firebase_user, db)
    document = _owned_document(db, document_id, user.id)
    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_document(
    document_id: uuid.UUID,
    firebase_user: dict = Depends(require_verified_email),
    db: Session = Depends(get_db),
):
    user = _current_user(firebase_user, db)
    document = _owned_document(db, document_id, user.id)

    try:
        delete_blob(document.storage_path)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not delete the document from storage.",
        )

    db.delete(document)
    db.commit()
    return None
