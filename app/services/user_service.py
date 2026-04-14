import uuid
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from app.models import UserProfile


def create_user(
    db: Session, email: str, password: str, role: str = "StandardUser"
) -> UserProfile:
    user = UserProfile(
        id=uuid.uuid4(),
        email=email,
        password_hash=bcrypt.hash(password),
        role=role,
        preferences={},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.email == email).first()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.verify(plain_password, hashed_password)
