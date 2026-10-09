import re
import secrets

# Character set excluding visually ambiguous characters:
# Excluded: 0, O (zero vs capital O), 1, I (one vs capital I)
# 32 characters total -> 32^12 ≈ 1.15 x 10^18 combinations
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CASE_CODE_REGEX = re.compile(r"^WD-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")

def generate_case_code() -> str:
    """
    Generates a cryptographically strong, unguessable case code.
    Format: WD-XXXX-XXXX-XXXX
    Example: WD-8F4K-92QP-X7LM
    """
    parts = []
    for _ in range(3):
        chunk = "".join(secrets.choice(CHARSET) for _ in range(4))
        parts.append(chunk)
    return f"WD-{'-'.join(parts)}"

def is_valid_case_code_format(code: str) -> bool:
    """Validates if a given string matches the required case code format."""
    if not code or not isinstance(code, str):
        return False
    return bool(CASE_CODE_REGEX.match(code.strip().upper()))
