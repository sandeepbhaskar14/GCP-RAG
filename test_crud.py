from app.db.session import SessionLocal

from app.db.repositories.users import create_user
from app.db.repositories.documents import (
    create_document,
    get_user_documents,
    get_document,
    update_document_status,
    delete_document,
)


def test_crud():

    db = SessionLocal()

    try:
        # 1. Create a test user
        user = create_user(
            db=db,
            firebase_uid="test_firebase_uid_001",
            email="rag_test@example.com",
            name="RAG Test User",
        )

        print("User created:", user.id)

        # 2. Create a document
        document = create_document(
            db=db,
            user_id=user.id,
            file_name="sample.pdf",
            file_type="application/pdf",
            storage_path=f"users/{user.id}/sample.pdf",
            file_size=1024,
        )

        print("Document created:", document.id)

        # 3. Retrieve user's documents
        documents = get_user_documents(
            db=db,
            user_id=user.id,
        )

        print("User document count:", len(documents))

        # 4. Retrieve document with ownership check
        retrieved = get_document(
            db=db,
            document_id=document.id,
            user_id=user.id,
        )

        print("Document retrieved:", retrieved.file_name)

        # 5. Update document status
        updated = update_document_status(
            db=db,
            document_id=document.id,
            user_id=user.id,
            status="processing",
        )

        print("Updated status:", updated.status)

        # 6. Test ownership isolation
        import uuid

        unauthorized = get_document(
            db=db,
            document_id=document.id,
            user_id=uuid.uuid4(),
        )

        print("Unauthorized access:", unauthorized)

        assert unauthorized is None

        # 7. Delete document
        deleted = delete_document(
            db=db,
            document_id=document.id,
            user_id=user.id,
        )

        print("Document deleted:", deleted)

        assert deleted is True

        # 8. Clean up test user
        db.delete(user)
        db.commit()

        print("\nCRUD tests completed successfully!")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    test_crud()