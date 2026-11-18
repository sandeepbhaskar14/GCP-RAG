import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document


def create_document(
    db: Session,
    user_id: uuid.UUID,
    file_name: str,
    file_type: str,
    storage_path: str,
    file_size: int | None = None,
) -> Document:

    document = Document(
        user_id=user_id,
        file_name=file_name,
        file_type=file_type,
        storage_path=storage_path,
        file_size=file_size,
        status="pending",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def get_document(
    db: Session,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document | None:

    statement = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id,
    )

    return db.scalar(statement)


def get_user_documents(
    db: Session,
    user_id: uuid.UUID,
) -> list[Document]:

    statement = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.uploaded_at.desc())
    )

    return list(db.scalars(statement).all())


def update_document_status(
    db: Session,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
) -> Document | None:

    document = get_document(
        db,
        document_id,
        user_id,
    )

    if document is None:
        return None

    allowed_statuses = {
        "pending",
        "processing",
        "completed",
        "failed",
        "deleting",
    }

    if status not in allowed_statuses:
        raise ValueError("Invalid document status")

    document.status = status

    db.commit()
    db.refresh(document)

    return document


def delete_document(
    db: Session,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:

    document = get_document(
        db,
        document_id,
        user_id,
    )

    if document is None:
        return False

    db.delete(document)
    db.commit()

    return True