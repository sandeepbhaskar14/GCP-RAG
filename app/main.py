from fastapi import FastAPI

from app.api.routes import auth, documents, internal


app = FastAPI(
    title="GCP RAG API",
    description="Authentication, document management, and RAG ingestion API",
    version="1.1.0",
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(internal.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "gcp-rag-api",
    }
