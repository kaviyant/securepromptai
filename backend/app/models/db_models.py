# SecurePrompt AI - MongoDB Schema models
# Since MongoDB is NoSQL, these definitions describe the standard structures,
# fields, types, and index requirements used throughout the backend services.

# 1. Collection Name: "users"
# Represents user accounts logged in the database.
# Indices: 
#   - Unique Index: "email"
#   - Unique Index: "username"
USER_DOCUMENT_SCHEMA = {
    "_id": "ObjectId",                 # Primary key
    "username": "str",                 # Unique username login handle
    "email": "str",                    # Unique email address
    "hashed_password": "str",          # Bcrypt hashed password
    "role": "str",                     # RBAC Role: "Admin" or "Employee"
    "department": "str",               # Corporate department group (e.g., "Engineering")
    "is_active": "bool"                # Account activation toggle (default: True)
}

# 2. Collection Name: "prompts_history"
# Audit trail of every scan conducted by the browser extension or direct REST client.
# Indices:
#   - Index: "timestamp" (sorted descending)
#   - Index: "siteKey"
#   - Text Search Index: ["originalPrompt", "reason"]
PROMPT_HISTORY_SCHEMA = {
    "_id": "ObjectId",                 # Primary key
    "timestamp": "datetime",           # Date time prompt scanned (UTC)
    "username": "str",                 # Scanner account or "anonymous_extension"
    "department": "str",               # Department of user during scan
    "website": "str",                  # Host portal URL (e.g. "chatgpt.com/chat")
    "siteKey": "str",                  # Parsed site tag (e.g. "chatgpt")
    "originalPrompt": "str",           # Full user text submitted
    "sanitizedPrompt": "str",          # Redacted prompt version sent to target AI
    "riskScore": "int",                # Security risk assessment score (0 to 100)
    "riskLevel": "str",                # Verdict: "None", "Low", "Medium", "High", "Critical"
    "action": "str",                   # Enforcement: "ALLOW", "WARN", "BLOCK"
    "reason": "str",                   # Scan failure reason warning explanation
    "flaggedTerms": "list[str]",       # Raw text portions that triggered warnings
    "category": "str",                 # Classified content category (e.g., "Finance")
    "complianceStatus": "str",         # Policy match status: "Compliant", "Warning", "Critical"
    "browserInfo": "dict",             # Client system details (Browser, version, OS, UA)
    "session_id": "str"                # Client Browser session identifier
}

# 3. Collection Name: "alerts"
# Tracks critical data leakage breaches that require corporate administrator review.
# Indices:
#   - Index: "timestamp" (sorted descending)
#   - Index: "severity"
ALERT_DOCUMENT_SCHEMA = {
    "_id": "ObjectId",                 # Primary key
    "timestamp": "datetime",           # Time incident triggered (UTC)
    "prompt_id": "ObjectId",           # Reference key to history log entry
    "username": "str",                 # Scanner account or "anonymous_extension"
    "department": "str",               # Corporate department of violating user
    "website": "str",                  # Target AI URL where violation happened
    "severity": "str",                 # Violation level matching: "Medium", "High", "Critical"
    "riskScore": "int",                # Triggering risk score
    "reason": "str",                   # Detail warning reason
    "flaggedTerms": "list[str]",       # Flagged violation terms
    "is_resolved": "bool"              # Incident status review toggle (default: False)
}

# 4. Collection Name: "policies"
# Custom scanning configurations or keywords managed by corporate security administrators.
# Indices:
#   - Unique Index: "name"
POLICY_DOCUMENT_SCHEMA = {
    "_id": "ObjectId",                 # Primary key
    "name": "str",                     # Policy name (e.g., "PII Protection Policy")
    "description": "str",              # Policy details description
    "sensitivity": "int",              # Match sensitivity threshold (1 to 100)
    "is_active": "bool"                # Enable/disable scan check trigger (default: True)
}
