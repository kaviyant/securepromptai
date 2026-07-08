import unittest
import numpy as np
from engine.drift_detector import DriftDetector
from engine.risk_scoring import RiskScoringEngine
from backend.app.ml.scanner import PromptScanner, luhn_checksum
from backend.app.ml.classifier import ContentClassifier

class TestSecurePromptUnit(unittest.TestCase):
    # 1. Test Luhn Checksum Algorithm
    def test_luhn_checksum(self):
        # Valid 16-digit test card number
        self.assertTrue(luhn_checksum("4111111111111111"))
        # Invalid 16-digit card number
        self.assertFalse(luhn_checksum("4111111111111112"))

    # 2. Test Heuristics PII / Secrets Scanner
    def test_prompt_scanner_pii(self):
        prompt = "My email is test@secureprompt.ai and phone is +1-202-555-0143."
        res = PromptScanner.scan(prompt)
        
        # Scans have two medium PII violations, risk score 80 -> risk level is High
        self.assertEqual(res["risk_level"], "High")
        self.assertIn("[REDACTED_EMAIL]", res["sanitized_prompt"])
        self.assertIn("[REDACTED_PHONE_NUMBER]", res["sanitized_prompt"])
        self.assertIn("Email Address", res["reason"])
        self.assertIn("Phone Number", res["reason"])

    def test_prompt_scanner_secrets(self):
        prompt = "AWS credentials: AWS_KEY='AKIA1234567890ABCDEF'"
        res = PromptScanner.scan(prompt)
        
        self.assertEqual(res["action"], "BLOCK")
        self.assertEqual(res["risk_level"], "Critical")
        self.assertIn("[REDACTED_AWS_KEY]", res["sanitized_prompt"])

    # 3. Test Text Content Category Classifier
    def test_content_classifier(self):
        prompt_finance = "We need to analyze Q4 EBITDA margins and forecast balance sheet profiles."
        res_fin = ContentClassifier.classify(prompt_finance)
        self.assertEqual(res_fin["category"], "Finance & Accounting")
        self.assertEqual(res_fin["compliance_status"], "Warning")

        prompt_code = "def parse_token(auth_header): return auth_header.split(' ')[1]"
        res_code = ContentClassifier.classify(prompt_code)
        self.assertEqual(res_code["category"], "Source Code & Engineering")

    # 4. Test Risk Scoring Engine Logic
    def test_risk_scoring_matrix(self):
        # Using parameters that aggregate to critical risk levels
        score_res = RiskScoringEngine.calculate_score(
            sensitive_data_level="CRITICAL",
            source_code_lang="python",
            source_code_has_secrets=True,
            similarity_score=0.95,
            prompt_category="Security",
            department="Marketing",
            past_violations_count=3
        )
        self.assertEqual(score_res["risk_level"], "CRITICAL")
        self.assertGreaterEqual(score_res["risk_score"], 90)

    # 5. Test Model Input Data Drift calculations
    def test_drift_calculation(self):
        # Baseline lengths (representing a standard training set)
        baseline = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60] * 10
        # Target lengths matching baseline (no drift)
        target_stable = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60] * 10
        # Target lengths showing huge shift (drifted)
        target_drifted = [150, 200, 250, 300, 350, 400, 450, 500] * 15

        # Stable check
        res_stable = DriftDetector.detect_data_drift(baseline, target_stable)
        self.assertFalse(res_stable["drift_detected"])
        self.assertLess(res_stable["psi"], 0.1)

        # Drifted check
        res_drift = DriftDetector.detect_data_drift(baseline, target_drifted)
        self.assertTrue(res_drift["drift_detected"])
        self.assertGreaterEqual(res_drift["psi"], 0.25)

if __name__ == "__main__":
    unittest.main()
