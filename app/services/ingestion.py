import hashlib
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Document, DocumentChunk
from app.services.chunking import create_chunks
from app.services.embeddings import embed_documents
from app.services.extraction import InvalidDocumentError, extract_document
from app.services.storage import download_blob


logger = logging.getLogger(__name__)


def process_document(db: Session, document_id: uuid.UUID) -> str:
    document = db.scalar(
        select(Document).where(Document.id == document_id)
    )
    if document is None:
        return "not_found"
    if document.status == "completed":
        return "completed"

    document.status = "processing"
    db.commit()

    try:
        data = download_blob(document.storage_path)
        if len(data) != document.file_size:
            raise InvalidDocumentError("Stored file size does not match the confirmed upload.")
        if len(data) > settings.MAX_DOCUMENT_SIZE_BYTES:
            raise InvalidDocumentError("Document exceeds the maximum allowed size.")

        sections = extract_document(data, document.file_name, document.file_type)
        chunks = create_chunks(sections)
        if not chunks:
            raise InvalidDocumentError("No extractable text was found in this document.")

        vectors = embed_documents([chunk.content for chunk in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding count does not match chunk count.")

        # Replace all chunks in one transaction only after extraction and embedding succeed.
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.user_id == document.user_id,
            )
        )
        for chunk, vector in zip(chunks, vectors):
            content_hash = hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()
            db.add(
                DocumentChunk(
                    user_id=document.user_id,
                    document_id=document.id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=vector,
                    chunk_metadata=chunk.metadata,
                    content_hash=content_hash,
                )
            )

        document.status = "completed"
        db.commit()
        logger.info(
            "Document ingestion completed",
            extra={"document_id": str(document.id), "chunk_count": len(chunks)},
        )
        return "completed"

    except InvalidDocumentError:
        db.rollback()
        current = db.scalar(select(Document).where(Document.id == document_id))
        if current is not None:
            current.status = "failed"
            db.commit()
        logger.warning("Document rejected during ingestion: %s", document_id, exc_info=True)
        raise
    except Exception:
        db.rollback()
        current = db.scalar(select(Document).where(Document.id == document_id))
        if current is not None:
            current.status = "failed"
            db.commit()
        logger.exception("Document ingestion failed: %s", document_id)
        raise
