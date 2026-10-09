import json
from typing import Optional, List
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_
from app.database import get_db
from app.models import Report, StatusUpdate, Moderator
from app.schemas import (
    ReportAdminSummary, ReportAdminDetail, PaginatedReportsResponse,
    StatusChangeRequest, StatusUpdateItem, SimilarReportItem, DashboardStatsResponse
)
from app.auth import get_current_moderator
from app.services.similarity_engine import similarity_engine

router = APIRouter(prefix="/admin", tags=["Moderator Administration"])

# Valid state transitions lookup table
VALID_STATUS_TRANSITIONS = {
    "SUBMITTED": ["UNDER_REVIEW"],
    "UNDER_REVIEW": ["RESOLVED", "DISMISSED"],
    "RESOLVED": [],   # Terminal state
    "DISMISSED": [],  # Terminal state
}

@router.get("/reports", response_model=PaginatedReportsResponse)
def list_reports(
    status: Optional[str] = Query(None, description="Filter by status (SUBMITTED, UNDER_REVIEW, RESOLVED, DISMISSED)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MEDIUM, HIGH, CRITICAL)"),
    search: Optional[str] = Query(None, description="Search term matching description or case code"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, severity, status)"),
    order: str = Query("desc", description="Sort order (asc, desc)"),
    current_mod: Moderator = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    """
    Moderator endpoint to list and filter reports with pagination.
    Guarantees zero reporter identity is exposed.
    """
    query = db.query(Report)

    if status:
        query = query.filter(Report.status == status.strip().upper())
    if category:
        query = query.filter(Report.category == category.strip())
    if severity:
        query = query.filter(Report.severity == severity.strip().upper())
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Report.case_code.ilike(search_term),
                Report.description.ilike(search_term)
            )
        )

    # Sorting
    sort_col = getattr(Report, sort_by, Report.created_at)
    if order.lower() == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    total = query.count()
    offset = (page - 1) * limit
    reports_page = query.offset(offset).limit(limit).all()

    # Build summaries
    all_reports_for_sim_count = db.query(Report).all()
    summaries = []
    for r in reports_page:
        # Calculate how many similar reports exist
        sim_count = 0
        if r.embedding:
            try:
                target_vec = json.loads(r.embedding)
                sims = similarity_engine.find_similar(
                    target_vec=target_vec,
                    target_id=r.id,
                    candidates=all_reports_for_sim_count,
                    threshold=0.70,
                    top_k=10
                )
                sim_count = len(sims)
            except Exception:
                sim_count = 0

        desc_snippet = (r.description[:120] + "...") if len(r.description) > 120 else r.description
        summaries.append(ReportAdminSummary(
            id=r.id,
            case_code=r.case_code,
            category=r.category,
            ai_category=r.ai_category,
            ai_confidence=r.ai_confidence,
            severity=r.severity,
            status=r.status,
            description_preview=desc_snippet,
            pii_redacted=r.pii_redacted,
            redactions_count=r.redactions_count,
            similar_reports_count=sim_count,
            created_at=r.created_at
        ))

    total_pages = ceil(total / limit) if total > 0 else 1
    return PaginatedReportsResponse(
        reports=summaries,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages
    )

