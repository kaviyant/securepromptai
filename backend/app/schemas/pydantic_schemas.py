from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any
from datetime import datetime

# 1. User & Auth Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["john_doe"])
    email: EmailStr = Field(..., examples=["john@secureprompt.ai"])
    password: str = Field(..., min_length=6, examples=["SecurePass123!"])
    role: str = Field("Employee", pattern="^(Admin|Employee)$", examples=["Employee"])
    department: str = Field(..., examples=["Engineering"])

class UserLogin(BaseModel):
    username: str = Field(..., examples=["john_doe"])
    password: str = Field(..., examples=["SecurePass123!"])

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    username: str
    email: EmailStr
    role: str
    department: str
    is_active: bool

    class Config:
        populate_by_name = True

# 2. Browser Scan Payload & Response (Integrates with Extension)
class BrowserInfoSchema(BaseModel):
    browser: str = Field(..., examples=["Chrome"])
    browserVersion: str = Field(..., examples=["120.0.0.0"])
    os: str = Field(..., examples=["Windows"])
    userAgent: str = Field(..., examples=["Mozilla/5.0..."])

class PromptScanRequest(BaseModel):
    prompt: str = Field(..., examples=["Please analyze this code: AWS_KEY='AKIA...'"])
    website: str = Field(..., examples=["chatgpt.com"])
    timestamp: int = Field(..., examples=[1680000000000])
    session_id: str = Field(..., examples=["uuid-1234-5678"])
    browser_info: BrowserInfoSchema
    uploaded_files: Optional[List[str]] = Field(default=[], examples=[["confidential_report.pdf"]])

class PromptScanResponse(BaseModel):
    risk_score: int = Field(..., ge=0, le=100, examples=[95])
    risk_level: str = Field(..., examples=["Critical"])
    action: str = Field(..., examples=["BLOCK"])
    sanitized_prompt: str = Field(..., examples=["Please analyze this code: AWS_KEY='[REDACTED_AWS_KEY]'"])
    reason: Optional[str] = Field(None, examples=["AWS Access Key detected."])
    flagged_terms: List[str] = Field(default=[], examples=["AKIA1234567890EXAMPLE"])

# 3. Sanitize & Classify Payload
class PromptSanitizeRequest(BaseModel):
    prompt: str = Field(..., examples=["My email is test@domain.com"])

class PromptSanitizeResponse(BaseModel):
    sanitized_prompt: str
    flagged_terms: List[str]

class PromptClassifyRequest(BaseModel):
    prompt: str = Field(..., examples=["Review our Q2 financial growth targets"])

class PromptClassifyResponse(BaseModel):
    category: str = Field(..., examples=["Finance / Business Operations"])
    compliance_status: str = Field(..., examples=["Warning"])
    flagged_policies: List[str] = Field(default=[])

# 4. LLM Interface
class LLMProxyRequest(BaseModel):
    model: str = Field("gpt-4", examples=["gpt-4"])
    prompt: str = Field(..., examples=["Hello, summarize this context..."])

# 5. Dashboard & Analytics
class DashboardStatsResponse(BaseModel):
    total_scans: int
    allowed_count: int
    warned_count: int
    blocked_count: int
    risk_distribution: Dict[str, int]
    activity_timeline: List[Dict[str, Any]]

class StatisticsResponse(BaseModel):
    top_flagged_terms: List[Dict[str, Any]]
    department_violations: List[Dict[str, Any]]
    category_shares: Dict[str, int]

# 6. Policies Models
class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., max_length=300)
    sensitivity: int = Field(50, ge=1, le=100)
    is_active: bool = True

class PolicyResponse(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    description: str
    sensitivity: int
    is_active: bool

    class Config:
        populate_by_name = True
