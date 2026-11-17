from app.db.base import Base

# Import models so SQLAlchemy registers their tables.
from app.db.models import User, Document, DocumentChunk


def test_models():
    print("Registered tables:")

    for table_name in Base.metadata.tables:
        print("-", table_name)

    assert "users" in Base.metadata.tables
    assert "documents" in Base.metadata.tables
    assert "document_chunks" in Base.metadata.tables

    print("\nAll three models loaded successfully!")


if __name__ == "__main__":
    test_models()