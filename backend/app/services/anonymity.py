import re
from typing import Tuple, List, Set

# Regex patterns for high-risk Personally Identifiable Information (PII)
PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "PHONE": re.compile(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{4,5}\b"),
    "STUDENT_EMP_ID": re.compile(
        r"\b(?:RA\d{13}|EMP[-_]?\d+|SRM[-_]?\d+|ID[:\s#]*\d{4,8}|Roll\s*(?:No|Number)?[:\s#]*[A-Z0-9]+|Reg\s*(?:No|Number)?[:\s#]*[A-Z0-9]+)\b",
        re.IGNORECASE
    ),
    "IP_ADDRESS": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "NATIONAL_ID": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),  # Aadhaar / 12-digit ID
    "SPECIFIC_LOCATION": re.compile(
        r"\b(?:Desk|Cubicle|Room|Cabin|Floor|Block|Building|Lab)\s+[A-Za-z0-9\-]+\b",
        re.IGNORECASE
    ),
    "SPECIFIC_DATE": re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?)\b",
        re.IGNORECASE
    ),
    "TITLED_NAME": re.compile(
        r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Dean|Director|Manager|HOD)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
    ),
    "EXPLICIT_NAME_INTRO": re.compile(
        r"\b(?:my name is|i am|this is|contact)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        re.IGNORECASE
    ),
}

def redact_pii(text: str) -> Tuple[str, int, List[str]]:
    """
    Scans text for Personally Identifiable Information and redacts it.
    Returns:
        (cleaned_text, total_redactions_count, list_of_detected_pii_types)
    """
    if not text:
        return text, 0, []

    cleaned = text
    total_count = 0
    detected_types: Set[str] = set()

    # Redact Emails
    matches = list(PATTERNS["EMAIL"].finditer(cleaned))
    if matches:
        total_count += len(matches)
        detected_types.add("EMAIL")
        cleaned = PATTERNS["EMAIL"].sub("[REDACTED_EMAIL]", cleaned)

    # Redact National IDs (Aadhaar / SSN)
    matches = list(PATTERNS["NATIONAL_ID"].finditer(cleaned))
    if matches:
        total_count += len(matches)
        detected_types.add("NATIONAL_ID")
        cleaned = PATTERNS["NATIONAL_ID"].sub("[REDACTED_ID]", cleaned)

    # Redact Student / Employee IDs
    matches = list(PATTERNS["STUDENT_EMP_ID"].finditer(cleaned))
    if matches:
        total_count += len(matches)
        detected_types.add("STUDENT_EMP_ID")
        cleaned = PATTERNS["STUDENT_EMP_ID"].sub("[REDACTED_ID]", cleaned)

    # Redact IP addresses
    matches = list(PATTERNS["IP_ADDRESS"].finditer(cleaned))
    if matches:
        total_count += len(matches)
        detected_types.add("IP_ADDRESS")
        cleaned = PATTERNS["IP_ADDRESS"].sub("[REDACTED_IP]", cleaned)

    # Redact Phone numbers (after checking IDs/IPs so numbers aren't double-consumed)
    matches = list(PATTERNS["PHONE"].finditer(cleaned))
    # Filter matches to only real phone lengths (at least 7 digits)
    phone_matches = [m for m in matches if sum(c.isdigit() for c in m.group(0)) >= 7]
    if phone_matches:
        total_count += len(phone_matches)
        detected_types.add("PHONE")
        for m in phone_matches:
            cleaned = cleaned.replace(m.group(0), "[REDACTED_PHONE]")

    # Redact Titled Names (e.g. "Dr. Ramesh Sharma" -> "Dr. [REDACTED_PERSON]")
    titled_matches = list(PATTERNS["TITLED_NAME"].finditer(cleaned))
    if titled_matches:
        total_count += len(titled_matches)
        detected_types.add("PERSON")
        cleaned = PATTERNS["TITLED_NAME"].sub(r"\g<0>", cleaned)
        # Replace the captured name with redaction
        for m in titled_matches:
            name_part = m.group(1)
            cleaned = cleaned.replace(name_part, "[REDACTED_PERSON]")

    # Redact explicit introductions
    intro_matches = list(PATTERNS["EXPLICIT_NAME_INTRO"].finditer(cleaned))
    if intro_matches:
        total_count += len(intro_matches)
        detected_types.add("PERSON")
        for m in intro_matches:
            name_part = m.group(1)
            cleaned = cleaned.replace(name_part, "[REDACTED_PERSON]")

    # Redact Specific Locations (Desk 4B, Room 302, Building A)
    loc_matches = list(PATTERNS["SPECIFIC_LOCATION"].finditer(cleaned))
    if loc_matches:
        total_count += len(loc_matches)
        detected_types.add("LOCATION")
        cleaned = PATTERNS["SPECIFIC_LOCATION"].sub("[REDACTED_LOCATION]", cleaned)

    # Redact Exact Dates
    date_matches = list(PATTERNS["SPECIFIC_DATE"].finditer(cleaned))
    if date_matches:
        total_count += len(date_matches)
        detected_types.add("DATE")
        cleaned = PATTERNS["SPECIFIC_DATE"].sub("[REDACTED_DATE]", cleaned)

    return cleaned, total_count, sorted(list(detected_types))
