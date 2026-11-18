
import firebase_admin
from firebase_admin import credentials


FIREBASE_PROJECT_ID = "gcp-rag-system"


def initialize_firebase():
    """
    Initialize Firebase Admin SDK using
    Google Application Default Credentials.
    """

    try:
        # Avoid initializing the default app more than once.
        if firebase_admin._apps:
            return firebase_admin.get_app()

        credential = credentials.ApplicationDefault()

        firebase_app = firebase_admin.initialize_app(
            credential,
            options={
                "projectId": FIREBASE_PROJECT_ID,
            },
        )

        print("Firebase Admin SDK initialized successfully.")

        return firebase_app

    except Exception as exc:
        raise RuntimeError(
            f"Firebase initialization failed: {exc}"
        ) from exc
