import re
from typing import Dict, Any, List

class ContentClassifier:
    # Score Vector classification dictionaries
    CATEGORIES = {
        "Source Code & Engineering": {
            "keywords": ["def ", "class ", "import ", "function", "const ", "console.log", "public class", "fn ", "struct ", "repository", "docker", "k8s", "deploy", "auth", "encrypt", "decrypt", "sql", "select *", "database schema"],
            "weight": 1.5
        },
        "Finance & Accounting": {
            "keywords": ["revenue", "margin", "forecast", "ebitda", "q1", "q2", "q3", "q4", "fiscal year", "profit", "loss", "balance sheet", "ledger", "audit", "expensing", "compliance filing", "stock price", "investor report"],
            "weight": 1.2
        },
        "Healthcare & Patient Records": {
            "keywords": ["hipaa", "phi", "patient", "medical history", "diagnosis", "prescription", "mri", "treatment", "electronic health record", "clinic", "symptoms", "health insurance", "physician", "hospitalization"],
            "weight": 1.4
        },
        "Intellectual Property & Patents": {
            "keywords": ["patent", "proprietary", "trade secret", "confidential", "nda", "product blueprint", "merger", "acquisition", "strategic roadmap", "internal design", "draft patent", "competitor analysis"],
            "weight": 1.3
        },
        "HR & Employee Records": {
            "keywords": ["employee review", "salary band", "payroll", "disciplinary", "termination", "offer letter", "resume", "hiring pipeline", "performance review", "social security", "background check"],
            "weight": 1.0
        }
    }

    @classmethod
    def classify(cls, prompt_text: str) -> Dict[str, Any]:
        """
        Calculates category scores using vector matches and returns the winning category
        and compliance policy status.
        """
        text_lower = prompt_text.lower()
        scores = {}

        # 1. Calculate matching density score
        for category, config in cls.CATEGORIES.items():
            matches = 0
            for kw in config["keywords"]:
                # Match full words or specific code segments
                if kw in text_lower:
                    matches += text_lower.count(kw)
            
            scores[category] = matches * config["weight"]

        # 2. Get winning category
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]

        # Default fallback if no match density
        if best_score == 0:
            best_category = "General Inquiry"
            compliance_status = "Compliant"
            flagged_policies = []
        else:
            # 3. Policy validation checks based on categories
            flagged_policies = []
            compliance_status = "Compliant"

            if best_category == "Source Code & Engineering":
                # Check if it looks like sensitive internal source code
                if len(prompt_text) > 400 or "database" in text_lower or "credentials" in text_lower:
                    compliance_status = "Warning"
                    flagged_policies.append("Engineering Source Code Sharing Policy")
                    
            elif best_category == "Finance & Accounting":
                if any(k in text_lower for k in ["forecast", "margin", "ebitda"]):
                    compliance_status = "Warning"
                    flagged_policies.append("Corporate Financial Disclosure Policy")
                    
            elif best_category == "Healthcare & Patient Records":
                compliance_status = "Critical"
                flagged_policies.append("HIPAA Privacy Regulation Policy")
                
            elif best_category == "Intellectual Property & Patents":
                if "proprietary" in text_lower or "secret" in text_lower or "patent" in text_lower:
                    compliance_status = "Critical"
                    flagged_policies.append("IP Theft & Trade Secret Policy")
                    
            elif best_category == "HR & Employee Records":
                if any(k in text_lower for k in ["disciplinary", "salary", "termination"]):
                    compliance_status = "Warning"
                    flagged_policies.append("Employee Private Information Policy")

        return {
            "category": best_category,
            "compliance_status": compliance_status,
            "flagged_policies": flagged_policies
        }
