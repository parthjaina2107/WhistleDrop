import json
from app.database import SessionLocal, Base, engine
from app.models import Report, StatusUpdate, Moderator
from app.auth import get_password_hash, seed_default_moderator
from app.services.similarity_engine import similarity_engine
from app.services.ml_classifier import classifier
from app.services.severity_engine import calculate_severity
from app.services.anonymity import redact_pii
from app.services.tag_extractor import extract_tags

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_default_moderator(db)

        # Check if already seeded with reports
        existing_count = db.query(Report).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} reports. Skipping seed.")
            return

        print("Seeding realistic whistleblower demonstration cases...")

        sample_cases = [
            {
                "case_code": "WD-8F4K-92QP-X7LM",
                "category": "Security",
                "raw_text": "Someone gained unauthorized root access to our internal production database and downloaded confidential employee salary records. The incident was noticed by the infrastructure team on October 8th.",
                "status": "UNDER_REVIEW",
                "updates": [
                    ("SUBMITTED", "Report received and securely queued."),
                    ("UNDER_REVIEW", "Report escalated to the Cyber Incident Response Team.")
                ]
            },
            {
                "case_code": "WD-3A8Z-KF9V-2NHT",
                "category": "Security",
                "raw_text": "An unauthorized party bypassed the firewall and accessed our internal production database servers, exfiltrating staff salary records.",
                "status": "SUBMITTED",
                "updates": [
                    ("SUBMITTED", "Report received and queued for investigation.")
                ]
            },
            {
                "case_code": "WD-X9P7-LM4B-8CDE",
                "category": "Corruption",
                "raw_text": "The department head is demanding cash kickbacks of 50,000 rupees to approve hardware vendor contracts for the upcoming tech symposium.",
                "status": "UNDER_REVIEW",
                "updates": [
                    ("SUBMITTED", "Report registered anonymously."),
                    ("UNDER_REVIEW", "Assigned to the Institutional Ethics Oversight Committee.")
                ]
            },
            {
                "case_code": "WD-72LA-91PQ-4BVX",
                "category": "Harassment",
                "raw_text": "A senior research director is verbally abusing and threatening junior scholars with cancellation of their stipends if they do not complete personal chores.",
                "status": "SUBMITTED",
                "updates": [
                    ("SUBMITTED", "Report received and protected under whistleblower confidentiality.")
                ]
            },
            {
                "case_code": "WD-5B2M-67NX-3YTR",
                "category": "Technical",
                "raw_text": "The primary database automated backup pipeline has been failing silently for three weeks, leaving zero recoverable snapshots for disaster recovery.",
                "status": "RESOLVED",
                "updates": [
                    ("SUBMITTED", "Report queued."),
                    ("UNDER_REVIEW", "DevOps team notified of snapshot storage failure."),
                    ("RESOLVED", "S3 IAM permissions corrected. Backup schedule verified and restored.")
                ]
            },
            {
                "case_code": "WD-K4M9-12QW-8AZP",
                "category": "Other",
                "raw_text": "Hostel cafeteria in North Block consistently serving expired milk and contaminated drinking water from the dispenser.",
                "status": "UNDER_REVIEW",
                "updates": [
                    ("SUBMITTED", "Report submitted."),
                    ("UNDER_REVIEW", "Forwarded to Campus Health and Food Safety Inspection.")
                ]
            }
        ]

        for case in sample_cases:
            cleaned, red_cnt, _ = redact_pii(case["raw_text"])
            ai_res = classifier.predict(cleaned)
            sev = calculate_severity(cleaned, category=case["category"])
            tags = extract_tags(cleaned, top_n=5)
            vec = similarity_engine.encode(cleaned)

            report = Report(
                case_code=case["case_code"],
                category=case["category"],
                description=cleaned,
                ai_category=ai_res["predicted_category"],
                ai_confidence=ai_res["confidence"],
                severity=sev,
                status=case["status"],
                pii_redacted=red_cnt > 0,
                redactions_count=red_cnt,
                ai_tags=json.dumps(tags),
                embedding=json.dumps(vec)
            )
            db.add(report)
            db.flush()

            for st, msg in case["updates"]:
                upd = StatusUpdate(
                    report_id=report.id,
                    previous_status=None,
                    new_status=st,
                    message=msg
                )
                db.add(upd)

        db.commit()
        print("Database successfully seeded with 6 demonstration cases!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
