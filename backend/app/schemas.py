from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

CategoryType = Literal["Security", "Harassment", "Corruption", "Technical", "Other"]
StatusType = Literal["SUBMITTED", "UNDER_REVIEW", "RESOLVED", "DISMISSED", "CLOSED"]
SeverityType = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# --- Public Reporter Schemas ---

class ReportCreate(BaseModel):
    category: CategoryType = Field(..., description="Category of the incident")
    description: str = Field(..., min_length=10, max_length=15000, description="Detailed narrative of what occurred")
    evidence_url: Optional[str] = Field(None, max_length=500, description="Optional link to evidence")

    @field_validator("evidence_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not (v.startswith("http://") or v.startswith("https://") or v.startswith("/static/uploads/")):
            raise ValueError("Evidence URL must start with http://, https://, or /static/uploads/")
        return v

class AIAnalysisSummary(BaseModel):
    predicted_category: Optional[str] = None
    confidence: Optional[float] = None
    severity: str
    pii_redacted: bool
    redactions_count: int

class ReportSubmitResponse(BaseModel):
    case_code: str
    message: str
    ai_analysis: AIAnalysisSummary

class StatusUpdateItem(BaseModel):
    status: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class ReportTrackResponse(BaseModel):
    case_code: str
    category: str
    status: str
    severity: str
    submitted_at: datetime
    updates: List[StatusUpdateItem]

class RedactionPreviewRequest(BaseModel):
    description: str = Field(..., min_length=5, max_length=15000)

class RedactionPreviewResponse(BaseModel):
    redacted_text: str
    redactions_count: int
    detected_types: List[str]
    warning: str

# --- Moderator Schemas ---

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class StatusChangeRequest(BaseModel):
    status: StatusType
    message: str = Field(..., min_length=3, max_length=2000, description="Audit note explaining the transition")

class SimilarReportItem(BaseModel):
    id: str
    case_code: str
    category: str
    status: str
    severity: str
    similarity: float

class ReportAdminSummary(BaseModel):
    id: str
    case_code: str
    category: str
    ai_category: Optional[str]
    ai_confidence: Optional[float]
    severity: str
    status: str
    description_preview: str
    pii_redacted: bool
    redactions_count: int
    similar_reports_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ReportAdminDetail(BaseModel):
    id: str
    case_code: str
    category: str
    description: str
    evidence_url: Optional[str]
    ai_category: Optional[str]
    ai_confidence: Optional[float]
    severity: str
    status: str
    pii_redacted: bool
    redactions_count: int
    ai_tags: List[str]
    created_at: datetime
    updated_at: datetime
    updates: List[StatusUpdateItem]
    similar_reports: List[SimilarReportItem] = []

    model_config = ConfigDict(from_attributes=True)

class PaginatedReportsResponse(BaseModel):
    reports: List[ReportAdminSummary]
    total: int
    page: int
    limit: int
    total_pages: int

class DashboardStatsResponse(BaseModel):
    total_reports: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    ai_metrics: Dict[str, Any]
