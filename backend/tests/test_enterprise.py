import unittest
import asyncio
from app.services.groq_service import GroqService
from app.services.ocr_service import OcrService
from app.services.file_service import FileService
from app.services.anomaly_detector import AnomalyDetector
from app.services.shadow_ai_detector import ShadowAiDetector

# Helper to run async methods synchronously in unittest
def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)

class TestEnterpriseServices(unittest.TestCase):
    
    # 1. Test Groq API Service (Mock Mode)
    def test_groq_service_mock(self):
        service = GroqService()
        self.assertEqual(service.default_model, "llama3-8b-8192")
        self.assertEqual(service.max_retries, 3)

    # 2. Test OCR Service (Mock Fallback)
    def test_ocr_service_fallback(self):
        service = OcrService()
        # Mock image bytes
        mock_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        text = service.extract_text(mock_bytes)
        # Should execute self-healing fallback mock scan
        self.assertIn("[OCR FILE SCAN MOCK]", text)
        self.assertIn("admin-leaks@secureprompt.ai", text)

    # 3. Test File Service document scans
    def test_file_service_scan(self):
        service = FileService()
        mock_text_bytes = b"Hello from SecurePrompt AI internal document roadmap file."
        # Run async scan
        res = run_async(service.scan_file(
            file_bytes=mock_text_bytes,
            filename="document.txt",
            department="Engineering"
        ))
        self.assertTrue(res["scanned"])
        self.assertEqual(res["filename"], "document.txt")
        self.assertEqual(res["risk_level"], "LOW")
        self.assertEqual(res["action"], "ALLOW")

    # 4. Test Anomaly Threat Detector (Rule-based boundaries)
    def test_anomaly_detector_rules(self):
        detector = AnomalyDetector()
        
        # Test large prompt anomaly
        large_prompt = "A" * 9000
        res = run_async(detector.analyze_user_activity(
            user_email="test-user@company.com",
            prompt_text=large_prompt,
            sensitive_count=0
        ))
        self.assertTrue(res["is_anomaly"])
        self.assertIn("Unusually large prompt size (potential data dump)", res["reasons"])

        # Test frequent PII anomaly
        res_pii = run_async(detector.analyze_user_activity(
            user_email="test-user@company.com",
            prompt_text="Check these items",
            sensitive_count=6
        ))
        self.assertTrue(res_pii["is_anomaly"])
        self.assertIn("Frequent sensitive data/PII leaks detected in prompt", res_pii["reasons"])

    # 5. Test Shadow AI audit reporting
    def test_shadow_ai_detector_summary(self):
        # Retrieve mock summaries (database is not running in pure unit tests)
        res = run_async(ShadowAiDetector.get_audit_summary())
        self.assertIn("total_requests", res)
        self.assertIn("platforms", res)
        self.assertIn("departments", res)
        self.assertGreater(res["total_requests"], 0)

if __name__ == "__main__":
    unittest.main()
