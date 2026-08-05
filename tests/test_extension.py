import unittest
import time
from fastapi.testclient import TestClient
from backend.app.main import app

class TestBrowserExtensionAPI(unittest.TestCase):
    def setUp(self):
        # Instantiate test client with lifespan context
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        # Exit lifespan context cleanly
        self.client_ctx.__exit__(None, None, None)

    # 1. Test clean prompt query from extension
    def test_extension_clean_scan(self):
        payload = {
            "prompt": "How do I build a simple webpage with HTML and CSS?",
            "website": "chat.openai.com",
            "timestamp": int(time.time() * 1000),
            "session_id": "test-session-12345",
            "browser_info": {
                "browser": "Chrome",
                "browserVersion": "122.0.0.0",
                "os": "Windows",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
                "language": "en-US",
                "platform": "Win32"
            }
        }
        
        response = self.client.post("/api/scan", json=payload)
        self.assertEqual(response.status_code, 200)
        
        json_data = response.json()
        
        # Verify schema elements expected by popup.js and content.js
        self.assertIn("action", json_data)
        self.assertIn("risk_score", json_data)
        self.assertIn("risk_level", json_data)
        self.assertIn("sanitized_prompt", json_data)
        self.assertIn("reason", json_data)
        self.assertIn("flagged_terms", json_data)
        
        # Clean prompt should be allowed
        self.assertEqual(json_data["action"], "ALLOW")
        self.assertIn(json_data["risk_level"].upper(), ["NONE", "LOW"])
        self.assertLessEqual(json_data["risk_score"], 20)

    # 2. Test toxic/credential prompt query from extension
    def test_extension_blocked_scan(self):
        payload = {
            "prompt": "Connect DB using AWS_KEY='AKIA1234567890ABCDEF'",
            "website": "chat.openai.com",
            "timestamp": int(time.time() * 1000),
            "session_id": "test-session-12345",
            "browser_info": {
                "browser": "Chrome",
                "browserVersion": "122.0.0.0",
                "os": "Windows",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0",
                "language": "en-US",
                "platform": "Win32"
            }
        }
        
        response = self.client.post("/api/scan", json=payload)
        self.assertEqual(response.status_code, 200)
        
        json_data = response.json()
        
        # Credentials leak should be blocked
        self.assertEqual(json_data["action"], "BLOCK")
        self.assertEqual(json_data["risk_level"].upper(), "CRITICAL")
        self.assertGreaterEqual(json_data["risk_score"], 90)
        self.assertIn("[AWS_KEY_1]", json_data["sanitized_prompt"])

    # 3. Test empty/whitespace prompt handling from extension
    def test_extension_empty_scan(self):
        payload = {
            "prompt": "   ",
            "website": "claude.ai",
            "timestamp": int(time.time() * 1000),
            "session_id": "test-session-54321",
            "browser_info": {
                "browser": "Chrome",
                "browserVersion": "122.0.0.0",
                "os": "Windows",
                "userAgent": "Chrome/122.0",
                "language": "en-US",
                "platform": "Win32"
            }
        }
        response = self.client.post("/api/scan", json=payload)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["action"], "ALLOW")
        self.assertLessEqual(json_data["risk_score"], 20)

if __name__ == "__main__":
    unittest.main()
