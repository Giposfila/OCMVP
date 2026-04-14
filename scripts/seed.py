import uuid
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.models import UserProfile, Claim, Report, Score, Source, Rebuttal, ClaimSources

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, echo=False)
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(bind=engine)


def create_seed_data():
    db = SessionLocal()
    try:
        password = "test123"[:72]

        elena = UserProfile(
            id=uuid.uuid4(),
            email="elena@test.ru",
            password_hash=bcrypt.hash(password),
            role="StandardUser",
        )
        artem = UserProfile(
            id=uuid.uuid4(),
            email="artem@test.ru",
            password_hash=bcrypt.hash(password),
            role="ProfessionalAnalyst",
        )
        admin = UserProfile(
            id=uuid.uuid4(),
            email="admin@test.ru",
            password_hash=bcrypt.hash(password),
            role="Admin",
        )

        db.add_all([elena, artem, admin])
        db.commit()

        sample_claims = [
            "Курс доллара упадет до 50 рублей к концу года",
            "В России отменят пенсионную реформу",
            "Новый закон разрешает конфискацию имущества",
            "Биткоин достигнет 100000$ в 2024 году",
            "Apple выпустит новый iPhone без зарядки",
        ]

        for content in sample_claims:
            claim = Claim(
                id=uuid.uuid4(),
                content_body=content,
                source_platform="Web",
                status="completed",
                user_id=elena.id,
            )
            db.add(claim)
            db.flush()

            idx = sample_claims.index(content)
            score_value = 30 + idx * 12
            contradictions = 5 - idx

            source1 = Source(
                id=uuid.uuid4(),
                url="https://cbr.ru/press/pr/",
                source_type="official_registry",
                trust_level=95,
                retrieved_at=datetime.utcnow(),
            )
            source2 = Source(
                id=uuid.uuid4(),
                url="https://ria.ru/economy/",
                source_type="media",
                trust_level=72,
                retrieved_at=datetime.utcnow(),
            )
            db.add_all([source1, source2])
            db.flush()

            report = Report(
                id=uuid.uuid4(),
                claim_id=claim.id,
                summary_text=f"Анализ выявил {contradictions} противоречия. Индекс {score_value}/100.",
                contradictions_found=contradictions,
                generated_at=datetime.utcnow(),
            )

            score = Score(
                id=uuid.uuid4(),
                claim_id=claim.id,
                score_value=score_value,
                confidence_level="high"
                if score_value > 65
                else "medium"
                if score_value > 35
                else "low",
                calculated_at=datetime.utcnow(),
            )

            rebuttal = Rebuttal(
                id=uuid.uuid4(),
                report_id=report.id,
                text_content=f"✅ Проверено VerifyAI | Индекс: {score_value}/100",
                created_at=datetime.utcnow(),
            )

            db.add_all([report, score, rebuttal])

            cs1 = ClaimSources(claim_id=claim.id, source_id=source1.id)
            cs2 = ClaimSources(claim_id=claim.id, source_id=source2.id)
            db.add_all([cs1, cs2])

        db.commit()
        print("Seed data created successfully!")
        print(
            "Users: elena@test.ru / test123, artem@test.ru / test123, admin@test.ru / admin123"
        )
    finally:
        db.close()


if __name__ == "__main__":
    create_seed_data()
