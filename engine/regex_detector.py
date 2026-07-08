import re
from typing import List, Dict, Any
from engine.validation import DataValidator
from engine.config import ENTITIES

class RegexDetector:
    def __init__(self):
        # Compile all Regex Patterns
        self.patterns = {
            "EMAIL": re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
            "PHONE": re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            "PASSWORD": re.compile(r'\b(?:password|pwd|passphrase|secret_phrase)\s*[:=]\s*["\']?([A-Za-z0-9_\-.~+=@#$%^&*()]{8,})["\']?', re.IGNORECASE),
            "JWT": re.compile(r'\beyJhbGciOi[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b'),
            "GITHUB_TOKEN": re.compile(r'\b(?:ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82})\b'),
            "GROQ_KEY": re.compile(r'\bgsk_[a-zA-Z0-9]{50}\b'),
            "OPENAI_KEY": re.compile(r'\bsk-[a-zA-Z0-9]{48}\b|\bsk-proj-[a-zA-Z0-9_]{156}\b'),
            "GEMINI_KEY": re.compile(r'\bAIzaSy[A-Za-z0-9_-]{33}\b'),
            "AWS_KEY": re.compile(r'\b(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ASCA|ASIA)[A-Z0-9]{16}\b'),
            "AZURE_KEY": re.compile(r'\b(?:azure|accountkey)\s*[:=]\s*["\']?([a-zA-Z0-9]{44})["\']?', re.IGNORECASE),
            "GOOGLE_KEY": re.compile(r'\bAIzaSy[A-Za-z0-9_-]{33}\b'),
            "SSH_KEY": re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
            "RSA_KEY": re.compile(r'-----BEGIN RSA PRIVATE KEY-----'),
            "DB_MONGO": re.compile(r'mongodb(?:\+srv)?://[a-zA-Z0-9_.~-]+:[a-zA-Z0-9_.~-]+@[a-zA-Z0-9.-]+'),
            "DB_POSTGRES": re.compile(r'postgres(?:ql)?://[a-zA-Z0-9_.~-]+:[a-zA-Z0-9_.~-]+@[a-zA-Z0-9.-]+'),
            "DB_REDIS": re.compile(r'redis://(?:[a-zA-Z0-9_.~-]+:)?(?:[a-zA-Z0-9_.~-]+)@[a-zA-Z0-9.-]+'),
            "CREDIT_CARD": re.compile(r'\b(?:\d[ -]?){13,16}\d\b'),
            "PAN": re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'),
            "AADHAAR": re.compile(r'\b(?:\d{4}\s\d{4}\s\d{4}|\d{12})\b'),
            "PASSPORT": re.compile(r'\b[A-Z0-9]{6,9}\b'), # checked contextually
            "IBAN": re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b'),
            "BANK_ACCOUNT": re.compile(r'\b\d{9,18}\b'), # checked contextually
            "IFSC": re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b'),
            "CUSTOMER_ID": re.compile(r'\b(?:cust|customer)[_-]?id\s*[:=]\s*["\']?([a-zA-Z0-9-]{6,15})["\']?', re.IGNORECASE),
            "EMPLOYEE_ID": re.compile(r'\b(?:emp|employee)[_-]?id\s*[:=]\s*["\']?([a-zA-Z0-9-]{4,15})["\']?', re.IGNORECASE),
            "MEDICAL_RECORD": re.compile(r'\b(?:mrn|medical[_-]?record)\s*[:=]\s*["\']?(\d{6,12})["\']?', re.IGNORECASE),
            "SSN": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "IP_ADDRESS": re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
            "MAC_ADDRESS": re.compile(r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'),
            "COOKIE": re.compile(r'\b(?:cookie|sessionid)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.IGNORECASE),
            "SESSION_ID": re.compile(r'\b(?:sess|session)[_-]?id\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?', re.IGNORECASE),
            "ENV_VAR": re.compile(r'\b([A-Z_]{3,20})\s*=\s*["\']?([A-Za-z0-9_\-.~+=@#$%^&*()]{8,})["\']?'),
            "SECRET": re.compile(r'\b(?:secret|private[_-]?key|passkey)\s*[:=]\s*["\']?([A-Za-z0-9_\-.~+=@#$%^&*()]{16,})["\']?', re.IGNORECASE),
            "CERTIFICATE": re.compile(r'-----BEGIN CERTIFICATE-----'),
            "CODE_SECRET": re.compile(r'\b(?:token|auth|key|secret)\s*[:=]\s*["\']?([A-Za-z0-9_-]{16,})["\']?', re.IGNORECASE)
        }

    def scan(self, text: str) -> List[Dict[str, Any]]:
        """
        Scans raw text and runs regex matches against all 33 categories.
        Validates check digits mathematically (Luhn/Verhoeff/IBAN) to prune false positives.
        """
        findings = []
        text_lower = text.lower()

        for ent_type, regex in self.patterns.items():
            matches = regex.finditer(text)
            for m in matches:
                val = m.group(0)
                start, end = m.span()
                
                # Check for sub-groups if specific tokens are captured (like password value)
                val_extract = val
                if regex.groups > 0:
                    try:
                        val_extract = m.group(regex.groups)
                    except IndexError:
                        pass
                
                # Apply Mathematical Checksum Validation Filters
                if ent_type == "CREDIT_CARD":
                    if not DataValidator.luhn_check(val):
                        continue
                
                elif ent_type == "AADHAAR":
                    if not DataValidator.verhoeff_check(val):
                        continue
                        
                elif ent_type == "IBAN":
                    if not DataValidator.iban_check(val):
                        continue
                
                # Apply context boundary filters for high false positive rates
                elif ent_type == "PASSPORT":
                    # Passport needs nearby words like "passport", "travel"
                    context_words = ["passport", "passport#", "travel", "doc"]
                    if not any(w in text_lower[max(0, start-30):min(len(text), end+30)] for w in context_words):
                        continue
                        
                elif ent_type == "BANK_ACCOUNT":
                    # Bank account needs nearby words like "bank", "account", "routing"
                    context_words = ["bank", "account", "routing", "savings", "checking", "deposit"]
                    if not any(w in text_lower[max(0, start-35):min(len(text), end+35)] for w in context_words):
                        continue

                # Fetch settings for config mapping
                cfg = ENTITIES[ent_type]
                findings.append({
                    "type": ent_type,
                    "value": val_extract,
                    "start": start,
                    "end": end,
                    "confidence": cfg["default_confidence"],
                    "severity": cfg["severity"]
                })

        return findings
