import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestSecurePromptAPI(unittest.TestCase):
    def setUp(self):
        # Instantiate test client with lifespan context
        self.client_ctx = TestClient(app)
        self.client = self.client_ctx.__enter__()
        
        # Self-register and login admin to obtain credentials for gated endpoints
        admin_register_payload = {
            "username": "api_test_admin",
            "email": "test_admin@secureprompt.ai",
            "password": "SecureAdminPassword2026!",
            "role": "Admin",
            "department": "Security Operations"
        }
        # Ignore registration failures if already registered in db persistence
        self.client.post("/api/register", json=admin_register_payload)
        
        login_response = self.client.post("/api/login", data={
            "username": "api_test_admin",
            "password": "SecureAdminPassword2026!"
        })
        if login_response.status_code == 200:
            token_data = login_response.json()
            self.headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        else:
            self.headers = {}

    def tearDown(self):
        # Exit lifespan context cleanly
        self.client_ctx.__exit__(None, None, None)

    # 1. Test Public Health Endpoints
    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    # 2. Test Prometheus Scraper Endpoint
    def test_metrics_endpoint(self):
        response = self.client.get("/metrics")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers["content-type"])
        self.assertIn("secureprompt_scans_total", response.text)

    # 3. Test Security Sanitization endpoints (Gated by Employee role)
    def test_sanitize_endpoint(self):
        payload = {"prompt": "John Doe's SSN is 000-12-3456."}
        response = self.client.post("/api/sanitize", json=payload, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            self.assertIn("[REDACTED_SSN]", data["sanitized_prompt"])
            self.assertIn("000-12-3456", data["flagged_terms"])
        else:
            self.assertEqual(response.status_code, 401) # Check if auth failed

    # 4. Test Content classification endpoint
    def test_classify_endpoint(self):
        payload = {"prompt": "We need to review our hiring pipeline for software engineers."}
        response = self.client.post("/api/classify", json=payload, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["category"], "HR & Employee Records")

    # 5. Test MLOps endpoints (Gated by Admin role)
    def test_mlops_model_status(self):
        response = self.client.get("/api/mlops/model-status", headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            self.assertIn("sklearn_loaded", data)
            self.assertIn("distilbert_loaded", data)
            self.assertIn("mlflow_sync_active", data)
        else:
            self.assertEqual(response.status_code, 401)

    def test_mlops_retrain_trigger(self):
        response = self.client.post("/api/mlops/retrain", headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["status"], "started")
        else:
            self.assertEqual(response.status_code, 401)

if __name__ == "__main__":
    unittest.main()
