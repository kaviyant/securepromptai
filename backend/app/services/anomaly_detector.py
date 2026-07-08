import logging
import datetime
from typing import Dict, Any, List
from app.database.connection import get_database

logger = logging.getLogger("secureprompt")

try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class AnomalyDetector:
    def __init__(self):
        self.contamination = 0.05 # 5% contamination target

    async def analyze_user_activity(
        self, 
        user_email: str,
        prompt_text: str,
        sensitive_count: int
    ) -> Dict[str, Any]:
        """
        Evaluates a prompt submission for potential insider threat anomalies.
        Uses IsolationForest if scikit-learn is available and history is > 15 logs.
        Otherwise executes a threshold-based rule engine.
        """
        db = get_database()
        now = datetime.datetime.utcnow()
        current_hour = now.hour
        prompt_len = len(prompt_text)

        # 1. Calculate prompt submission frequency (rolling 5 minutes)
        five_mins_ago = now - datetime.timedelta(minutes=5)
        rolling_count = 0
        
        if db is not None:
            try:
                rolling_count = await db.prompts.count_documents({
                    "user_email": user_email,
                    "timestamp": {"$gte": five_mins_ago}
                })
            except Exception as e:
                logger.error(f"Failed to query rolling count in anomaly check: {e}")

        # Features: [prompt_length, sensitive_count, submission_hour, rolling_frequency]
        features = [prompt_len, sensitive_count, current_hour, rolling_count]
        
        is_anomaly = False
        anomaly_score = 0.0
        reasons = []

        # 2. Scikit-learn Isolation Forest ML Check
        if SKLEARN_AVAILABLE and db is not None:
            try:
                # Retrieve past user prompts for training (up to 100 entries)
                cursor = db.prompts.find(
                    {"user_email": user_email},
                    {"prompt_text": 1, "sensitive_count": 1, "timestamp": 1}
                ).sort("timestamp", -1).limit(100)
                
                history = await cursor.to_list(length=100)
                
                if len(history) >= 15:
                    # Construct feature matrix from history
                    X_train = []
                    for h in history:
                        h_time = h.get("timestamp", now)
                        h_text = h.get("prompt_text", "")
                        h_sens = h.get("sensitive_count", 0)
                        
                        # Fetch count for each past log's 5-min window
                        h_five_ago = h_time - datetime.timedelta(minutes=5)
                        h_freq = await db.prompts.count_documents({
                            "user_email": user_email,
                            "timestamp": {"$gte": h_five_ago, "$lte": h_time}
                        })
                        
                        X_train.append([len(h_text), h_sens, h_time.hour, h_freq])

                    X_train = np.array(X_train)
                    
                    # Fit Isolation Forest
                    clf = IsolationForest(contamination=self.contamination, random_state=42)
                    clf.fit(X_train)
                    
                    # Predict current item (-1 = Anomaly, 1 = Normal)
                    pred = clf.predict([features])[0]
                    # Score (lower is more anomalous)
                    score = float(clf.decision_function([features])[0])
                    
                    if pred == -1:
                        is_anomaly = True
                        anomaly_score = round(abs(score) * 100, 2)
                        
            except Exception as e:
                logger.error(f"Isolation Forest anomaly check failed: {e}. Falling back to Rule-Engine.")

        # 3. Rule-Engine Fallback checks
        # Standard safety bounds
        if prompt_len > 8000:
            is_anomaly = True
            reasons.append("Unusually large prompt size (potential data dump)")
            
        if current_hour < 6 or current_hour > 22:
            # Submissions between 10PM and 6AM local
            is_anomaly = True
            reasons.append("Suspicious out-of-hours night activity")
            
        if sensitive_count > 4:
            is_anomaly = True
            reasons.append("Frequent sensitive data/PII leaks detected in prompt")
            
        if rolling_count > 10:
            is_anomaly = True
            reasons.append("High submission frequency spike (unusual rate limit stress)")

        # Map details for rule-engine score
        if is_anomaly and anomaly_score == 0.0:
            anomaly_score = float(len(reasons) * 25)

        # 4. Generate Alert in Database if anomalous
        if is_anomaly and db is not None:
            try:
                alert_doc = {
                    "user_email": user_email,
                    "timestamp": now,
                    "alert_type": "Insider Threat Anomaly",
                    "severity": "HIGH" if anomaly_score >= 50 else "MEDIUM",
                    "reasons": reasons if reasons else ["Anomalous submission density flagged by Isolation Forest ML model."],
                    "score": anomaly_score,
                    "features": {
                        "prompt_length": prompt_len,
                        "sensitive_count": sensitive_count,
                        "submission_hour": current_hour,
                        "rolling_frequency": rolling_count
                    },
                    "resolved": False
                }
                await db.alerts.insert_one(alert_doc)
                logger.info(f"Insider Threat alert generated for {user_email}.")
            except Exception as e:
                logger.error(f"Failed to record threat alert: {e}")

        return {
            "is_anomaly": is_anomaly,
            "score": anomaly_score,
            "reasons": reasons
        }
