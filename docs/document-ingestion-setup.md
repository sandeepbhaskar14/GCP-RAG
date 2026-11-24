# Document ingestion

## Workflow

1. The authenticated client requests a signed upload URL.
2. The client uploads the file directly to the private Cloud Storage bucket.
3. The client confirms the upload.
4. The API enqueues a deterministic Cloud Task when \`CLOUD_TASKS_ENABLED=true\`.
5. Cloud Tasks calls \`POST /internal/tasks/ingest-document\` with an OIDC token.
6. The worker verifies the token's audience and service-account email.
7. The worker downloads and validates the file, extracts text, chunks it, generates Vertex AI embeddings, and stores chunks in PostgreSQL/pgvector.
8. The document status becomes \`completed\` or \`failed\`.

The worker accepts only a document UUID. It loads the document and its owner from PostgreSQL; it never trusts a client-supplied user ID.

## Embedding and chunk configuration

The existing \`document_chunks.embedding\` column is \`vector(768)\`. The default model is \`text-embedding-005\`, which returns 768-dimensional vectors and is specialized for English. Keep the model and database vector dimension aligned. If multilingual support is required, evaluate a multilingual model and migrate the vector column before changing the configured model.

Defaults:
- Chunk size: 1,200 characters
- Overlap: 150 characters
- Embedding batch size: 32 texts
- Maximum upload: 25 MiB
- PDF maximum: 1,000 pages
- CSV maximum: 100,000 data rows

Image-only PDFs are not OCR processed in this milestone. Password-protected PDFs and non-UTF-8 TXT/CSV files are rejected.

## GCP setup

Enable APIs:

\`\`\`bash
gcloud services enable cloudtasks.googleapis.com aiplatform.googleapis.com
\`\`\`

Create the queue:

\`\`\`bash
gcloud tasks queues create document-ingestion \\
  --location=asia-south1 \\
  --project=gcp-rag-system
\`\`\`

Create a dedicated task invoker identity if one does not already exist:

\`\`\`bash
gcloud iam service-accounts create rag-task-invoker \\
  --display-name="RAG Cloud Tasks Invoker" \\
  --project=gcp-rag-system
\`\`\`

Grant the task invoker permission to call the Cloud Run service:

\`\`\`bash
gcloud run services add-iam-policy-binding YOUR_CLOUD_RUN_SERVICE \\
  --region=asia-south1 \\
  --member="serviceAccount:rag-task-invoker@gcp-rag-system.iam.gserviceaccount.com" \\
  --role="roles/run.invoker" \\
  --project=gcp-rag-system
\`\`\`

The API runtime service account needs:
- \`roles/cloudtasks.enqueuer\` to enqueue tasks.
- \`roles/iam.serviceAccountUser\` on the task invoker service account (to attach it to tasks).
- \`roles/aiplatform.user\` to call Vertex AI.
- \`storage.objects.get\` on the private document bucket.

The Cloud Tasks service agent must retain its \`roles/cloudtasks.serviceAgent\` role and receive \`roles/iam.serviceAccountUser\` on the task invoker service account so it can mint OIDC tokens. The task invoker service account must be in the same project as the queue.

Grant the Cloud Tasks service agent permission to use the task invoker identity:

\`\`\`bash
PROJECT_NUMBER=$(gcloud projects describe gcp-rag-system --format="value(projectNumber)")
gcloud iam service-accounts add-iam-policy-binding \\
  rag-task-invoker@gcp-rag-system.iam.gserviceaccount.com \\
  --member="serviceAccount:service-\${PROJECT_NUMBER}@gcp-sa-cloudtasks.iam.gserviceaccount.com" \\
  --role="roles/iam.serviceAccountUser" \\
  --project=gcp-rag-system
\`\`\`

Set these Cloud Run environment variables:
- \`CLOUD_TASKS_ENABLED=true\`
- \`CLOUD_TASKS_QUEUE=document-ingestion\`
- \`CLOUD_TASKS_LOCATION=asia-south1\`
- \`INGESTION_WORKER_URL=https://YOUR_CLOUD_RUN_SERVICE.run.app/internal/tasks/ingest-document\`
- \`TASK_INVOKER_SERVICE_ACCOUNT=rag-task-invoker@gcp-rag-system.iam.gserviceaccount.com\`
- \`TASK_OIDC_AUDIENCE=https://YOUR_CLOUD_RUN_SERVICE.run.app\`
- \`GOOGLE_CLOUD_PROJECT=gcp-rag-system\`
- \`GOOGLE_CLOUD_LOCATION=asia-south1\`

The audience must match the audience configured for the worker token. The worker validates the task token's audience and service-account email in application code.

## Local development

Install dependencies and authenticate ADC:

\`\`\`bash
pip install -r requirements.txt
gcloud auth application-default login
\`\`\`

Keep \`CLOUD_TASKS_ENABLED=false\` locally unless the worker is deployed to Cloud Run and the queue is configured. With the queue disabled, confirmation leaves the document in \`pending\`; test extraction/chunking/embedding functions independently or run the deployed worker path.

## Operational notes

- Cloud Tasks retries non-2xx worker responses. Invalid or unsupported documents are marked failed and acknowledged to avoid retrying permanent errors.
- Processing is idempotent for completed documents. Chunks are replaced in a single database transaction after all embeddings are ready.
- A transient failure can incur another embedding call when Cloud Tasks retries. Monitor task retry counts and Vertex AI usage.
- The current 25 MiB limit is checked at confirmation and again before worker download. The signed PUT URL does not enforce a pre-upload content-length limit; tighten this before production.
