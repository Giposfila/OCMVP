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

PLATFORM_VALUES = {"Web": 152637, "Telegram": 152639, "Extension": 152641}
STATUS_VALUES = {"pending": 152643, "processing": 152645, "completed": 152647, "error": 152649}
CONFIDENCE_VALUES = {"low": 152651, "medium": 152653, "high": 152655}

class AmoCRMService:
    def __init__(self):
        self.domain = settings.amo_domain
        self.base_url = f"https://{self.domain}"
        self.access_token = settings.amo_access_token
        self.timeout = 10.0

    def _is_configured(self) -> bool:
        return bool(self.domain and self.access_token)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    def _refresh_token(self) -> bool:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/oauth2/access_token",
                    json={
                        "client_id": settings.amo_client_id,
                        "client_secret": settings.amo_client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": settings.amo_refresh_token,
                        "redirect_uri": settings.amo_redirect_uri,
                    },
                )
                if resp.status_code == 200:
                    self.access_token = resp.json()["access_token"]
                    logger.info("amoCRM токен обновлён")
                    return True
        except Exception as e:
            logger.error(f"Ошибка обновления токена amoCRM: {e}")
        return False

    def _request(self, method: str, url: str, **kwargs):
        with httpx.Client(timeout=self.timeout) as client:
            resp = getattr(client, method)(url, headers=self._headers(), **kwargs)
            if resp.status_code == 401 and self._refresh_token():
                resp = getattr(client, method)(url, headers=self._headers(), **kwargs)
            return resp

    def create_deal(self, claim: Claim) -> Optional[str]:
        if not self._is_configured():
            return None
        payload = [{
            "name": f"VerifyAI — {claim.content_body[:60]}",
            "custom_fields_values": [
                {"field_id": FIELD_CLAIM_ID, "values": [{"value": str(claim.id)}]},
                {"field_id": FIELD_CONTENT, "values": [{"value": claim.content_body[:500]}]},
                {"field_id": FIELD_PLATFORM, "values": [{"enum_id": PLATFORM_VALUES.get(claim.source_platform, 152637)}]},
                {"field_id": FIELD_STATUS, "values": [{"enum_id": STATUS_VALUES.get(claim.status, 152643)}]},
            ]
        }]
        try:
            resp = self._request("post", f"{self.base_url}/api/v4/leads", json=payload)
            if resp.status_code in (200, 201):
                deal_id = str(resp.json()["_embedded"]["leads"][0]["id"])
                logger.info(f"Создана сделка amoCRM ID={deal_id} для claim {claim.id}")
                return deal_id
            logger.error(f"amoCRM create error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"HTTP error create_deal: {e}")
        return None

    def update_deal(self, deal_id: str, score: Optional[Score] = None, report: Optional[Report] = None) -> bool:
        if not self._is_configured():
            return False
        fields = [{"field_id": FIELD_STATUS, "values": [{"enum_id": STATUS_VALUES["completed"]}]}]
        if score:
            fields.append({"field_id": FIELD_SCORE, "values": [{"value": score.score_value}]})
            fields.append({"field_id": FIELD_CONFIDENCE, "values": [{"enum_id": CONFIDENCE_VALUES.get(score.confidence_level, 152651)}]})
        if report:
            fields.append({"field_id": FIELD_CONTRADICTIONS, "values": [{"value": report.contradictions_found}]})
        try:
            resp = self._request("patch", f"{self.base_url}/api/v4/leads/{deal_id}", json={"custom_fields_values": fields})
            if resp.status_code in (200, 202):
                logger.info(f"Обновлена сделка amoCRM ID={deal_id}")
                return True
            logger.error(f"amoCRM update error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"HTTP error update_deal: {e}")
        return False

crm_service = AmoCRMService()

def sync_claim_created(claim: Claim, db: Session) -> None:
    deal_id = crm_service.create_deal(claim)
    if deal_id:
        claim.crm_contact_id = deal_id
        claim.crm_synced_at = datetime.utcnow()
        db.commit()

def sync_claim_completed(claim: Claim, score: Score, report: Report, db: Session) -> None:
    if not claim.crm_contact_id:
        return
    if crm_service.update_deal(claim.crm_contact_id, score, report):
        claim.crm_synced_at = datetime.utcnow()
        db.commit()