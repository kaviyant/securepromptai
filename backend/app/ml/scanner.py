import re
from typing import Tuple, List, Dict, Any

# Compiled Regex Patterns for PII
EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b')
PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
SSN_REGEX = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
IPV4_REGEX = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')

# Compiled Regex Patterns for Credentials / Secrets
AWS_KEY_REGEX = re.compile(r'\b(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ASCA|ASIA)[A-Z0-9]{16}\b')
GITHUB_TOKEN_REGEX = re.compile(r'\b(ghp_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82})\b')
SLACK_WEBHOOK_REGEX = re.compile(r'https://hooks\.slack\.com/services/T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}')
STRIPE_KEY_REGEX = re.compile(r'\brk_live_[0-9a-zA-Z]{24}\b|\bsk_live_[0-9a-zA-Z]{24}\b')
PRIVATE_KEY_REGEX = re.compile(r'-----BEGIN [A-Z ]+PRIVATE KEY-----')
GENERIC_SECRET_REGEX = re.compile(
    r'\b(api[_-]?key|secret|password|auth[_-]?token|access[_-]?token)\b\s*[:=]\s*["\']([A-Za-z0-9_\-.~+=]{16,})["\']',
    re.IGNORECASE
)

# Broad numeric sweep for Credit Cards (Checked via Luhn algorithm)
CARD_NUMBER_REGEX = re.compile(r'\b(?:\d[ -]?){13,16}\d\b')

def luhn_checksum(card_number: str) -> bool:
    """
    Validates a credit card number using Luhn's algorithm.
    """
    # Strip spaces and dashes
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    
    # Luhn checksum double-every-other logic
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled if doubled < 10 else doubled - 9
        else:
            checksum += digit
    return checksum % 10 == 0

