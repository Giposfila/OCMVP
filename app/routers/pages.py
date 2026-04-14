from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.models import Claim

router = APIRouter()


@router.get("/")
async def landing(request: Request):
    from app.main import templates

    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/history")
async def history_page(request: Request, db: Session = Depends(get_db)):
    from app.main import templates

    user_id = request.session.get("user_id")
    if not user_id:
        return templates.TemplateResponse(
            "history.html", {"request": request, "logged_in": False}
        )

    claims = (
        db.query(Claim)
        .filter(Claim.user_id == uuid.UUID(user_id))
        .filter(Claim.status != "deleted")
        .order_by(Claim.created_at.desc())
        .limit(50)
        .all()
    )

    return templates.TemplateResponse(
        "history.html", {"request": request, "logged_in": True, "claims": claims}
    )
