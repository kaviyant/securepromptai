import logging
from typing import List, Dict, Any

logger = logging.getLogger("secureprompt")

try:
    import spacy
    import spacy.cli
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False


class NerDetector:
    def __init__(self):
        self.nlp = None
        self._init_spacy()

    def _init_spacy(self):
        """
        Attempts to load spaCy's en_core_web_sm model. 
        If missing, automatically downloads it.
        """
        if not SPACY_AVAILABLE:
            logger.warning("spaCy package is not installed. Named Entity Recognition (NER) is disabled.")
            self.nlp = None
            return

        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy en_core_web_sm model loaded successfully.")
        except OSError:
            logger.info("spaCy en_core_web_sm model not found. Downloading...")
            try:
                spacy.cli.download("en_core_web_sm")
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy model downloaded and loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to auto-download spaCy model: {e}. NER disabled.")
                self.nlp = None

    def scan(self, text: str) -> List[Dict[str, Any]]:
        """
        Runs spaCy NER and maps standard tags (PERSON, ORG, GPE) to PII types.
        """
        if not self.nlp or not text:
            return []

        doc = self.nlp(text)
        findings = []

        # Maps standard spaCy tags to our PII terminology
        tag_mappings = {
            "PERSON": {"type": "NAME", "severity": "MEDIUM", "confidence": 85},
            "ORG": {"type": "ORGANIZATION", "severity": "LOW", "confidence": 80},
            "GPE": {"type": "LOCATION", "severity": "LOW", "confidence": 80},
            "DATE": {"type": "DATE", "severity": "LOW", "confidence": 75}
        }

        for ent in doc.ents:
            if ent.label_ in tag_mappings:
                cfg = tag_mappings[ent.label_]
                val = ent.text
                start, end = ent.start_char, ent.end_char

                # Context Boost: look at context words around Person names
                confidence = cfg["confidence"]
                severity = cfg["severity"]
                
                context_window = text[max(0, start-20):start].lower()
                boost_keywords = ["name is", "i am", "call me", "myself", "mr.", "ms.", "dr."]
                if ent.label_ == "PERSON" and any(k in context_window for k in boost_keywords):
                    confidence = 95
                    severity = "HIGH"

                findings.append({
                    "type": cfg["type"],
                    "value": val,
                    "start": start,
                    "end": end,
                    "confidence": confidence,
                    "severity": severity
                })

        return findings
