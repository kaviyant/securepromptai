import logging
from typing import Dict, Any, Optional
from engine.pipeline import DetectionPipeline
from engine.source_code_detector import SourceCodeDetector
from engine.document_similarity import DocumentSimilarityEngine
from engine.prompt_classifier import PromptClassifier
from engine.risk_scoring import RiskScoringEngine
from engine.sanitizer import PromptSanitizer

logger = logging.getLogger("secureprompt")

_firewall_instance: Optional["PromptFirewall"] = None

def get_firewall_instance(model_dir: str = "model", db_dir: str = "model/chromadb") -> "PromptFirewall":
    global _firewall_instance
    if _firewall_instance is None:
        _firewall_instance = PromptFirewall(model_dir=model_dir, db_dir=db_dir)
    return _firewall_instance

class PromptFirewall:
    def __init__(self, model_dir: str = "model", db_dir: str = "model/chromadb"):
        self.pipeline = DetectionPipeline(model_dir=model_dir)
        self.code_detector = SourceCodeDetector()
        self.similarity_engine = DocumentSimilarityEngine(db_dir=db_dir)
        self.classifier = PromptClassifier(model_dir=model_dir)

    def scan_and_decide(
        self, 
        prompt_text: str, 
        department: str = "General Operations",
        past_violations_count: int = 0,
        auto_sanitize_pii: bool = False
    ) -> Dict[str, Any]:
        """
        Runs the complete security scanning pipeline across 6 modules.
        Calculates risk scoring vectors and outputs the firewall action decision (ALLOW, WARN, SANITIZE, BLOCK).
        """
        clean_prompt = prompt_text.strip()
        
        # Scan pipeline entities (contains raw spans)
        regex_finds = self.pipeline.regex_detector.scan(clean_prompt)
        ner_finds = self.pipeline.ner_detector.scan(clean_prompt)
        combined_finds = regex_finds + ner_finds
        resolved_entities = self.pipeline._resolve_overlaps(combined_finds)

        # 2. Source Code Leakage Detection (Module 1)
        code_result = self.code_detector.scan(clean_prompt)

        # 3. Document Similarity Engine Checks (Module 2)
        similarity_result = self.similarity_engine.query_similarity(clean_prompt)

        # 4. Prompt Category Classification (Module 3)
        class_result = self.classifier.predict(clean_prompt)

        # 5. Compile Sensitive Data level
        sensitive_level = "NONE"
        if len(resolved_entities) > 0:
            # Get highest severity from findings
            severities = [e["severity"] for e in resolved_entities]
            if "CRITICAL" in severities:
                sensitive_level = "CRITICAL"
            elif "HIGH" in severities:
                sensitive_level = "HIGH"
            elif "MEDIUM" in severities:
                sensitive_level = "MEDIUM"
            else:
                sensitive_level = "LOW"

        # 6. Calculate Risk Score Matrix (Module 4)
        score_result = RiskScoringEngine.calculate_score(
            sensitive_data_level=sensitive_level,
            source_code_lang=code_result["language"],
            source_code_has_secrets=code_result["has_secrets"],
            similarity_score=similarity_result["score"],
            prompt_category=class_result["category"],
            department=department,
            past_violations_count=past_violations_count
        )

        # 7. Prompt Sanitization (Module 5)
        sanitized_prompt, restore_map = PromptSanitizer.sanitize(clean_prompt, resolved_entities)

        # 8. Firewall Decisions Engine (Module 6)
        risk_score = score_result["risk_score"]
        risk_level = score_result["risk_level"]
        
        # Security Override: Escalate direct credential or token leaks to CRITICAL,
        # and high document similarity matches to HIGH
        if sensitive_level == "CRITICAL" or code_result["has_secrets"]:
            risk_level = "CRITICAL"
            risk_score = max(risk_score, 90)
        elif similarity_result["score"] > 0.6:
            risk_level = "HIGH"
            risk_score = max(risk_score, 75)
        elif sensitive_level in ["HIGH", "MEDIUM"]:
            risk_level = "MEDIUM"
            risk_score = max(risk_score, 50)
        
        action = "ALLOW"
        explanation = "Approved: Prompt is compliant and contains no sensitive data."

        if risk_level == "CRITICAL" or risk_level == "HIGH":
            action = "BLOCK"
            explanation = f"Blocked: Critical risk level ({risk_level}) identified. Risk Score: {risk_score}/100. Reason: "
            reasons = []
            if sensitive_level in ["CRITICAL", "HIGH"]:
                reasons.append("credentials/PII leakage detected")
            if code_result["has_secrets"]:
                reasons.append("credentials inside source code")
            if similarity_result["score"] > 0.6:
                reasons.append(f"high similarity with company document ({similarity_result['matched_doc']})")
            if not reasons:
                reasons.append(f"Prompt content matches forbidden category ({class_result['category']})")
            explanation += ", ".join(reasons) + "."
            
        elif risk_level == "MEDIUM":
            # If user settings specify auto sanitization, we can sanitize and allow it!
            # Otherwise, warn the user.
            if auto_sanitize_pii and len(resolved_entities) > 0:
                action = "SANITIZE"
                explanation = "Sanitized: Prompt contains PII. Sensitive elements have been redacted before sending."
            else:
                action = "WARN"
                explanation = f"Warning: Medium risk prompts identified. Risk Score: {risk_score}/100. Category: {class_result['category']}."
                
        elif risk_level == "LOW" and len(resolved_entities) > 0:
            if auto_sanitize_pii:
                action = "SANITIZE"
                explanation = "Sanitized: PII elements replaced with placeholders."
            else:
                action = "ALLOW"
                explanation = "Approved: Contains low risk PII, allowed to submit."

        return {
            "action": action,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "explanation": explanation,
            "sanitized_prompt": sanitized_prompt,
            "category": class_result["category"],
            "source_code": {
                "detected": code_result["detected"],
                "language": code_result["language"],
                "confidence": code_result["confidence"]
            },
            "similarity": {
                "matched_doc": similarity_result["matched_doc"],
                "score": similarity_result["score"]
            },
            "restore_map": restore_map
        }
