import os
import joblib
from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from app.config import settings

# Enriched realistic seed dataset covering all 5 GDG categories
SEED_TRAINING_DATA = [
    # --- SECURITY ---
    ("Someone unauthorized gained root access to our production database and exfiltrated user records.", "Security"),
    ("Unauthorized access detected in the production database with stolen credentials.", "Security"),
    ("I discovered exposed AWS API keys and credentials hardcoded in the public repository.", "Security"),
    ("A developer bypassed 2-factor authentication on the corporate admin console.", "Security"),
    ("Sensitive student passwords and personal records are being stored in plain text in an open S3 bucket.", "Security"),
    ("Ransomware payload detected on the internal file storage server after a phishing email was clicked.", "Security"),
    ("A backdoor script was introduced into the build pipeline allowing external shell execution.", "Security"),
    ("Confidential customer payment cards and CVV numbers are logged unencrypted in application logs.", "Security"),
    ("An ex-employee still has active VPN access and was seen downloading internal source code.", "Security"),
    ("SQL injection vulnerability in the student login portal allows dumping the entire marks database.", "Security"),
    ("Private encryption keys were copied onto an unauthorized personal USB flash drive.", "Security"),
    ("Firewall rules were intentionally disabled on the payment gateway cluster.", "Security"),
    ("DDoS attack vulnerability knowingly left unpatched before the university registration rush.", "Security"),
    ("Security breach: hackers compromised employee accounts and accessed private data.", "Security"),
    ("Malware planted inside the server cluster intercepting SSL traffic.", "Security"),

    # --- HARASSMENT ---
    ("My team lead repeatedly sends inappropriate and suggestive text messages late at night.", "Harassment"),
    ("A senior professor threatened to fail my semester project if I did not agree to personal favors.", "Harassment"),
    ("Persistent racial slurs and derogatory remarks directed towards junior team members during standups.", "Harassment"),
    ("A manager is intentionally isolating and screaming at female colleagues in front of the entire department.", "Harassment"),
    ("I am being stalked by a coworker after work hours, and HR has dismissed my formal complaints.", "Harassment"),
    ("Toxic work environment where the director uses abusive language and physical intimidation.", "Harassment"),
    ("Retaliatory bullying and mocking because I reported an ethical violation to compliance.", "Harassment"),
    ("Unwelcome physical touching and sexual advances during the departmental annual dinner.", "Harassment"),
    ("Team leader is blackmailing junior interns, threatening poor evaluation ratings if they speak up.", "Harassment"),
    ("Humiliation and verbal disparagement based on religion and caste in the faculty lounge.", "Harassment"),
    ("Workplace harassment: constant verbal abuse and derogatory jokes targeted at my colleagues.", "Harassment"),
    ("Sexual harassment by supervisor who makes inappropriate advances in the office.", "Harassment"),

    # --- CORRUPTION ---
    ("The department head accepted cash kickbacks to award the hardware vendor contract.", "Corruption"),
    ("Finance officer is creating fake vendor invoices and routing university funds to a personal shell company.", "Corruption"),
    ("Bribes being solicited from students in exchange for approving attendance shortfalls.", "Corruption"),
    ("A senior executive embezzled funds allocated for research grants and lab equipment.", "Corruption"),
    ("Tender bidding process was rigged to favor a company owned by the director's brother-in-law.", "Corruption"),
    ("Internal auditor was paid off to overlook massive financial discrepancies in the annual report.", "Corruption"),
    ("Dean is demanding money from international students under the pretext of bogus processing fees.", "Corruption"),
    ("Lab equipment purchased with government grant money was stolen and redirected to a private tutoring center.", "Corruption"),
    ("HR manager is demanding a cut of recruit referral bonuses for approving candidate selections.", "Corruption"),
    ("Misuse of university vehicles and departmental budget for lavish private family vacations.", "Corruption"),
    ("Procurement officer taking bribery and illegal commissions from contractors.", "Corruption"),
    ("Financial fraud: manipulating balance sheets and stealing grant funds.", "Corruption"),

    # --- TECHNICAL ---
    ("The primary database cluster crashes every night at midnight due to unhandled memory leaks.", "Technical"),
    ("Production Kubernetes cluster went down for four hours because of an untested deployment script.", "Technical"),
    ("Backup restoration pipeline has been failing silently for three months with zero valid snapshots.", "Technical"),
    ("Campus Wi-Fi authentication portal is rejecting valid student credentials due to LDAP certificate expiration.", "Technical"),
    ("Core payment microservice is dropping 30% of webhook requests during peak transaction volume.", "Technical"),
    ("Database replication lag has exceeded 48 hours causing inconsistent data between read and write nodes.", "Technical"),
    ("Application server ran out of disk space because rotating log files were never configured.", "Technical"),
    ("The grading portal crashed during the final submission deadline due to connection pool starvation.", "Technical"),
    ("CI/CD pipeline failed due to outdated Node.js runner images breaking all team builds.", "Technical"),
    ("A major bug in the attendance calculation algorithm miscalculated thousands of student eligibility records.", "Technical"),
    ("Server outage: critical software bug caused continuous system downtime.", "Technical"),
    ("Application memory crash causing 500 internal server error for all users.", "Technical"),

    # --- OTHER ---
    ("The cafeteria is serving spoiled food and expired milk cartons in the university hostel.", "Other"),
    ("Designated parking spaces for disabled individuals are consistently blocked by delivery trucks.", "Other"),
    ("Broken air conditioning in the library makes the third-floor study hall completely unusable.", "Other"),
    ("Cleanliness and sanitation standards in the north campus restrooms are severely neglected.", "Other"),
    ("Dispute regarding arbitrary changes to the campus shuttle bus schedule without prior notice.", "Other"),
    ("Excessive construction noise right outside the exam halls during morning assessment hours.", "Other"),
    ("Stray dogs entering the hostel corridors causing safety hazards for resident students.", "Other"),
    ("Gymnasium equipment is broken and unmaintained despite recent sports fee hike.", "Other"),
    ("General complaint about the lack of drinking water dispensers on the fourth floor of the tech park.", "Other"),
    ("Hostel laundry service consistently losing clothes and refusing to compensate students.", "Other"),
    ("Complaints about library book overdue fines and uncomfortable classroom seating.", "Other"),
]

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL_FILE = os.path.join(MODEL_DIR, "whistledrop_classifier.joblib")

