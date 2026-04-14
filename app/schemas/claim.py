from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "StandardUser"


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimCreate(BaseModel):
    content_body: str
    source_platform: str = "Web"
    user_id: Optional[UUID] = None
    crm_contact_id: Optional[str] = None


class ClaimResponse(BaseModel):
    id: UUID
    content_body: str
    source_platform: str
    status: str
    user_id: UUID
    created_at: datetime
    crm_contact_id: Optional[str] = None

    model_config = {"from_attributes": True}


class SourceResponse(BaseModel):
    id: UUID
    url: str
    source_type: str
    trust_level: int
    retrieved_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: UUID
    claim_id: UUID
    summary_text: str
    contradictions_found: int
    generated_at: datetime

    model_config = {"from_attributes": True}


class ScoreResponse(BaseModel):
    id: UUID
    claim_id: UUID
    score_value: int
    confidence_level: str
    calculated_at: datetime

    model_config = {"from_attributes": True}


class RebuttalResponse(BaseModel):
    id: UUID
    report_id: UUID
    text_content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimWithReport(BaseModel):
    claim: ClaimResponse
    report: Optional[ReportResponse] = None
    score: Optional[ScoreResponse] = None
    sources: list[SourceResponse] = []


class ClaimStatusResponse(BaseModel):
    status: str
    score_value: Optional[int] = None
    confidence_level: Optional[str] = None
