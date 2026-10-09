import pytest
from app.services.similarity_engine import similarity_engine
from app.services.ml_classifier import classifier
from app.services.severity_engine import calculate_severity
from app.services.anonymity import redact_pii

def test_semantic_similarity_matching():
    text1 = "Someone accessed our internal production database without authorization and stole user tables."
    text2 = "Unauthorized intruder compromised the production database server and exfiltrated user data."
    unrelated = "The cafeteria in Block 2 is serving cold lunch and stale sandwiches."

    vec1 = similarity_engine.encode(text1)
    vec2 = similarity_engine.encode(text2)
    vec_unrelated = similarity_engine.encode(unrelated)

    sim_related = similarity_engine.compute_similarity(vec1, vec2)
    sim_unrelated = similarity_engine.compute_similarity(vec1, vec_unrelated)

    # Similar reports should have significantly higher similarity than unrelated ones
    assert sim_related > 0.60
    assert sim_unrelated < 0.30

def test_severity_levels():
    assert calculate_severity("Ransomware payload detected with root access and leaked passwords", "Security") == "CRITICAL"
    assert calculate_severity("Vendor demanding kickback bribes to award tender contract", "Corruption") == "HIGH"
    assert calculate_severity("Database connection pool memory leak causing microservice latency", "Technical") == "MEDIUM"
    assert calculate_severity("Office water dispenser is broken and making noise", "Other") == "LOW"

def test_pii_comprehensive_scrubbing():
    dirty_text = (
        "I am Dr. Ramesh Gupta from SRM University (Reg No: RA2111003010999). "
        "Email me at ramesh.gupta@srmist.edu.in or call 9876543210. "
        "The incident happened in Cabin 402 on October 14th from IP 192.168.1.50."
    )
    cleaned, count, types = redact_pii(dirty_text)
    
    assert "ramesh.gupta@srmist.edu.in" not in cleaned
    assert "9876543210" not in cleaned
    assert "RA2111003010999" not in cleaned
    assert "192.168.1.50" not in cleaned
    assert "[REDACTED_EMAIL]" in cleaned
    assert "[REDACTED_PHONE]" in cleaned
    assert "[REDACTED_ID]" in cleaned
    assert "[REDACTED_IP]" in cleaned
    assert count >= 5
