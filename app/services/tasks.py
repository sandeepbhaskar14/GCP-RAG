import hashlib
import json

from google.api_core.exceptions import AlreadyExists
from google.cloud import tasks_v2

from app.core.config import settings


def enqueue_document_ingestion(document_id: str) -> None:
    if not settings.CLOUD_TASKS_ENABLED:
        return

    required = (
        settings.GOOGLE_CLOUD_PROJECT,
        settings.CLOUD_TASKS_QUEUE,
        settings.CLOUD_TASKS_LOCATION,
        settings.INGESTION_WORKER_URL,
        settings.TASK_INVOKER_SERVICE_ACCOUNT,
        settings.TASK_OIDC_AUDIENCE,
    )
    if not all(required):
        raise RuntimeError("Cloud Tasks ingestion configuration is incomplete.")

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        settings.GOOGLE_CLOUD_PROJECT,
        settings.CLOUD_TASKS_LOCATION,
        settings.CLOUD_TASKS_QUEUE,
    )
    task_id = "ingest-" + hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:32]
    task_name = client.task_path(
        settings.GOOGLE_CLOUD_PROJECT,
        settings.CLOUD_TASKS_LOCATION,
        settings.CLOUD_TASKS_QUEUE,
        task_id,
    )
    task = {
        "name": task_name,
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": settings.INGESTION_WORKER_URL,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"document_id": document_id}).encode("utf-8"),
            "oidc_token": {
                "service_account_email": settings.TASK_INVOKER_SERVICE_ACCOUNT,
                "audience": settings.TASK_OIDC_AUDIENCE,
            },
        },
    }

    try:
        client.create_task(request={"parent": parent, "task": task})
    except AlreadyExists:
        # A deterministic task name makes repeated confirmation requests safe.
        pass
    finally:
        client.close()
