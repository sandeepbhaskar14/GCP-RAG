import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.extraction import InvalidDocumentError
from app.services.ingestion import process_document


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/tasks", tags=["Internal tasks"])


class IngestionTaskRequest(BaseModel):
    document_id: uuid.UUID


def verify_task_invoker(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing task token.")

    if not settings.TASK_INVOKER_SERVICE_ACCOUNT or not settings.TASK_OIDC_AUDIENCE:
        raise HTTPException(status_code=503, detail="Task authentication is not configured.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = id_token.verify_oauth2_token(
            token,
            Request(),
            audience=settings.TASK_OIDC_AUDIENCE,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid task token.") from exc

    if (
        claims.get("email") != settings.TASK_INVOKER_SERVICE_ACCOUNT
        or claims.get("email_verified") is not True
    ):
        raise HTTPException(status_code=403, detail="Task caller is not permitted.")


@router.post("/ingest-document", dependencies=[Depends(verify_task_invoker)])
def ingest_document_task(
    payload: IngestionTaskRequest,
    db: Session = Depends(get_db),
):
    try:
        result = process_document(db, payload.document_id)
        return {"document_id": str(payload.document_id), "status": result}
    except InvalidDocumentError:
        # Permanent parsing/validation failures should not be retried by Cloud Tasks.
        return {"document_id": str(payload.document_id), "status": "failed"}
    except Exception:
        logger.exception("Retryable ingestion task failure for %s", payload.document_id)
        raise HTTPException(status_code=500, detail="Document ingestion failed; retry the task.")
