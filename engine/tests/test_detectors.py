import unittest
import os
import shutil
from engine.validation import DataValidator
from engine.preprocessing import TextPreprocessor
from engine.regex_detector import RegexDetector
from engine.pipeline import DetectionPipeline

# AI Security Engine imports
from engine.source_code_detector import SourceCodeDetector
from engine.document_similarity import DocumentSimilarityEngine
from engine.prompt_classifier import PromptClassifier
from engine.risk_scoring import RiskScoringEngine
from engine.sanitizer import PromptSanitizer
from engine.firewall import PromptFirewall

class TestDataDetectors(unittest.TestCase):
    
    # 1. Test Text Preprocessing
    def test_preprocessor_clean(self):
        raw = "Hello   world!\n\nThis  is NFKC Normalization test: \u2116 1."
        cleaned = TextPreprocessor.clean(raw)
        self.assertNotIn("  ", cleaned)  # check spacing compression
        self.assertIn("No 1.", cleaned)    # NFKC should convert № (\u2116) to No

    # 2. Test Checksum Validators
    def test_luhn_validator(self):
        card_base = "401288888888188"
        for i in range(10):
            test_card = card_base + str(i)
            if DataValidator.luhn_check(test_card):
                self.assertTrue(DataValidator.luhn_check(test_card))
                invalid_card = card_base + str((i + 1) % 10)
                self.assertFalse(DataValidator.luhn_check(invalid_card))
                break

    def test_verhoeff_validator(self):
        base = "36840987654"
        for i in range(10):
            test_uid = base + str(i)
            if DataValidator.verhoeff_check(test_uid):
                self.assertTrue(DataValidator.verhoeff_check(test_uid))
                invalid_uid = base + str((i + 1) % 10)
                self.assertFalse(DataValidator.verhoeff_check(invalid_uid))
                break

    def test_iban_validator(self):
        valid_iban = "DE89370400440532013000"
        self.assertTrue(DataValidator.iban_check(valid_iban))
        invalid_iban = "DE89370400440532013001"
        self.assertFalse(DataValidator.iban_check(invalid_iban))

    # 3. Test Regex Scan Detections
    def test_regex_scanner_detections(self):
        detector = RegexDetector()
        
        email_text = "Contact me at security-audits@secureprompt.ai"
        findings = detector.scan(email_text)
        self.assertGreater(len(findings), 0)
        self.assertEqual(findings[0]["type"], "EMAIL")
        self.assertEqual(findings[0]["value"], "security-audits@secureprompt.ai")

        ip_text = "Server IP is 192.168.1.50"
        findings = detector.scan(ip_text)
        self.assertGreater(len(findings), 0)
        self.assertEqual(findings[0]["type"], "IP_ADDRESS")

        aws_text = "Secret is AKIA1234567890ABCDEF"
        findings = detector.scan(aws_text)
        self.assertGreater(len(findings), 0)
        self.assertEqual(findings[0]["type"], "AWS_KEY")

    # 4. Test Complete Pipeline Orchestration
    def test_pipeline_scan(self):
        pipeline = DetectionPipeline()
        
        result = pipeline.scan("Email: user@domain.com, and valid card info skipped.")
        self.assertTrue(result["detected"])
        self.assertGreater(len(result["entities"]), 0)
        self.assertEqual(result["entities"][0]["type"], "EMAIL")

        result_clean = pipeline.scan("Write a function to return the length of a string.")
        self.assertFalse(result_clean["detected"])
        self.assertEqual(len(result_clean["entities"]), 0)

    # ==================================================
    # NEW TESTS: AI Security Engine Expansion (Modules 1-6)
    # ==================================================

    # 5. Test Source Code Leakage Detection (Module 1)
    def test_source_code_leakage_detector(self):
        detector = SourceCodeDetector()
        
        # Test Python detection
        py_code = """
        def compute_sum(a, b):
            return a + b
        """
        res = detector.scan(py_code)
        self.assertTrue(res["detected"])
        self.assertEqual(res["language"], "Python")
        self.assertEqual(res["severity"], "HIGH")
        self.assertFalse(res["has_secrets"])

        # Test database credentials inside Python code
        py_leak = """
        def connect_db():
            db_pass = "root_access_token_123!"
            return db_pass
        """
        res_leak = detector.scan(py_leak)
        self.assertTrue(res_leak["detected"])
        self.assertEqual(res_leak["language"], "Python")
        self.assertTrue(res_leak["has_secrets"])
        self.assertEqual(res_leak["severity"], "CRITICAL")

    # 6. Test Document Similarity Engine (Module 2)
    def test_document_similarity_engine(self):
        # Create temp file in current path
        temp_file = "test_doc_leak.txt"
        secret_content = "SecurePrompt AI internal company strategic roadmap details for product launch."
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(secret_content)

        engine = DocumentSimilarityEngine()
        
        try:
            # Index document
            indexed = engine.add_document(temp_file, doc_id="temp_doc_roadmap")
            self.assertTrue(indexed)
            
            # Query similar prompt
            res = engine.query_similarity("Strategic roadmap product launch timeline.")
            self.assertEqual(res["matched_doc"], temp_file)
            self.assertGreater(res["score"], 0.40)
            self.assertGreater(res["confidence"], 40)
        finally:
            # Cleanup temp document files
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(engine.fallback_db_path):
                os.remove(engine.fallback_db_path)

    # 7. Test Prompt Risk Classification (Module 3)
    def test_prompt_risk_classification(self):
        classifier = PromptClassifier()
        
        # Test Finance classification
        finance_prompt = "Our EBITDA and revenue growth projections are fiscal target milestones."
        res = classifier.predict(finance_prompt)
        self.assertEqual(res["category"], "Finance")
        self.assertEqual(res["risk_level"], "MEDIUM")

        # Test Programming classification
        prog_prompt = "How to declare an array variables in Go language?"
        res_prog = classifier.predict(prog_prompt)
        self.assertEqual(res_prog["category"], "Programming")
        self.assertEqual(res_prog["risk_level"], "LOW")

    # 8. Test Risk Scoring Engine (Module 4)
    def test_risk_scoring_engine(self):
        # Test Low risk mapping
        low_res = RiskScoringEngine.calculate_score(
            sensitive_data_level="NONE",
            source_code_lang=None,
            source_code_has_secrets=False,
            similarity_score=0.1,
            prompt_category="General",
            department="Operations"
        )
        self.assertEqual(low_res["risk_level"], "LOW")
        self.assertLess(low_res["risk_score"], 40)

        # Test Critical risk mapping
        critical_res = RiskScoringEngine.calculate_score(
            sensitive_data_level="CRITICAL",
            source_code_lang="Python",
            source_code_has_secrets=True,
            similarity_score=0.85,
            prompt_category="Security",
            department="Marketing",         # triggers policy vector anomaly
            past_violations_count=3          # triggers historical violations vector
        )
        self.assertEqual(critical_res["risk_level"], "CRITICAL")
        self.assertGreaterEqual(critical_res["risk_score"], 90)

    # 9. Test Prompt Sanitizer (Module 5)
    def test_prompt_sanitizer(self):
        raw_text = "Users: john@gmail.com and dave@gmail.com are registered."
        entities = [
            {"type": "EMAIL", "value": "john@gmail.com", "start": 7, "end": 21, "confidence": 99, "severity": "HIGH"},
            {"type": "EMAIL", "value": "dave@gmail.com", "start": 26, "end": 40, "confidence": 99, "severity": "HIGH"}
        ]
        
        sanitized, restore_map = PromptSanitizer.sanitize(raw_text, entities)
        self.assertIn("[EMAIL_1]", sanitized)
        self.assertIn("[EMAIL_2]", sanitized)
        self.assertNotIn("john@gmail.com", sanitized)
        
        # Verify de-anonymization restoration
        restored = PromptSanitizer.restore(sanitized, restore_map)
        self.assertEqual(restored, raw_text)

    # 10. Test Prompt Firewall (Module 6)
    def test_prompt_firewall(self):
        firewall = PromptFirewall()
        
        # 1. ALLOW action
        res_allow = firewall.scan_and_decide("How do I cook pasta at home?")
        self.assertEqual(res_allow["action"], "ALLOW")
        self.assertEqual(res_allow["risk_level"], "LOW")

        # 2. SANITIZE action
        res_sanitize = firewall.scan_and_decide(
            "Send confirmation details to test@gmail.com email.",
            auto_sanitize_pii=True
        )
        self.assertEqual(res_sanitize["action"], "SANITIZE")
        self.assertIn("[EMAIL_1]", res_sanitize["sanitized_prompt"])

        # 3. BLOCK action
        res_block = firewall.scan_and_decide("Connect DB using AWS_KEY='AKIA1234567890ABCDEF'")
        self.assertEqual(res_block["action"], "BLOCK")
        self.assertEqual(res_block["risk_level"], "CRITICAL")

if __name__ == "__main__":
    unittest.main()
