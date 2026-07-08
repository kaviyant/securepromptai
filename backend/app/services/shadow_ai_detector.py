import logging
import datetime
from typing import Dict, Any, List
from app.database.connection import get_database

logger = logging.getLogger("secureprompt")

class ShadowAiDetector:
    @staticmethod
    async def log_usage(
        user_email: str,
        department: str,
        site_key: str, # "chatgpt", "gemini", "claude", "copilot", "grok", "perplexity", "deepseek", "openrouter"
        prompt_text: str,
        blocked: bool = False
    ) -> bool:
        """
        Logs prompt request metadata for corporate Shadow AI auditing.
        """
        db = get_database()
        if db is None:
            return False

        try:
            log_doc = {
                "user_email": user_email,
                "department": department,
                "site_key": site_key.lower(),
                "prompt_length": len(prompt_text),
                "timestamp": datetime.datetime.utcnow(),
                "blocked": blocked
            }
            # Save into prompts collection (which acts as main ledger)
            await db.prompts.insert_one(log_doc)
            return True
        except Exception as e:
            logger.error(f"Failed to log Shadow AI audit metric: {e}")
            return False

    @staticmethod
    async def get_audit_summary() -> Dict[str, Any]:
        """
        Compiles aggregates from MongoDB prompts collection:
        1. Access distribution per website platform.
        2. Submission volumes by department.
        3. Block rates and total requests.
        """
        db = get_database()
        if db is None:
            # Mock details if running offline
            return {
                "total_requests": 250,
                "block_rate": 12.4,
                "platforms": {"chatgpt": 120, "gemini": 50, "claude": 40, "copilot": 25, "grok": 15},
                "departments": {"Engineering": 130, "Finance": 40, "HR": 30, "Legal": 10, "Marketing": 40}
            }

        try:
            total_requests = await db.prompts.count_documents({})
            total_blocked = await db.prompts.count_documents({"blocked": True})
            block_rate = round((total_blocked / max(1, total_requests)) * 100, 2)

            # Aggregate by Platform
            platform_pipeline = [
                {"$group": {"_id": "$site_key", "count": {"$sum": 1}}}
            ]
            platform_results = await db.prompts.aggregate(platform_pipeline).to_list(length=100)
            platforms = {r["_id"]: r["count"] for r in platform_results if r["_id"] is not None}

            # Aggregate by Department
            dept_pipeline = [
                {"$group": {"_id": "$department", "count": {"$sum": 1}}}
            ]
            dept_results = await db.prompts.aggregate(dept_pipeline).to_list(length=100)
            departments = {r["_id"]: r["count"] for r in dept_results if r["_id"] is not None}

            return {
                "total_requests": total_requests,
                "block_rate": block_rate,
                "platforms": platforms,
                "departments": departments
            }
        except Exception as e:
            logger.error(f"Failed to generate Shadow AI audit: {e}")
            return {}
