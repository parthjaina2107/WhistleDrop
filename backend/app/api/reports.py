import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Report, StatusUpdate
from app.schemas import (
    ReportCreate, ReportSubmitResponse, ReportTrackResponse,
    StatusUpdateItem, AIAnalysisSummary,
    RedactionPreviewRequest, RedactionPreviewResponse
)
from app.services.case_code import generate_case_code, is_valid_case_code_format
from app.services.anonymity import redact_pii
from app.services.ml_classifier import classifier
from app.services.severity_engine import calculate_severity
from app.services.similarity_engine import similarity_engine
from app.services.tag_extractor import extract_tags

router = APIRouter(prefix="/reports", tags=["Reports (Anonymous Public)"])

@router.post("", response_model=ReportSubmitResponse, status_code=status.HTTP_201_CREATED)
def submit_report(payload: ReportCreate, db: Session = Depends(get_db)):
    """
    Submits an anonymous report.
    - Zero user identity or IP stored.
    - Automatic PII redaction (names, emails, IDs, phone numbers).
    - ML category classification with confidence score.
    - Automated severity triage score.
    - Generates high-entropy Case Code for tracking.
    """
    # 1. PII Redaction / Anonymization
    cleaned_desc, redactions_count, detected_types = redact_pii(payload.description)
    pii_redacted = redactions_count > 0

    # 2. ML Classification
    ai_result = classifier.predict(cleaned_desc)
    predicted_category = ai_result["predicted_category"]
    confidence = ai_result["confidence"]

    # 3. Severity Calculation
    severity = calculate_severity(cleaned_desc, category=payload.category)

    # 4. Extract Tags
    tags = extract_tags(cleaned_desc, top_n=6)

    # 5. Semantic Vector Embedding for Duplicate / Similarity Detection
    embedding_vec = similarity_engine.encode(cleaned_desc)

    # 6. Generate Unique Case Code (with collision check)
    max_attempts = 10
    case_code = None
    for _ in range(max_attempts):
        candidate_code = generate_case_code()
        exists = db.query(Report).filter(Report.case_code == candidate_code).first()
        if not exists:
            case_code = candidate_code
            break

    if not case_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate unique case tracking code. Please retry."
        )

    # 7. Create Report Record
    new_report = Report(
        case_code=case_code,
        category=payload.category,
        description=cleaned_desc,
        evidence_url=payload.evidence_url,
        ai_category=predicted_category,
        ai_confidence=confidence,
        severity=severity,
        status="SUBMITTED",
        pii_redacted=pii_redacted,
        redactions_count=redactions_count,
        ai_tags=json.dumps(tags),
        embedding=json.dumps(embedding_vec)
    )
    db.add(new_report)
    db.flush()  # obtain report.id

    # 8. Add Initial Status Update
    initial_update = StatusUpdate(
        report_id=new_report.id,
        previous_status=None,
        new_status="SUBMITTED",
        message="Report received and securely queued in the system."
    )
    db.add(initial_update)
    db.commit()
    db.refresh(new_report)

    return ReportSubmitResponse(
        case_code=case_code,
        message="Report submitted successfully. Save your case code to track resolution progress.",
        ai_analysis=AIAnalysisSummary(
            predicted_category=predicted_category,
            confidence=confidence,
            severity=severity,
            pii_redacted=pii_redacted,
            redactions_count=redactions_count
        )
    )

@router.get("/{case_code}", response_model=ReportTrackResponse)
def track_report(case_code: str, db: Session = Depends(get_db)):
    """
    Public tracking endpoint for anonymous reporters using only their Case Code.
    """
    code_normalized = case_code.strip().upper()
    
    if not is_valid_case_code_format(code_normalized):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid case code format. Format must be WD-XXXX-XXXX-XXXX."
        )

    report = db.query(Report).filter(Report.case_code == code_normalized).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case code not found. Please verify your code and retry."
        )

    updates_list = [
        StatusUpdateItem(
            status=u.new_status,
            message=u.message,
            timestamp=u.created_at
        )
        for u in report.updates
    ]

    return ReportTrackResponse(
        case_code=report.case_code,
        category=report.category,
        status=report.status,
        severity=report.severity,
        submitted_at=report.created_at,
        updates=updates_list
    )

@router.post("/preview-redaction", response_model=RedactionPreviewResponse)
def preview_redaction(payload: RedactionPreviewRequest):
    """
    Utility endpoint allowing reporters to preview how PII is stripped prior to final submission.
    """
    cleaned, count, types = redact_pii(payload.description)
    warning = (
        f"{count} potential identifying detail(s) ({', '.join(types)}) detected and will be redacted for your protection."
        if count > 0
        else "No identifying details detected. Your text is clean and ready."
    )
    return RedactionPreviewResponse(
        redacted_text=cleaned,
        redactions_count=count,
        detected_types=types,
        warning=warning
    )