class WhistleDropClassifier:
    def __init__(self):
        self.pipeline: Pipeline = None
        if os.path.exists(MODEL_FILE):
            try:
                self.pipeline = joblib.load(MODEL_FILE)
            except Exception:
                self._train()
        else:
            self._train()

    def _train(self):
        """Trains a high-precision TF-IDF + Multinomial Naive Bayes classifier."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        texts, labels = zip(*SEED_TRAINING_DATA)
        
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                max_features=6000,
                stop_words="english"
            )),
            ("nb", MultinomialNB(alpha=0.15))
        ])
        
        self.pipeline.fit(texts, labels)
        joblib.dump(self.pipeline, MODEL_FILE)

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Predicts category, calculates calibrated confidence, and determines review flag.
        Returns:
            {
                "predicted_category": str,
                "confidence": float (0.0 to 1.0),
                "decision": "AUTO_CLASSIFY" | "REVIEW_RECOMMENDED" | "MANUAL_REVIEW_REQUIRED",
                "probabilities": dict of category -> prob
            }
        """
        if not self.pipeline:
            self._train()

        probabilities = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        
        prob_dict = {str(cls): float(round(prob, 4)) for cls, prob in zip(classes, probabilities)}
        best_idx = probabilities.argmax()
        best_class = str(classes[best_idx])
        confidence = float(round(probabilities[best_idx], 4))

        # Three-tier decision framework based on the approved implementation plan
        if confidence >= settings.CONFIDENCE_AUTO_CLASSIFY_THRESHOLD:
            decision = "AUTO_CLASSIFY"
            final_category = best_class
        elif confidence >= settings.CONFIDENCE_REVIEW_THRESHOLD:
            decision = "REVIEW_RECOMMENDED"
            final_category = best_class
        else:
            decision = "MANUAL_REVIEW_REQUIRED"
            final_category = best_class if confidence > 0.30 else "Other"

        return {
            "predicted_category": final_category,
            "raw_category": best_class,
            "confidence": confidence,
            "decision": decision,
            "probabilities": prob_dict
        }

# Global singleton
classifier = WhistleDropClassifier()
