import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.schemas.pydantic_schemas import PromptScanRequest, PromptScanResponse
from app.ml.scanner import PromptScanner
from app.ml.classifier import ContentClassifier
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import bson

logger = logging.getLogger("secureprompt")

class ScanService:
    @staticmethod
    async def process_and_log_scan(
        db: AsyncIOMotorDatabase, 
        scan_in: PromptScanRequest, 
        username: Optional[str] = None
    ) -> PromptScanResponse:
        """
        Executes heuristic scanner + content classifier, logs the audit entry,
        and triggers a security Alert document if a risk boundary is crossed.
        """
        # 1. Run Scanners
        # Read sensitivity from database settings or default to 50
        sensitivity = 50
        settings_doc = await db.settings.find_one({"key": "global_config"})
        if settings_doc:
            sensitivity = settings_doc.get("sensitivityThreshold", 50)
            
        scan_result = PromptScanner.scan(scan_in.prompt, sensitivity_threshold=sensitivity)
        classification = ContentClassifier.classify(scan_in.prompt)

        # 2. Compile Log Entry
        # Fetch user's department to classify metric shares
        department = "External/Extension User"
        if username:
            user = await db.users.find_one({"username": username})
            if user:
                department = user.get("department", "Engineering")

        log_doc = {
            "timestamp": datetime.fromtimestamp(scan_in.timestamp / 1000.0, tz=timezone.utc),
            "username": username or "anonymous_extension",
            "department": department,
            "website": scan_in.website,
            "siteKey": scan_in.website.split(".")[0] if "." in scan_in.website else scan_in.website,
            "originalPrompt": scan_in.prompt,
            "sanitizedPrompt": scan_result["sanitized_prompt"],
            "riskScore": scan_result["risk_score"],
            "riskLevel": scan_result["risk_level"],
            "action": scan_result["action"],
            "reason": scan_result["reason"],
            "flaggedTerms": scan_result["flagged_terms"],
            "category": classification["category"],
            "complianceStatus": classification["compliance_status"],
            "browserInfo": scan_in.browser_info.model_dump(),
            "session_id": scan_in.session_id
        }

        # Save to prompts_history collection
        await db.prompts_history.insert_one(log_doc)

        # 3. Create Alert if Critical/High Risk Action
        if scan_result["action"] in ["BLOCK", "WARN"] and scan_result["risk_score"] >= 40:
            alert_doc = {
                "timestamp": datetime.now(timezone.utc),
                "prompt_id": log_doc["_id"],
                "username": username or "anonymous_extension",
                "department": department,
                "website": scan_in.website,
                "severity": scan_result["risk_level"],
                "riskScore": scan_result["risk_score"],
                "reason": scan_result["reason"],
                "flaggedTerms": scan_result["flagged_terms"],
                "is_resolved": False
            }
            await db.alerts.insert_one(alert_doc)
            logger.warning(f"Security Alert generated! Risk score: {scan_result['risk_score']} - Reason: {scan_result['reason']}")

        # Record scan to Prometheus
        from app.middleware.prometheus import PrometheusMetrics
        PrometheusMetrics.record_scan(
            action=scan_result["action"],
            risk_level=scan_result["risk_level"],
            model="HeuristicRegex"
        )

        return PromptScanResponse(
            risk_score=scan_result["risk_score"],
            risk_level=scan_result["risk_level"],
            action=scan_result["action"],
            sanitized_prompt=scan_result["sanitized_prompt"],
            reason=scan_result["reason"],
            flagged_terms=scan_result["flagged_terms"]
        )

    @staticmethod
    async def get_history(
        db: AsyncIOMotorDatabase,
        search: Optional[str] = None,
        site: Optional[str] = None,
        risk: Optional[str] = None,
        page: int = 1,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieves paginated audit logs, filtered by query selectors.
        """
        query = {}
        
        # Site filter
        if site and site != "all":
            query["siteKey"] = site
            
        # Risk filter
        if risk and risk != "all":
            if risk == "None":
                query["riskLevel"] = {"$in": ["None", "Unknown"]}
            else:
                query["riskLevel"] = risk

        # Text search (searches prompts or reason)
        if search:
            query["$or"] = [
                {"originalPrompt": {"$regex": search, "$options": "i"}},
                {"reason": {"$regex": search, "$options": "i"}},
                {"username": {"$regex": search, "$options": "i"}}
            ]

        skip = (page - 1) * limit
        cursor = db.prompts_history.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        
        history = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            # Format timestamp back to milliseconds for UI consistency
            doc["timestamp"] = int(doc["timestamp"].replace(tzinfo=timezone.utc).timestamp() * 1000)
            history.append(doc)
            
        return history

    @staticmethod
    async def get_dashboard_stats(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
        """
        Computes dashboard analytics totals, risk counts, and time trends.
        """
        total_scans = await db.prompts_history.count_documents({})
        allowed_count = await db.prompts_history.count_documents({"action": "ALLOW"})
        warned_count = await db.prompts_history.count_documents({"action": "WARN"})
        blocked_count = await db.prompts_history.count_documents({"action": "BLOCK"})

        # Risk distribution aggregation
        risk_dist = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "None": 0}
        pipeline = [{"$group": {"_id": "$riskLevel", "count": {"$sum": 1}}}]
        cursor = db.prompts_history.aggregate(pipeline)
        async for doc in cursor:
            lvl = doc["_id"]
            if lvl in risk_dist:
                risk_dist[lvl] = doc["count"]

        # Timeline trends (last 7 days)
        # Using aggregation to group counts by YYYY-MM-DD date format
        timeline_pipeline = [
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}
                    },
                    "count": {"$sum": 1},
                    "blocked": {"$sum": {"$cond": [{"$eq": ["$action", "BLOCK"]}, 1, 0]}}
                }
            },
            {"$sort": {"_id": 1}},
            {"$limit": 7}
        ]
        
        activity_timeline = []
        cursor = db.prompts_history.aggregate(timeline_pipeline)
        async for doc in cursor:
            activity_timeline.append({
                "date": doc["_id"],
                "total": doc["count"],
                "blocked": doc["blocked"]
            })

        return {
            "total_scans": total_scans,
            "allowed_count": allowed_count,
            "warned_count": warned_count,
            "blocked_count": blocked_count,
            "risk_distribution": risk_dist,
            "activity_timeline": activity_timeline
        }

    @staticmethod
    async def get_granular_statistics(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
        """
        Compiles list of top flagged terms, department compliance distribution,
        and category ratios.
        """
        # 1. Unwind flaggedTerms to find top violators
        terms_pipeline = [
            {"$unwind": "$flaggedTerms"},
            {"$group": {"_id": "$flaggedTerms", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_flagged_terms = []
        cursor = db.prompts_history.aggregate(terms_pipeline)
        async for doc in cursor:
            top_flagged_terms.append({
                "term": doc["_id"],
                "count": doc["count"]
            })

        # 2. Violations grouped by corporate department
        dept_pipeline = [
            {"$match": {"action": {"$in": ["WARN", "BLOCK"]}}},
            {"$group": {"_id": "$department", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        department_violations = []
        cursor = db.prompts_history.aggregate(dept_pipeline)
        async for doc in cursor:
            department_violations.append({
                "department": doc["_id"] or "General Operations",
                "violations_count": doc["count"]
            })

        # 3. Category distribution
        cat_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        
        category_shares = {}
        cursor = db.prompts_history.aggregate(cat_pipeline)
        async for doc in cursor:
            category_shares[doc["_id"] or "Unclassified"] = doc["count"]

        return {
            "top_flagged_terms": top_flagged_terms,
            "department_violations": department_violations,
            "category_shares": category_shares
        }
