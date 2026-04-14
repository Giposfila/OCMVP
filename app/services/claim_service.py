import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Claim


def create_claim(
    db: Session, content_body: str, source_platform: str, user_id: uuid.UUID
) -> Claim:
    claim = Claim(
        id=uuid.uuid4(),
        content_body=content_body,
        source_platform=source_platform,
        user_id=user_id,
        status="pending",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def get_claim(db: Session, claim_id: uuid.UUID) -> Claim | None:
    return db.query(Claim).filter(Claim.id == claim_id).first()


def get_claims_by_user(
    db: Session, user_id: uuid.UUID, limit: int = 10, offset: int = 0
):
    return (
        db.query(Claim)
        .filter(Claim.user_id == user_id)
        .order_by(Claim.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def delete_claim(db: Session, claim_id: uuid.UUID) -> bool:
    claim = get_claim(db, claim_id)
    if claim:
        claim.status = "deleted"
        db.commit()
        return True
    return False
