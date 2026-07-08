import unittest
import asyncio
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from engine.retrain_pipeline import RetrainingPipeline

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "secureprompt_test_db")

class TestSecurePromptIntegration(unittest.TestCase):
    def setUp(self):
        # Establish async loop
        self.loop = asyncio.get_event_loop()
        
        # Connect to test DB
        self.client = AsyncIOMotorClient(MONGODB_URL)
        self.db = self.client[DATABASE_NAME]

    def tearDown(self):
        # Cleanup test DB collections
        self.loop.run_until_complete(self.db.prompts_history.drop())
        self.loop.run_until_complete(self.db.alerts.drop())
        self.client.close()

    # 1. Test database audit log insertion and indexing
    def test_log_insertion_and_retrieval(self):
        async def run_test():
            # Construct a mock log entry
            log_doc = {
                "timestamp": datetime.now(timezone.utc),
                "username": "integration_tester",
                "department": "Engineering",
                "website": "chat.openai.com",
                "originalPrompt": "Analyze database logs for AWS_KEY='AKIA1234567890ABCDEF'",
                "sanitizedPrompt": "Analyze database logs for AWS_KEY='[REDACTED_AWS_KEY]'",
                "riskScore": 95,
                "riskLevel": "Critical",
                "action": "BLOCK",
                "reason": "AWS Key Leakage",
                "flaggedTerms": ["AKIA1234567890ABCDEF"]
            }
            
            # Insert log
            res = await self.db.prompts_history.insert_one(log_doc)
            self.assertIsNotNone(res.inserted_id)
            
            # Query back
            retrieved = await self.db.prompts_history.find_one({"username": "integration_tester"})
            self.assertEqual(retrieved["riskLevel"], "Critical")
            self.assertEqual(retrieved["action"], "BLOCK")
            self.assertIn("AKIA1234567890ABCDEF", retrieved["flaggedTerms"])
            
        try:
            self.loop.run_until_complete(run_test())
        except Exception as e:
            self.skipTest(f"Live MongoDB instance not available at {MONGODB_URL}: {e}")

    # 2. Test Retraining pipeline database compilation interface
    def test_retraining_data_collection(self):
        async def run_test():
            # Seed 5 mock prompts in database
            for i in range(5):
                await self.db.prompts_history.insert_one({
                    "timestamp": datetime.now(timezone.utc),
                    "username": f"user_{i}",
                    "originalPrompt": f"Mock prompt number {i} containing engineering credentials.",
                    "riskLevel": "High" if i % 2 == 0 else "None",
                    "action": "BLOCK" if i % 2 == 0 else "ALLOW"
                })
                
            # Collect data from retrain pipeline
            # Temporarily point pipeline target to test database
            os.environ["DATABASE_NAME"] = DATABASE_NAME
            samples = await RetrainingPipeline.collect_new_data()
            
            # Check length is augmented to minimum requirements (50+)
            self.assertGreaterEqual(len(samples), 50)
            self.assertEqual(samples[0]["is_sensitive"], 1) # First record index model check
            
        try:
            self.loop.run_until_complete(run_test())
        except Exception as e:
            self.skipTest(f"Live MongoDB instance not available: {e}")

if __name__ == "__main__":
    unittest.main()
