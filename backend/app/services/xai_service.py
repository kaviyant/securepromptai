import re
from typing import List, Dict, Any

class XaiService:
    @staticmethod
    def generate_explanation(
        prompt_text: str,
        entities: List[Dict[str, Any]],
        risk_score: int,
        risk_level: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Generates Explainable AI (XAI) metadata:
        1. Compiles a highlighted version of the prompt (Markdown style).
        2. Explains the reasons for the risk level.
        3. Provides recommendations for safety remediation.
        """
        
        # 1. Generate Highlighted Prompt (wrap flagged words in ==highlight== syntax)
        highlighted_prompt = prompt_text
        # Sort entities by start index descending to avoid character shift issues during replacement
        sorted_entities = sorted(entities, key=lambda x: x.get("start", 0), reverse=True)
        
        # Use offset slice replacement to be robust
        chars = list(prompt_text)
        for ent in sorted_entities:
            start = ent.get("start")
            end = ent.get("end")
            val = ent.get("value")
            ent_type = ent.get("type", "SENSITIVE")
            
            if start is not None and end is not None and val:
                highlighted_text = f"=={val} [{ent_type}]=="
                chars[start:end] = list(highlighted_text)
                
        highlighted_prompt = "".join(chars)

        # 2. Formulate Reasonings
        reasons = []
        if risk_level == "CRITICAL":
            reasons.append("The prompt contains high-impact credentials or secrets (such as API keys, passwords, or DB connections) that must never be shared with LLMs.")
        elif risk_level == "HIGH":
            reasons.append("We identified multiple high-risk PII tokens (such as SSNs, Passports, or Aadhaar) or code blocks containing potential data leaks.")
        elif risk_level == "MEDIUM":
            reasons.append("The prompt contains moderate risk parameters, such as personal contact emails, IP addresses, or internal financial terminology.")
        else:
            reasons.append("The prompt contains general query structures and complies with corporate safety standards.")

        # Add category-specific reasons
        category_reasons = {
            "Finance": "Discussing corporate EBITDA, revenue growth, or investment ledger sheets.",
            "Healthcare": "Contains references to medical record numbers (MRNs) or patient electronic health records (HIPAA).",
            "Legal": "Refers to legal contract drafts, NDA provisions, or copyright claims.",
            "HR": "Relates to performance sheets, salary bands, or hiring status lists.",
            "Security": "Shares firewall access flags, access configurations, or threat scanner logs."
        }
        if category in category_reasons:
            reasons.append(f"Category Context: {category_reasons[category]}")

        # 3. Formulate Actionable Recommendations
        recommendations = []
        if risk_level in ["CRITICAL", "HIGH"]:
            recommendations.append("Action Required: submission blocked.")
            recommendations.append("1. Redact all raw API keys, passwords, and private certificates immediately.")
            recommendations.append("2. Replace real user SSNs or passwords with fake mock values before submitting.")
            recommendations.append("3. For developers: retrieve secrets programmatically using Key Vaults (AWS Secrets Manager, HashiCorp Vault) rather than hardcoding them.")
        elif risk_level == "MEDIUM":
            recommendations.append("Suggestion: sanitize prompt elements.")
            recommendations.append("1. Toggle 'Auto-Redact' in your settings panel to replace email/phone values with safe placeholders.")
            recommendations.append("2. Avoid sharing specific customer IDs or internal database details.")
        else:
            recommendations.append("No actions needed. Prompt is safe for submission.")

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "category": category,
            "highlighted_prompt": highlighted_prompt,
            "reasons": reasons,
            "recommendations": recommendations,
            "confidence_score": 95 if risk_level == "CRITICAL" else 85
        }
