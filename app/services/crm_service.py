import httpx
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Claim, Score, Report

logger = logging.getLogger(__name__)

# ===== ID кастомных полей в amoCRM (портал ozipov26) =====
FIELD_CLAIM_ID = 274457
FIELD_CONTENT = 274459
FIELD_PLATFORM = 274461
FIELD_STATUS = 274463
FIELD_SCORE = 274465
FIELD_CONFIDENCE = 274467
FIELD_CONTRADICTIONS = 274469

# ===== ID значений для select-полей =====
PLATFORM_VALUES = {
    "Web": 152637,
    "Telegram": 152639,
    "Extension": 152641,
}
STATUS_VALUES = {
    "pending": 152643,
    "processing": 152645,
    "completed": 152647,
    "error": 152649,
}
CONFIDENCE_VALUES = {
    "low": 152651,
    "medium": 152653,
    "high": 152655,
}


class AmoCRMService:
    """Сервис интеграции VerifyAI с amoCRM через REST API v4."""

    def __init__(self):
        self.domain = settings.amo_domain
        self.base_url = f"https://{self.domain}"
        self.access_token = settings.amo_access_token
        self.timeout = 10.0

    def _is_configured(self) -> bool:
        if not self.domain or not self.access_token:
            logger.warning("amoCRM не настроена — пропускаю синхронизацию")
            return False
        return True

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _refresh_token(self) -> bool:
        """Обновляет access_token через refresh_token."""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/oauth2/access_token",
                    json={
                        "client_id": settings.amo_client_id,
                        "client_secret": settings.amo_client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": settings.amo_refresh_token,
                        "redirect_uri": settings.amo_redirect_uri,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data["access_token"]
                    logger.info("amoCRM токен успешно обновлён")
                    return True
        except Exception as e:
            logger.error(f"Ошибка обновления токена amoCRM: {e}")
        return False

    def _make_request(self, method: str, url: str, **kwargs):
        """Выполняет запрос, при 401 обновляет токен и повторяет."""
        with httpx.Client(timeout=self.timeout) as client:
            response = getattr(client, method)(
                url, headers=self._headers(), **kwargs
            )
            if response.status_code == 401:
                logger.info("Токен истёк, обновляю...")
                if self._refresh_token():
                    response = getattr(client, method)(
                        url, headers=self._headers(), **kwargs
                    )
            return response

    def create_deal(self, claim: Claim) -> Optional[str]:
        """
        Создаёт сделку в amoCRM при подаче нового запроса на проверку.
        Возвращает ID созданной сделки или None при ошибке.
        """
        if not self._is_configured():
            return None

        platform_enum_id = PLATFORM_VALUES.get(claim.source_platform, 152637)
        status_enum_id = STATUS_VALUES.get(claim.status, 152643)

        payload = [
            {
                "name": f"VerifyAI — {claim.content_body[:60]}",
                "custom_fields_values": [
                    {
                        "field_id": FIELD_CLAIM_ID,
                        "values": [{"value": str(claim.id)}],
                    },
                    {
                        "field_id": FIELD_CONTENT,
                        "values": [{"value": claim.content_body[:500]}],
                    },
                    {
                        "field_id": FIELD_PLATFORM,
                        "values": [{"enum_id": platform_enum_id}],
                    },
                    {
                        "field_id": FIELD_STATUS,
                        "values": [{"enum_id": status_enum_id}],
                    },
                ],
            }
        ]

        try:
            response = self._make_request(
                "post",
                f"{self.base_url}/api/v4/leads",
                json=payload,
            )

            if response.status_code in (200, 201):
                deal_id = str(
                    response.json()["_embedded"]["leads"][0]["id"]
                )
                logger.info(
                    f"Создана сделка amoCRM ID={deal_id} "
                    f"для claim {claim.id}"
                )
                return deal_id
            else:
                logger.error(
                    f"amoCRM вернула {response.status_code}: {response.text}"
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP-ошибка при создании сделки amoCRM: {e}")

        return None

    def update_deal(
        self,
        deal_id: str,
        score: Optional[Score] = None,
        report: Optional[Report] = None,
    ) -> bool:
        """
        Обновляет сделку в amoCRM после завершения анализа —
        записывает score, confidence, contradictions.
        """
        if not self._is_configured():
            return False

        custom_fields = [
            {
                "field_id": FIELD_STATUS,
                "values": [{"enum_id": STATUS_VALUES["completed"]}],
            }
        ]

        if score:
            custom_fields.append(
                {
                    "field_id": FIELD_SCORE,
                    "values": [{"value": score.score_value}],
                }
            )
            confidence_enum = CONFIDENCE_VALUES.get(
                score.confidence_level, 152651
            )
            custom_fields.append(
                {
                    "field_id": FIELD_CONFIDENCE,
                    "values": [{"enum_id": confidence_enum}],
                }
            )

        if report:
            custom_fields.append(
                {
                    "field_id": FIELD_CONTRADICTIONS,
                    "values": [{"value": report.contradictions_found}],
                }
            )

        payload = {"custom_fields_values": custom_fields}

        try:
            response = self._make_request(
                "patch",
                f"{self.base_url}/api/v4/leads/{deal_id}",
                json=payload,
            )

            if response.status_code in (200, 202):
                logger.info(f"Обновлена сделка amoCRM ID={deal_id}")
                return True
            else:
                logger.error(
                    f"amoCRM вернула {response.status_code}: {response.text}"
                )

        except httpx.HTTPError as e:
            logger.error(f"HTTP-ошибка при обновлении сделки {deal_id}: {e}")

        return False


# Синглтон — один экземпляр на всё приложение
crm_service = AmoCRMService()


def sync_claim_created(claim: Claim, db: Session) -> None:
    """Хук: вызывается сразу после создания нового Claim."""
    deal_id = crm_service.create_deal(claim)
    if deal_id:
        claim.crm_contact_id = deal_id
        claim.crm_synced_at = datetime.utcnow()
        db.commit()
        logger.info(f"Claim {claim.id} синхронизирован с amoCRM: deal {deal_id}")


def sync_claim_completed(
    claim: Claim,
    score: Score,
    report: Report,
    db: Session,
) -> None:
    """Хук: вызывается после завершения анализа mock_analyze."""
    if not claim.crm_contact_id:
        logger.warning(
            f"У claim {claim.id} нет crm_contact_id — обновление пропущено"
        )
        return

    success = crm_service.update_deal(
        deal_id=claim.crm_contact_id,
        score=score,
        report=report,
    )
    if success:
        claim.crm_synced_at = datetime.utcnow()
        db.commit()