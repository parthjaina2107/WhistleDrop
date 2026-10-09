import json
import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from app.config import settings

class ReportSimilarityEngine:
    """
    Computes semantic vector representations of redacted report text
    and identifies duplicate or co-related whistleblower incidents.
    """
    def __init__(self):
        # 256-dimensional sublinear TF-IDF representation
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            sublinear_tf=True,
            max_features=256,
            stop_words="english"
        )
        # Seed corpus to establish standard vocabulary
        from app.services.ml_classifier import SEED_TRAINING_DATA
        seed_texts = [text for text, _ in SEED_TRAINING_DATA]
        self.vectorizer.fit(seed_texts)

    def encode(self, text: str) -> List[float]:
        """Encodes report text into a normalized dense feature vector."""
        if not text:
            return [0.0] * 256
        vec = self.vectorizer.transform([text]).toarray()[0]
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return [float(round(val, 5)) for val in vec]

    def compute_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Computes cosine similarity between two vector representations."""
        if not vec_a or not vec_b:
            return 0.0
        a = np.array(vec_a)
        b = np.array(vec_b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        sim = float(np.dot(a, b) / (norm_a * norm_b))
        return float(round(max(0.0, min(1.0, sim)), 4))

    def find_similar(
        self,
        target_vec: List[float],
        target_id: str,
        candidates: List[Any],
        threshold: float = 0.65,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Scans candidate reports to find semantically related or duplicate cases.
        """
        results = []
        for candidate in candidates:
            if candidate.id == target_id:
                continue
            if not candidate.embedding:
                continue
            try:
                cand_vec = json.loads(candidate.embedding)
            except Exception:
                continue

            sim = self.compute_similarity(target_vec, cand_vec)
            if sim >= threshold:
                results.append({
                    "id": candidate.id,
                    "case_code": candidate.case_code,
                    "category": candidate.category,
                    "status": candidate.status,
                    "severity": candidate.severity,
                    "similarity": round(sim, 3)
                })

        # Sort highest similarity first
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

similarity_engine = ReportSimilarityEngine()
