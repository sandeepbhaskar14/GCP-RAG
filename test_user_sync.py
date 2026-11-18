
from app.db.session import SessionLocal
from app.db.repositories.users import (
    get_or_create_user_from_firebase,
)


def test_user_sync():
    db = SessionLocal()

    try:
        firebase_uid = "SwjrP052zNXjPvwLVKUqwWUOl4k2"

        user = get_or_create_user_from_firebase(
            db=db,
            firebase_uid=firebase_uid,
            email="sandeep.bhaskar@gammaedge.io",
            name="Sandeep",
        )

        print("User synchronized successfully!")
        print("PostgreSQL UUID:", user.id)
        print("Firebase UID:", user.firebase_uid)
        print("Email:", user.email)

        # Call it again to verify that the existing
        # PostgreSQL record is reused.
        second_user = get_or_create_user_from_firebase(
            db=db,
            firebase_uid=firebase_uid,
            email="sandeep.bhaskar@gammaedge.io",
            name="Sandeep",
        )

        assert user.id == second_user.id

        print("Existing user reused successfully!")
        print("User synchronization test passed!")

    finally:
        db.close()


if __name__ == "__main__":
    test_user_sync()
