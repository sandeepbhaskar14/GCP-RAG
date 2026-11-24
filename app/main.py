from fastapi import FastAPI

from app.api.routes import auth, documents


app = FastAPI(
    title="GCP RAG API",
    description="Authentication and Retrieval-Augmented Generation API",
    version="1.0.0",
)


# Register API routers
app.include_router(auth.router)
app.include_router(documents.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "gcp-rag-api",
    }
