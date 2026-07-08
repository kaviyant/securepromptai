import numpy as np
import logging
from typing import Dict, Any, List, Tuple
from scipy.stats import ks_2samp

logger = logging.getLogger("secureprompt_drift")

class DriftDetector:
    @staticmethod
    def calculate_psi(baseline: np.ndarray, target: np.ndarray, num_buckets: int = 10) -> float:
        """
        Calculates the Population Stability Index (PSI) between a baseline distribution
        and a target distribution.
        
        PSI values:
        - PSI < 0.1: No significant distribution change (stable).
        - 0.1 <= PSI < 0.25: Moderate distribution shift.
        - PSI >= 0.25: Significant distribution drift.
        """
        if len(baseline) == 0 or len(target) == 0:
            return 0.0

        # Create quantile-based buckets from baseline to handle non-uniform distributions
        percentiles = np.linspace(0, 100, num_buckets + 1)
        buckets = np.percentile(baseline, percentiles)
        
        # Extend boundaries to infinity to capture all values (standard continuous binning)
        buckets[0] = -np.inf
        buckets[-1] = np.inf

        # Calculate frequency counts in each bucket
        baseline_counts, _ = np.histogram(baseline, bins=buckets)
        target_counts, _ = np.histogram(target, bins=buckets)

        # Convert counts to fractions (probabilities) and add epsilon smoothing to prevent divide-by-zero
        epsilon = 1e-4
        baseline_probs = (baseline_counts / len(baseline)) + epsilon
        target_probs = (target_counts / len(target)) + epsilon

        # Re-normalize to ensure sums are 1.0 after smoothing
        baseline_probs /= np.sum(baseline_probs)
        target_probs /= np.sum(target_probs)

        # Compute PSI index formula: sum( (Actual - Expected) * ln(Actual / Expected) )
        psi = np.sum((target_probs - baseline_probs) * np.log(target_probs / baseline_probs))
        return float(psi)

    @staticmethod
    def detect_data_drift(
        baseline_lengths: List[int],
        target_lengths: List[int],
        psi_threshold: float = 0.25
    ) -> Dict[str, Any]:
        """
        Runs PSI and Kolmogorov-Smirnov tests on prompt lengths to identify structural input data drift.
        """
        if len(baseline_lengths) < 30 or len(target_lengths) < 30:
            logger.warning("Insufficient sample sizes to calculate statistical drift. Minimum size: 30.")
            return {
                "drift_detected": False,
                "psi": 0.0,
                "ks_p_value": 1.0,
                "message": "Insufficient data samples to evaluate drift."
            }

        base_arr = np.array(baseline_lengths)
        target_arr = np.array(target_lengths)

        # 1. Calculate PSI
        psi_score = DriftDetector.calculate_psi(base_arr, target_arr)

        # 2. Calculate KS-Test (continuous Kolmogorov-Smirnov test)
        ks_stat, p_value = ks_2samp(base_arr, target_arr)

        # Drift conditions: PSI >= threshold OR highly significant KS difference (p < 0.01)
        is_drifted = (psi_score >= psi_threshold) or (p_value < 0.01)

        result = {
            "drift_detected": is_drifted,
            "psi": round(psi_score, 4),
            "ks_statistic": round(ks_stat, 4),
            "ks_p_value": round(p_value, 6),
            "message": (
                "Data drift detected! Input prompt distributions have shifted significantly." 
                if is_drifted else "No significant data drift detected."
            )
        }
        logger.info(f"Data Drift Check Results -> PSI: {result['psi']} | KS p-val: {result['ks_p_value']} | Drifted: {is_drifted}")
        return result

    @staticmethod
    def detect_concept_drift(
        historical_accuracy: List[float],
        current_accuracy: float,
        degradation_threshold: float = 0.10
    ) -> Dict[str, Any]:
        """
        Detects concept drift by monitoring performance (accuracy) degradation over time.
        If current accuracy is degradation_threshold lower than historical baseline average, triggers alert.
        """
        if not historical_accuracy:
            return {"drift_detected": False, "accuracy_drop": 0.0, "message": "No baseline accuracy records available."}

        avg_baseline = np.mean(historical_accuracy)
        acc_drop = avg_baseline - current_accuracy

        is_drifted = acc_drop >= degradation_threshold

        result = {
            "drift_detected": is_drifted,
            "baseline_accuracy": round(avg_baseline, 4),
            "current_accuracy": round(current_accuracy, 4),
            "accuracy_drop": round(max(0.0, acc_drop), 4),
            "message": (
                f"Concept drift detected! Model accuracy dropped by {acc_drop*100:.2f}%."
                if is_drifted else "Model accuracy remains within compliant threshold."
            )
        }
        logger.info(f"Concept Drift Check Results -> Baseline: {result['baseline_accuracy']} | Current: {result['current_accuracy']} | Drifted: {is_drifted}")
        return result
