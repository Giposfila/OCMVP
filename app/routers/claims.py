import uuid
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Claim, Report, Score, Source
from app.services.claim_service import create_claim as create_claim_service
from app.services.mock_analyzer import mock_analyze
import threading
import asyncio

router = APIRouter()


@router.post("/claims/submit")
async def submit_claim(
    request: Request,
    content_body: str = Form(...),
    source_platform: str = Form(default="Web"),
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        from app.models import UserProfile

        user = db.query(UserProfile).filter(UserProfile.email == "anonymous").first()
        if not user:
            user = UserProfile(
                id=uuid.uuid4(),
                email="anonymous",
                password_hash="",
                role="StandardUser",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = str(user.id)

    claim = create_claim_service(db, content_body, source_platform, uuid.UUID(user_id))

    def run_analysis(claim_id):
        from app.database import SessionLocal

        db2 = SessionLocal()
        try:
            mock_analyze(claim_id, db2)
        finally:
            db2.close()

    thread = threading.Thread(target=run_analysis, args=(claim.id,))
    thread.start()

    return RedirectResponse(f"/claims/{claim.id}/loading", status_code=302)


@router.get("/claims/{claim_id}/loading")
async def loading_page(request: Request, claim_id: uuid.UUID):
    from app.main import templates

    return templates.TemplateResponse(
        "loading.html", {"request": request, "claim_id": claim_id}
    )


@router.get("/claims/{claim_id}/report")
async def report_page(
    request: Request, claim_id: uuid.UUID, db: Session = Depends(get_db)
):
    from app.main import templates

    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if not claim:
        return RedirectResponse("/", status_code=302)

    report = db.query(Report).filter(Report.claim_id == claim_id).first()
    score = db.query(Score).filter(Score.claim_id == claim_id).first()

    user_role = request.session.get("user_role", "Guest")

    sources = db.query(Source).join(Claim.sources).filter(Claim.id == claim_id).all()

    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "claim": claim,
            "report": report,
            "score": score,
            "sources": sources,
            "user_role": user_role,
        },
    )


@router.get("/api/claims/{claim_id}/status")
async def get_claim_status(claim_id: uuid.UUID, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if not claim:
        return {"status": "error", "score_value": None, "confidence_level": None}

    score_value = None
    confidence_level = None

    if claim.status == "completed":
        score_obj = db.query(Score).filter(Score.claim_id == claim_id).first()
        if score_obj:
            score_value = score_obj.score_value
            confidence_level = score_obj.confidence_level

    return {
        "status": claim.status,
        "score_value": score_value,
        "confidence_level": confidence_level,
    }


@router.get("/api/claims")
async def get_claims(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return []

    claims = (
        db.query(Claim)
        .filter(Claim.user_id == uuid.UUID(user_id))
        .filter(Claim.status != "deleted")
        .order_by(Claim.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": str(c.id),
            "content_body": c.content_body[:80],
            "status": c.status,
            "created_at": c.created_at.isoformat(),
        }
        for c in claims
    ]


@router.delete("/api/claims/{claim_id}")
async def delete_claim(claim_id: uuid.UUID, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim:
        claim.status = "deleted"
        db.commit()
    return {"status": "deleted"}


@router.get("/api/claims/{claim_id}")
async def get_claim(claim_id: uuid.UUID, db: Session = Depends(get_db)):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()

    if not claim:
        return {"error": "not found"}

    report = db.query(Report).filter(Report.claim_id == claim_id).first()
    score = db.query(Score).filter(Score.claim_id == claim_id).first()

    return {
        "id": str(claim.id),
        "content_body": claim.content_body,
        "status": claim.status,
        "created_at": claim.created_at.isoformat(),
        "report": {
            "summary_text": report.summary_text,
            "contradictions_found": report.contradictions_found,
        }
        if report
        else None,
        "score": {
            "score_value": score.score_value,
            "confidence_level": score.confidence_level,
        }
        if score
        else None,
    }
