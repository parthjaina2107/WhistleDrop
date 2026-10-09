import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

# --- 1. Anonymous Report Submission Tests ---

def test_submit_valid_report():
    response = client.post(
        "/api/reports",
        json={
            "category": "Security",
            "description": "Unauthorized access detected in the production database with stolen credentials.",
            "evidence_url": "https://example.com/log.png"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "case_code" in data
    assert data["case_code"].startswith("WD-")
    assert len(data["case_code"].split("-")) == 4  # WD-XXXX-XXXX-XXXX
    assert "ai_analysis" in data
    assert data["ai_analysis"]["predicted_category"] == "Security"
    assert data["ai_analysis"]["severity"] in ["HIGH", "CRITICAL"]

def test_submit_report_validation_errors():
    # Missing description
    res1 = client.post("/api/reports", json={"category": "Security"})
    assert res1.status_code == 422

    # Description too short
    res2 = client.post("/api/reports", json={"category": "Security", "description": "Too short"})
    assert res2.status_code == 422

    # Invalid category
    res3 = client.post(
        "/api/reports",
        json={"category": "InvalidCategory", "description": "Valid length description for testing."}
    )
    assert res3.status_code == 422

    # Invalid evidence URL
    res4 = client.post(
        "/api/reports",
        json={
            "category": "Security",
            "description": "Valid length description for testing.",
            "evidence_url": "not-a-valid-url"
        }
    )
    assert res4.status_code == 422

# --- 2. Anonymity & PII Redaction Tests ---

def test_pii_redaction_engine():
    response = client.post(
        "/api/reports",
        json={
            "category": "Harassment",
            "description": "My manager Mr. Rajesh Sharma emailed me from rajesh.sharma@corp.com and called me at +91-9876543210 regarding my employee ID EMP-4921.",
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["ai_analysis"]["pii_redacted"] is True
    assert data["ai_analysis"]["redactions_count"] >= 3

def test_redaction_preview():
    response = client.post(
        "/api/reports/preview-redaction",
        json={"description": "Please contact test.user@example.com at Desk 4B on October 15th."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "[REDACTED_EMAIL]" in data["redacted_text"]
    assert "[REDACTED_LOCATION]" in data["redacted_text"]
    assert data["redactions_count"] >= 2

# --- 3. Public Case Tracking Tests ---

def test_track_report_workflow():
    # 1. Submit
    submit_res = client.post(
        "/api/reports",
        json={
            "category": "Technical",
            "description": "The campus server cluster suffered a critical power outage during evening backups.",
        }
    )
    case_code = submit_res.json()["case_code"]

    # 2. Track
    track_res = client.get(f"/api/reports/{case_code}")
    assert track_res.status_code == 200
    track_data = track_res.json()
    assert track_data["case_code"] == case_code
    assert track_data["status"] == "SUBMITTED"
    assert len(track_data["updates"]) >= 1

def test_track_report_not_found():
    response = client.get("/api/reports/WD-9999-8888-7777")
    assert response.status_code == 404

def test_track_report_invalid_case_code():
    response = client.get("/api/reports/12345-invalid")
    assert response.status_code == 400

# --- 4. Moderator Auth & Permissions Tests ---

def test_moderator_auth():
    # Valid login
    login_res = client.post(
        "/api/auth/login",
        json={"username": settings.DEFAULT_ADMIN_USERNAME, "password": settings.DEFAULT_ADMIN_PASSWORD}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    # Invalid password
    bad_res = client.post(
        "/api/auth/login",
        json={"username": settings.DEFAULT_ADMIN_USERNAME, "password": "WrongPassword!"}
    )
    assert bad_res.status_code == 401

    # Unauthorized access to admin route
    unauth_res = client.get("/api/admin/reports")
    assert unauth_res.status_code == 401

    # Authorized access
    auth_res = client.get("/api/admin/reports", headers={"Authorization": f"Bearer {token}"})
    assert auth_res.status_code == 200
    assert "reports" in auth_res.json()

# --- 5. State Machine Workflow Tests ---

def test_status_transition_state_machine():
    # Login
    login_res = client.post(
        "/api/auth/login",
        json={"username": settings.DEFAULT_ADMIN_USERNAME, "password": settings.DEFAULT_ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a fresh report
    sub_res = client.post(
        "/api/reports",
        json={
            "category": "Corruption",
            "description": "A contractor was observed bribing procurement officials with cash envelopes.",
        }
    )
    case_code = sub_res.json()["case_code"]

    # Fetch report ID from admin list
    admin_list = client.get(f"/api/admin/reports?search={case_code}", headers=headers).json()
    report_id = admin_list["reports"][0]["id"]

    # 1. Illegal transition: SUBMITTED -> RESOLVED (must be UNDER_REVIEW first!)
    illegal_res = client.patch(
        f"/api/admin/reports/{report_id}/status",
        headers=headers,
        json={"status": "RESOLVED", "message": "Trying to skip review"}
    )
    assert illegal_res.status_code == 422

    # 2. Valid transition: SUBMITTED -> UNDER_REVIEW
    valid_review = client.patch(
        f"/api/admin/reports/{report_id}/status",
        headers=headers,
        json={"status": "UNDER_REVIEW", "message": "Assigning to forensic team"}
    )
    assert valid_review.status_code == 200
    assert valid_review.json()["new_status"] == "UNDER_REVIEW"

    # 3. Add interim status note
    note_res = client.post(
        f"/api/admin/reports/{report_id}/updates?message=Forensic+analysis+in+progress",
        headers=headers
    )
    assert note_res.status_code == 200

    # 4. Valid transition: UNDER_REVIEW -> RESOLVED
    valid_resolve = client.patch(
        f"/api/admin/reports/{report_id}/status",
        headers=headers,
        json={"status": "RESOLVED", "message": "Contractor barred and referred to police"}
    )
    assert valid_resolve.status_code == 200
    assert valid_resolve.json()["new_status"] == "RESOLVED"

    # 5. Terminal state check: RESOLVED cannot be changed
    terminal_res = client.patch(
        f"/api/admin/reports/{report_id}/status",
        headers=headers,
        json={"status": "UNDER_REVIEW", "message": "Attempting reopen"}
    )
    assert terminal_res.status_code == 422

# --- 6. Dashboard Stats Test ---

def test_dashboard_stats():
    login_res = client.post(
        "/api/auth/login",
        json={"username": settings.DEFAULT_ADMIN_USERNAME, "password": settings.DEFAULT_ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/admin/dashboard/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()
    assert "total_reports" in stats
    assert "by_status" in stats
    assert "by_severity" in stats
    assert "by_category" in stats
    assert "ai_metrics" in stats

# --- 7. Evidence File Upload Tests (GDG Brownie Point) ---

def test_evidence_file_upload():
    file_content = b"Incident evidence screenshot data dummy buffer"
    res = client.post(
        "/api/reports/upload-evidence",
        files={"file": ("incident_leak.png", file_content, "image/png")}
    )
    assert res.status_code == 201
    data = res.json()
    assert "evidence_url" in data
    assert data["evidence_url"].startswith("/static/uploads/evidence_")
    assert data["filename"].endswith(".png")

def test_evidence_file_upload_invalid_type():
    file_content = b"malicious binary or executable script"
    res = client.post(
        "/api/reports/upload-evidence",
        files={"file": ("exploit.exe", file_content, "application/x-msdownload")}
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]

# --- 8. Permanent Case Closure & Purge Tests (GDG Brownie Point) ---

def test_permanently_close_case():
    login_res = client.post(
        "/api/auth/login",
        json={"username": settings.DEFAULT_ADMIN_USERNAME, "password": settings.DEFAULT_ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit a report
    sub_res = client.post(
        "/api/reports",
        json={
            "category": "Security",
            "description": "Critical security breach on bastion server needing permanent closure test.",
        }
    )
    case_code = sub_res.json()["case_code"]

    # Locate report ID
    admin_list = client.get(f"/api/admin/reports?search={case_code}", headers=headers).json()
    report_id = admin_list["reports"][0]["id"]

    # Advance to UNDER_REVIEW
    client.patch(
        f"/api/admin/reports/{report_id}/status",
        headers=headers,
        json={"status": "UNDER_REVIEW", "message": "Investigating"}
    )

    # Permanently close case
    close_res = client.post(
        f"/api/admin/reports/{report_id}/close?reason=Investigation+completed+and+sealed",
        headers=headers
    )
    assert close_res.status_code == 200
    assert close_res.json()["new_status"] == "CLOSED"

    # Attempting to change status of CLOSED case must return 422
    attempt_res = client.patch(
        f"/api/admin/reports/{report_id}/status",
        headers=headers,
        json={"status": "UNDER_REVIEW", "message": "Attempting reopen"}
    )
    assert attempt_res.status_code == 422

def test_purge_case():
    login_res = client.post(
        "/api/auth/login",
        json={"username": settings.DEFAULT_ADMIN_USERNAME, "password": settings.DEFAULT_ADMIN_PASSWORD}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit a report
    sub_res = client.post(
        "/api/reports",
        json={
            "category": "Other",
            "description": "Ephemeral test report destined for legal purge deletion test.",
        }
    )
    case_code = sub_res.json()["case_code"]

    admin_list = client.get(f"/api/admin/reports?search={case_code}", headers=headers).json()
    report_id = admin_list["reports"][0]["id"]

    # Purge the report
    del_res = client.delete(f"/api/admin/reports/{report_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["purged"] is True

    # Confirm it cannot be tracked
    track_res = client.get(f"/api/reports/{case_code}")
    assert track_res.status_code == 404

