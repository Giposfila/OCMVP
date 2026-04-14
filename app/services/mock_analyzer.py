import uuid
import random
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Claim


def update_claim_status(claim_id: uuid.UUID, status: str, db: Session):
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim:
        claim.status = status
        db.commit()


def create_mock_sources(db: Session, sources_data: list[dict]):
    from app.models import Source

    sources = []
    for s_data in sources_data:
        source = Source(
            id=uuid.uuid4(),
            url=s_data["url"],
            source_type=s_data["source_type"],
            trust_level=s_data["trust_level"],
            retrieved_at=datetime.utcnow(),
        )
        db.add(source)
        sources.append(source)
    db.commit()
    return sources


def mock_analyze(claim_id: uuid.UUID, db: Session = None):
    from app.models import Report, Score, Source, Rebuttal, ClaimSources
    from app.database import SessionLocal

    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        update_claim_status(claim_id, "processing", db)

        import time

        time.sleep(random.uniform(4, 8))

        score = random.randint(15, 95)
        contradictions = random.randint(0, 5)

        confidence = "high" if score > 65 else "medium" if score > 35 else "low"

        mock_sources_data = [
            {
                "url": "https://cbr.ru/press/pr/",
                "source_type": "official_registry",
                "trust_level": 95,
            },
            {
                "url": "https://ria.ru/economy/",
                "source_type": "media",
                "trust_level": 72,
            },
            {
                "url": "https://tass.ru/economy",
                "source_type": "media",
                "trust_level": 68,
            },
        ]

        sources = create_mock_sources(db, mock_sources_data)

        summary_templates = [
            f"Анализ выявил {contradictions} противоречия с данными из официальных реестров. "
            f"Ключевые цифры в тексте {'совпадают' if score > 60 else 'расходятся'} с данными ЦБ РФ. "
            f"Рекомендуется {'принять к сведению' if score > 60 else 'перепроверить'} информацию.",
            f"Система обнаружила {contradictions} несоответствия между заявленными фактами и первоисточниками. "
            f"Индекс аргументации {score}/100 указывает на {'высокий' if score > 60 else 'низкий'} уровень достоверности.",
        ]

        rebuttal_text = (
            f"✅ Проверено VerifyAI | Индекс: {score}/100\n"
            f"{'Информация подтверждена' if score > 60 else 'Требует проверки'} — "
            f"найдено {contradictions} противоречий с официальными источниками.\n"
            f"Подробный отчёт: [ссылка]"
        )

        summary = random.choice(summary_templates)

        report = Report(
            id=uuid.uuid4(),
            claim_id=claim_id,
            summary_text=summary,
            contradictions_found=contradictions,
            generated_at=datetime.utcnow(),
        )
        db.add(report)

        score_obj = Score(
            id=uuid.uuid4(),
            claim_id=claim_id,
            score_value=score,
            confidence_level=confidence,
            calculated_at=datetime.utcnow(),
        )
        db.add(score_obj)

        rebuttal = Rebuttal(
            id=uuid.uuid4(),
            report_id=report.id,
            text_content=rebuttal_text,
            created_at=datetime.utcnow(),
        )
        db.add(rebuttal)

        for source in sources:
            claim_source = ClaimSources(claim_id=claim_id, source_id=source.id)
            db.add(claim_source)

        db.commit()

        update_claim_status(claim_id, "completed", db)
    finally:
        if should_close:
            db.close()
