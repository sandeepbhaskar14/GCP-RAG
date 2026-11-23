
from typing import Any

from firebase_admin import auth

from app.core.firebase import initialize_firebase


def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    """
    Verify Firebase ID token, including revocation
    and disabled-account checks.
    """

    if not id_token or not id_token.strip():
        raise ValueError("Firebase ID token cannot be empty.")

    firebase_app = initialize_firebase()

    decoded_token = auth.verify_id_token(
        id_token,
        app=firebase_app,
        check_revoked=True,
    )

    return decoded_token
