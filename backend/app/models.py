import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

def get_coarsened_time():
    """Round timestamp to the current hour to protect against timing correlation attacks."""
    now = datetime.now(timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0)

class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_code = Column(String(32), unique=True, index=True, nullable=False)
    
    # Core whistleblower submission fields
    category = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    evidence_url = Column(String(500), nullable=True)
    
    # AI / ML enhancement fields
    ai_category = Column(String(50), nullable=True)
    ai_confidence = Column(Float, nullable=True)
    severity = Column(String(20), default="MEDIUM", index=True)
    pii_redacted = Column(Boolean, default=False)
    redactions_count = Column(Integer, default=0)
    ai_tags = Column(Text, nullable=True, default="[]")  # JSON string list
    embedding = Column(Text, nullable=True)  # JSON string float array for similarity
    
    # Workflow status: SUBMITTED -> UNDER_REVIEW -> RESOLVED | DISMISSED
    status = Column(String(20), default="SUBMITTED", index=True)
    
    # Coarsened timestamp for privacy
    created_at = Column(DateTime(timezone=True), default=get_coarsened_time, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    updates = relationship("StatusUpdate", back_populates="report", cascade="all, delete-orphan", order_by="StatusUpdate.created_at.asc()")

class StatusUpdate(Base):
    __tablename__ = "status_updates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    
    previous_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("Report", back_populates="updates")

class Moderator(Base):
    __tablename__ = "moderators"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(20), default="MODERATOR")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