@router.get("/reports/{report_id}", response_model=ReportAdminDetail)
def get_report_detail(
    report_id: str,
    current_mod: Moderator = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    """
    Moderator endpoint to fetch full report details, status updates, and semantic duplicates.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Parse AI tags
    try:
        tags = json.loads(report.ai_tags) if report.ai_tags else []
    except Exception:
        tags = []

    # Calculate similar / co-related reports
    similar_reports = []
    if report.embedding:
        try:
            target_vec = json.loads(report.embedding)
            all_reports = db.query(Report).all()
            raw_sims = similarity_engine.find_similar(
                target_vec=target_vec,
                target_id=report.id,
                candidates=all_reports,
                threshold=0.65,
                top_k=5
            )
            similar_reports = [SimilarReportItem(**s) for s in raw_sims]
        except Exception:
            similar_reports = []

    updates_list = [
        StatusUpdateItem(
            status=u.new_status,
            message=u.message,
            timestamp=u.created_at
        )
        for u in report.updates
    ]

    return ReportAdminDetail(
        id=report.id,
        case_code=report.case_code,
        category=report.category,
        description=report.description,
        evidence_url=report.evidence_url,
        ai_category=report.ai_category,
        ai_confidence=report.ai_confidence,
        severity=report.severity,
        status=report.status,
        pii_redacted=report.pii_redacted,
        redactions_count=report.redactions_count,
        ai_tags=tags,
        created_at=report.created_at,
        updated_at=report.updated_at,
        updates=updates_list,
        similar_reports=similar_reports
    )

@router.patch("/reports/{report_id}/status")
def update_report_status(
    report_id: str,
    payload: StatusChangeRequest,
    current_mod: Moderator = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    """
    Updates report status according to the strict state machine workflow:
    SUBMITTED -> UNDER_REVIEW -> RESOLVED | DISMISSED
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    current_status = report.status
    target_status = payload.status

    if current_status == target_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is already in status '{current_status}'."
        )

    allowed_next_states = VALID_STATUS_TRANSITIONS.get(current_status, [])
    if target_status not in allowed_next_states:
        if current_status in ["RESOLVED", "DISMISSED"]:
            detail_msg = f"Report is in terminal status '{current_status}' and cannot be altered."
        else:
            detail_msg = (
                f"Invalid status transition from '{current_status}' to '{target_status}'. "
                f"Allowed transitions: {allowed_next_states}"
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail_msg
        )

    # Update status
    report.status = target_status
    
    # Record timeline entry
    audit_entry = StatusUpdate(
        report_id=report.id,
        previous_status=current_status,
        new_status=target_status,
        message=payload.message
    )
    db.add(audit_entry)
    db.commit()

    return {
        "message": "Report status successfully updated.",
        "case_code": report.case_code,
        "previous_status": current_status,
        "new_status": target_status
    }

@router.post("/reports/{report_id}/updates")
def add_status_update(
    report_id: str,
    message: str = Query(..., min_length=3, max_length=2000, description="Investigation note visible to reporter"),
    current_mod: Moderator = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    """
    Adds an ongoing investigation update note to the case without altering the status.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    update_entry = StatusUpdate(
        report_id=report.id,
        previous_status=report.status,
        new_status=report.status,
        message=message
    )
    db.add(update_entry)
    db.commit()

    return {
        "message": "Status note added successfully.",
        "case_code": report.case_code,
        "status": report.status,
        "note": message
    }

@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    current_mod: Moderator = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    """
    Returns aggregated metrics for the moderator dashboard.
    """
    all_reports = db.query(Report).all()
    total = len(all_reports)

    by_status = {"SUBMITTED": 0, "UNDER_REVIEW": 0, "RESOLVED": 0, "DISMISSED": 0}
    by_severity = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    by_category = {"Security": 0, "Harassment": 0, "Corruption": 0, "Technical": 0, "Other": 0}

    auto_classified = 0
    flagged_review = 0
    redacted_cases = 0

    for r in all_reports:
        if r.status in by_status:
            by_status[r.status] += 1
        if r.severity in by_severity:
            by_severity[r.severity] += 1
        if r.category in by_category:
            by_category[r.category] += 1
        
        if r.ai_confidence and r.ai_confidence >= 0.80:
            auto_classified += 1
        elif r.ai_confidence and r.ai_confidence >= 0.50:
            flagged_review += 1
        
        if r.pii_redacted:
            redacted_cases += 1

    return DashboardStatsResponse(
        total_reports=total,
        by_status=by_status,
        by_severity=by_severity,
        by_category=by_category,
        ai_metrics={
            "auto_classified": auto_classified,
            "flagged_for_review": flagged_review,
            "privacy_redacted_cases": redacted_cases,
            "high_confidence_ratio": round(auto_classified / total, 2) if total > 0 else 1.0
        }
    )
