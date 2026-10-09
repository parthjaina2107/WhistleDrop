import re
from typing import Dict, Any, List

SEVERITY_KEYWORDS = {
    "CRITICAL": [
        "data breach", "password", "root access", "credentials", "exfiltrat", "ransomware",
        "physical threat", "violence", "sexual assault", "blackmail", "extort", "kill",
        "weapon", "life threatening", "suicide", "sabotage", "wipe database", "backdoor",
        "sql injection", "unauthorized access to production", "stolen keys", "private key"
    ],
    "HIGH": [
        "harass", "brib", "kickback", "corrupt", "embezzle", "fraud", "forge", "discrimina",
        "retaliat", "cover up", "threaten", "stalk", "abuse", "fake invoice", "rigged",
        "safety violation", "money laundering", "stolen equipment", "illegal"
    ],
    "MEDIUM": [
        "memory leak", "crash", "cluster down", "outage", "database lag", "untested deployment",
        "mismanagement", "conflict of interest", "negligence", "policy violation",
        "inappropriate", "unfair", "unauthorized", "dropped requests", "connection starvation"
    ],
    "LOW": [
        "printer", "cafeteria", "canteen", "parking", "noise", "air conditioning", "ac broken",
        "restroom", "cleanliness", "shuttle bus", "water dispenser", "gym", "laundry",
        "minor", "inconvenience", "suggestion", "slow wifi"
    ]
}

def calculate_severity(text: str, category: str = "Other") -> str:
    """
    Computes report severity level based on weighted keyword signals and category context.
    Returns: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
    """
    text_lower = text.lower()
    
    # 1. Check for immediate critical indicators
    for kw in SEVERITY_KEYWORDS["CRITICAL"]:
        if kw in text_lower:
            return "CRITICAL"

    # 2. Score across levels
    scores = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for level, keywords in SEVERITY_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[level] += 1

    # Apply category contextual baselines
    if category in ["Security", "Corruption"]:
        scores["HIGH"] += 1
    elif category == "Harassment":
        scores["HIGH"] += 1
    elif category == "Technical":
        scores["MEDIUM"] += 1
    elif category == "Other":
        scores["LOW"] += 1

    # Determine highest matching level
    if scores["CRITICAL"] > 0:
        return "CRITICAL"
    if scores["HIGH"] > 0:
        return "HIGH"
    if scores["MEDIUM"] > 0:
        return "MEDIUM"
    if scores["LOW"] > 0:
        return "LOW"

    # Default fallback
    return "MEDIUM"
