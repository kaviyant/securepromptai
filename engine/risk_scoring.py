from typing import Dict, Any

class RiskScoringEngine:
    @staticmethod
    def calculate_score(
        sensitive_data_level: str,  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
        source_code_lang: str,       # "Python", "Java", etc. or None
        source_code_has_secrets: bool,
        similarity_score: float,     # 0.0 to 1.0 similarity with company docs
        prompt_category: str,        # "General", "Finance", "Security", etc.
        department: str,             # "HR", "Engineering", etc.
        past_violations_count: int = 0
    ) -> Dict[str, Any]:
        """
        Calculates an aggregated risk score (0-100) and risk level (LOW, MEDIUM, HIGH, CRITICAL)
        using a weighted multi-vector matrix.
        """
        
        # 1. Sensitive Data Vector (Weight: 35%)
        # PII and credentials found by regex/NER
        sensitive_mapping = {
            "CRITICAL": 100,
            "HIGH": 80,
            "MEDIUM": 50,
            "LOW": 20,
            "NONE": 0
        }
        sensitive_score = sensitive_mapping.get(sensitive_data_level.upper(), 0)

        # 2. Source Code Vector (Weight: 15%)
        # Gated by language presence and secrets embedded in code
        source_code_score = 0
        if source_code_lang:
            source_code_score = 95 if source_code_has_secrets else 40

        # 3. Document Similarity Vector (Weight: 20%)
        # How closely prompt resembles company confidential policies
        similarity_score_scaled = int(similarity_score * 100)

        # 4. Prompt Category Vector (Weight: 15%)
        # General categories risk ratings
        category_mapping = {
            "Security": 90,
            "Healthcare": 80,
            "Customer Data": 80,
            "Legal": 80,
            "Finance": 50,
            "Internal Document": 60,
            "HR": 40,
            "Programming": 15,
            "General": 5
        }
        category_score = category_mapping.get(prompt_category, 5)

        # 5. Department Policy Vector (Weight: 10%)
        # Cross-checks if department activities conflict with standard operations
        # e.g., HR sharing Code, Finance sharing health data
        policy_score = 0
        dept_lower = department.lower()
        cat_lower = prompt_category.lower()

        if "hr" in dept_lower and cat_lower in ["programming", "security"]:
            policy_score = 80 # HR sharing code/secrets is highly anomalous
        elif "finance" in dept_lower and cat_lower in ["healthcare"]:
            policy_score = 70
        elif "engineering" in dept_lower and cat_lower in ["finance", "hr"]:
            policy_score = 60 # Engineering discussing payroll/revenue targets
        elif "marketing" in dept_lower and cat_lower in ["security", "programming"]:
            policy_score = 80

        # 6. Historical Behavior Vector (Weight: 5%)
        # Check client history counts
        if past_violations_count == 0:
            historical_score = 0
        elif past_violations_count == 1:
            historical_score = 30
        elif past_violations_count == 2:
            historical_score = 65
        else:
            historical_score = 100

        # 7. Aggregate Weighted Average
        weighted_score = (
            (0.35 * sensitive_score) +
            (0.15 * source_code_score) +
            (0.20 * similarity_score_scaled) +
            (0.15 * category_score) +
            (0.10 * policy_score) +
            (0.05 * historical_score)
        )

        final_score = min(100, max(0, int(weighted_score)))

        # 8. Map to Risk Levels
        if final_score >= 90:
            risk_level = "CRITICAL"
        elif final_score >= 70:
            risk_level = "HIGH"
        elif final_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "risk_score": final_score,
            "risk_level": risk_level,
            "vectors": {
                "sensitive_data": sensitive_score,
                "source_code": source_code_score,
                "document_similarity": similarity_score_scaled,
                "prompt_category": category_score,
                "department_policy": policy_score,
                "historical_violations": historical_score
            }
        }
