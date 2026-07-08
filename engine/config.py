# SecurePrompt AI - Sensitive Data Detection Engine Configurations

# Severity constants
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

# Supported Entity Type identifiers (33 types)
ENTITIES = {
    "EMAIL": {"severity": SEVERITY_HIGH, "default_confidence": 99},
    "PHONE": {"severity": SEVERITY_MEDIUM, "default_confidence": 95},
    "PASSWORD": {"severity": SEVERITY_CRITICAL, "default_confidence": 90},
    "JWT": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "GITHUB_TOKEN": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "GROQ_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "OPENAI_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "GEMINI_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "AWS_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "AZURE_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "GOOGLE_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "SSH_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "RSA_KEY": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "DB_MONGO": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "DB_POSTGRES": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "DB_REDIS": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "CREDIT_CARD": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "PAN": {"severity": SEVERITY_HIGH, "default_confidence": 99},
    "AADHAAR": {"severity": SEVERITY_HIGH, "default_confidence": 99},
    "PASSPORT": {"severity": SEVERITY_HIGH, "default_confidence": 99},
    "IBAN": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "BANK_ACCOUNT": {"severity": SEVERITY_HIGH, "default_confidence": 90},
    "IFSC": {"severity": SEVERITY_MEDIUM, "default_confidence": 99},
    "CUSTOMER_ID": {"severity": SEVERITY_MEDIUM, "default_confidence": 85},
    "EMPLOYEE_ID": {"severity": SEVERITY_MEDIUM, "default_confidence": 85},
    "MEDICAL_RECORD": {"severity": SEVERITY_HIGH, "default_confidence": 90},
    "SSN": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "IP_ADDRESS": {"severity": SEVERITY_LOW, "default_confidence": 95},
    "MAC_ADDRESS": {"severity": SEVERITY_MEDIUM, "default_confidence": 99},
    "COOKIE": {"severity": SEVERITY_HIGH, "default_confidence": 95},
    "SESSION_ID": {"severity": SEVERITY_HIGH, "default_confidence": 95},
    "ENV_VAR": {"severity": SEVERITY_HIGH, "default_confidence": 90},
    "SECRET": {"severity": SEVERITY_CRITICAL, "default_confidence": 90},
    "CERTIFICATE": {"severity": SEVERITY_CRITICAL, "default_confidence": 99},
    "CODE_SECRET": {"severity": SEVERITY_CRITICAL, "default_confidence": 95}
}

# General confidence thresholds
CONFIDENCE_THRESHOLD = 40
