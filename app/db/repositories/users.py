from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.models import User


def get_user_by_firebase_uid(
    db: Session,
    firebase_uid: str,
) -> User | None:

    statement = select(User).where(
        User.firebase_uid == firebase_uid
    )

    return db.scalar(statement)


def get_user_by_id(
    db: Session,
    user_id,
) -> User | None:

    statement = select(User).where(
        User.id == user_id
    )

    return db.scalar(statement)


def create_user(
    db: Session,
    firebase_uid: str,
    email: str,
    name: str | None = None,
) -> User:

    user = User(
        firebase_uid=firebase_uid,
        email=email,
        name=name,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_or_create_user_from_firebase(
    db: Session,
    firebase_uid: str,
    email: str,
    name: str | None = None,
) -> User:
    """
    Find an application user by Firebase UID.

    If the user does not exist, create a new PostgreSQL user.
    Synchronize email and name when an existing user's profile changes.
    """

    if not firebase_uid or not firebase_uid.strip():
        raise ValueError("Firebase UID cannot be empty.")

    if not email or not email.strip():
        raise ValueError("Email cannot be empty.")

    # 1. Check whether this Firebase user already exists.
    user = get_user_by_firebase_uid(db, firebase_uid)

    if user:
        # 2. Synchronize profile information.
        changed = False

        if user.email != email:
            user.email = email
            changed = True

        if name is not None and user.name != name:
            user.name = name
            changed = True

        if changed:
            try:
                db.commit()
                db.refresh(user)
            except IntegrityError:
                db.rollback()
                raise

        return user

    # 3. Create a new application user.
    user = User(
        firebase_uid=firebase_uid,
        email=email,
        name=name,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)

        return user

    except IntegrityError:
        # Handle concurrent requests attempting to create
        # the same Firebase user.
        db.rollback()

        existing_user = get_user_by_firebase_uid(
            db,
            firebase_uid,
        )

        if existing_user:
            return existing_user

        # For example, the email might already belong
        # to another Firebase UID.
        raise
