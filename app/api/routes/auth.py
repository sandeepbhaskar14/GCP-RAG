
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_firebase_user
from app.db.session import get_db
from app.db.repositories.users import get_or_create_user_from_firebase


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.get("/me")
def get_authenticated_user(
    firebase_user: dict = Depends(get_current_firebase_user),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated application's user profile.

    Firebase UID is obtained exclusively from the verified token.
    """

    firebase_uid = firebase_user.get("uid")
    email = firebase_user.get("email")
    name = firebase_user.get("name")

    if not firebase_uid or not email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firebase account must have a valid UID and email.",
        )

    user = get_or_create_user_from_firebase(
        db=db,
        firebase_uid=firebase_uid,
        email=email,
        name=name,
    )

    return {
        "id": str(user.id),
        "firebase_uid": user.firebase_uid,
        "email": user.email,
        "name": user.name,
        "subscription_tier": user.subscription_tier,
        "user_role": user.user_role,
    }
