
from typing import Any

from firebase_admin import auth

from app.core.firebase import initialize_firebase


def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    """
    Verify a Firebase ID token and return its decoded claims.

    Raises Firebase Admin SDK authentication exceptions
    if the token is invalid, expired, or otherwise unverifiable.
    """

    if not id_token or not id_token.strip():
        raise ValueError("Firebase ID token cannot be empty.")

    firebase_app = initialize_firebase()

    decoded_token = auth.verify_id_token(
        id_token,
        app=firebase_app,
    )

    return decoded_token