class PromptScanner:
    @staticmethod
    def scan(prompt_text: str, sensitivity_threshold: int = 50) -> Dict[str, Any]:
        """
        Scans a prompt for PII, API tokens, and credentials.
        Returns risk score, risk level, action, sanitized text, reasons, and flagged terms.
        """
        flagged_terms = []
        violations = []
        sanitized_prompt = prompt_text

        # 1. Scan for Credit Cards
        card_matches = CARD_NUMBER_REGEX.finditer(prompt_text)
        for match in card_matches:
            raw_val = match.group(0)
            clean_digits = "".join(filter(str.isdigit, raw_val))
            # Validate Luhn checksum to avoid high rate of false positives
            if luhn_checksum(clean_digits):
                flagged_terms.append(raw_val)
                violations.append("Credit Card Number")
                sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_CREDIT_CARD]")

        # 2. Scan for PII
        # Email Addresses
        email_matches = EMAIL_REGEX.finditer(prompt_text)
        for match in email_matches:
            raw_val = match.group(0)
            flagged_terms.append(raw_val)
            violations.append("Email Address")
            sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_EMAIL]")

        # SSNs
        ssn_matches = SSN_REGEX.finditer(prompt_text)
        for match in ssn_matches:
            raw_val = match.group(0)
            flagged_terms.append(raw_val)
            violations.append("SSN")
            sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_SSN]")

        # Phone Numbers
        phone_matches = PHONE_REGEX.finditer(prompt_text)
        for match in phone_matches:
            raw_val = match.group(0)
            # Avoid single short digit matches by ensuring length is reasonable
            if len("".join(filter(str.isdigit, raw_val))) >= 10:
                flagged_terms.append(raw_val)
                violations.append("Phone Number")
                sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_PHONE_NUMBER]")

        # IPv4 Addresses
        ip_matches = IPV4_REGEX.finditer(prompt_text)
        for match in ip_matches:
            raw_val = match.group(0)
            # Filter standard loopbacks unless sensitivity is very high
            if raw_val not in ["127.0.0.1", "0.0.0.0"] or sensitivity_threshold > 70:
                flagged_terms.append(raw_val)
                violations.append("IP Address")
                sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_IP_ADDRESS]")

        # 3. Scan for Credentials & API Keys
        # AWS Access Key
        aws_matches = AWS_KEY_REGEX.finditer(prompt_text)
        for match in aws_matches:
            raw_val = match.group(0)
            flagged_terms.append(raw_val)
            violations.append("AWS Access Key ID")
            sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_AWS_KEY]")

        # GitHub Pat
        gh_matches = GITHUB_TOKEN_REGEX.finditer(prompt_text)
        for match in gh_matches:
            raw_val = match.group(0)
            flagged_terms.append(raw_val)
            violations.append("GitHub Access Token")
            sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_GITHUB_TOKEN]")

        # Slack Webhook URLs
        slack_matches = SLACK_WEBHOOK_REGEX.finditer(prompt_text)
        for match in slack_matches:
            raw_val = match.group(0)
            flagged_terms.append(raw_val)
            violations.append("Slack Webhook URL")
            sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_SLACK_WEBHOOK]")

        # Stripe live tokens
        stripe_matches = STRIPE_KEY_REGEX.finditer(prompt_text)
        for match in stripe_matches:
            raw_val = match.group(0)
            flagged_terms.append(raw_val)
            violations.append("Stripe Secret Key")
            sanitized_prompt = sanitized_prompt.replace(raw_val, "[REDACTED_STRIPE_KEY]")

        # SSH Private Keys
        pk_matches = PRIVATE_KEY_REGEX.finditer(prompt_text)
        for match in pk_matches:
            raw_val = match.group(0)
            # Redact the whole prompt portion starting with private key block for safety
            flagged_terms.append("-----BEGIN PRIVATE KEY-----")
            violations.append("SSH Private Key")
            # Truncate or mask the whole block
            lines = prompt_text.splitlines()
            cleaned_lines = []
            in_key = False
            for line in lines:
                if "-----BEGIN" in line and "PRIVATE KEY" in line:
                    in_key = True
                    cleaned_lines.append("[REDACTED_PRIVATE_SSH_KEY_BLOCK]")
                elif "-----END" in line and "PRIVATE KEY" in line:
                    in_key = False
                elif not in_key:
                    cleaned_lines.append(line)
            sanitized_prompt = "\n".join(cleaned_lines)

        # Generic credentials check (api_key = "abc")
        gen_matches = GENERIC_SECRET_REGEX.finditer(prompt_text)
        for match in gen_matches:
            full_match = match.group(0)
            key_name = match.group(1)
            secret_val = match.group(2)
            flagged_terms.append(secret_val)
            violations.append(f"Generic Secret ({key_name})")
            sanitized_prompt = sanitized_prompt.replace(full_match, f"{key_name}: \"[REDACTED_SECRET]\"")

        # 4. Calculate Risk Metrics
        unique_violations = list(set(violations))
        risk_score = 0
        action = "ALLOW"
        reason = ""

        # Weight assignment based on violation types
        critical_types = ["Credit Card Number", "AWS Access Key ID", "GitHub Access Token", "Slack Webhook URL", "Stripe Secret Key", "SSH Private Key"]
        high_types = ["SSN"]
        medium_types = ["Email Address", "Phone Number", "IP Address", "Generic Secret"]

        # Calculate Score
        for v_type in unique_violations:
            if v_type in critical_types:
                risk_score += 95
            elif v_type in high_types:
                risk_score += 85
            elif any(m in v_type for m in medium_types):
                risk_score += 40
            else:
                risk_score += 15

        # Cap score at 100
        risk_score = min(risk_score, 100)

        # Map risk score to level and actions
        if risk_score >= 90:
            risk_level = "Critical"
            action = "BLOCK"
            reason = f"Critical risk detected: {', '.join(unique_violations)}. Access blocked."
        elif risk_score >= 70:
            risk_level = "High"
            action = "BLOCK"
            reason = f"High risk data leakage detected: {', '.join(unique_violations)}."
        elif risk_score >= 40:
            risk_level = "Medium"
            # Medium risks trigger a WARNING popup to let the user decide
            risk_level = "Medium"
            action = "WARN"
            reason = f"Medium risk alert: Contains {', '.join(unique_violations)}. Review before sending."
        elif risk_score >= 10:
            risk_level = "Low"
            # Low risks are allowed but logged and sanitized if required
            action = "ALLOW"
            reason = f"Low risk content identified: {', '.join(unique_violations)}."
        else:
            risk_level = "None"
            action = "ALLOW"
            reason = "No sensitive data signatures detected."

        # If user settings sensitivity is high, lower the thresholds for warnings/blocks
        if sensitivity_threshold > 75 and action == "ALLOW" and risk_score > 0:
            action = "WARN"
            reason += " (Upgraded to Warning due to high security sensitivity threshold)"

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "action": action,
            "sanitized_prompt": sanitized_prompt,
            "reason": reason,
            "flagged_terms": list(set(flagged_terms))
        }
