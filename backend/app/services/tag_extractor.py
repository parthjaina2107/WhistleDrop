import re
from typing import List
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

CUSTOM_STOP_WORDS = set(ENGLISH_STOP_WORDS).union({
    "report", "someone", "said", "told", "like", "just", "know", "going", "want",
    "thing", "things", "redacted", "person", "email", "phone", "location", "date"
})

def extract_tags(text: str, top_n: int = 5) -> List[str]:
    """
    Extracts key thematic tags and entities from the sanitized report narrative.
    """
    if not text:
        return []

    # Tokenize words, lowercase, strip punctuation
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    
    # Filter stopwords
    filtered = [w for w in words if w not in CUSTOM_STOP_WORDS]
    
    # Word frequency count
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1

    # Sort by frequency desc
    sorted_words = sorted(freq.keys(), key=lambda w: freq[w], reverse=True)
    return sorted_words[:top_n]
