import time
from engine.dataset_generator import DatasetGenerator
from engine.regex_detector import RegexDetector
from engine.ml_detector import MLDetector
from typing import List, Dict, Any

def calculate_metrics(y_true: List[int], y_pred: List[int]) -> Dict[str, float]:
    """
    Computes precision, recall, and F1-score.
    """
    tp = sum(1 for gt, pd in zip(y_true, y_pred) if gt == 1 and pd == 1)
    fp = sum(1 for gt, pd in zip(y_true, y_pred) if gt == 0 and pd == 1)
    fn = sum(1 for gt, pd in zip(y_true, y_pred) if gt == 1 and pd == 0)
    tn = sum(1 for gt, pd in zip(y_true, y_pred) if gt == 0 and pd == 0)

    precision = tp / max(1, (tp + fp))
    recall = tp / max(1, (tp + fn))
    f1 = 2 * (precision * recall) / max(1e-9, (precision + recall))
    accuracy = (tp + tn) / max(1, len(y_true))

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1
    }

def run_benchmark(dataset_size: int = 200):
    print("==================================================")
    print(f"Starting Benchmark Evaluation (Dataset Size: {dataset_size})")
    print("==================================================")
    
    # 1. Generate Test Set
    dataset = DatasetGenerator.generate_list(size=dataset_size)
    texts = [d["text"] for d in dataset]
    y_true = [d["is_sensitive"] for d in dataset]

    # 2. Instantiate Engines
    regex_detector = RegexDetector()
    ml_detector = MLDetector()

    # 3. Benchmark Heuristic Regex Engine
    start_time = time.time()
    y_pred_regex = []
    for text in texts:
        findings = regex_detector.scan(text)
        y_pred_regex.append(1 if len(findings) > 0 else 0)
    regex_duration = time.time() - start_time
    regex_throughput = len(texts) / regex_duration
    regex_metrics = calculate_metrics(y_true, y_pred_regex)

    # 4. Benchmark ML Scikit-learn Classifier
    start_time = time.time()
    y_pred_ml = []
    for text in texts:
        pred = ml_detector.predict(text)
        y_pred_ml.append(1 if pred["is_sensitive"] else 0)
    ml_duration = time.time() - start_time
    ml_throughput = len(texts) / ml_duration
    ml_metrics = calculate_metrics(y_true, y_pred_ml)

    # 5. Output comparison table
    print("\nBenchmark Results Summary:")
    print("--------------------------------------------------")
    print(f"{'Metric':<15} | {'Regex Heuristics':<18} | {'Scikit-learn ML':<15}")
    print("--------------------------------------------------")
    print(f"{'Throughput':<15} | {f'{regex_throughput:.2f} p/sec':<18} | {f'{ml_throughput:.2f} p/sec':<15}")
    print(f"{'Accuracy':<15} | {f'{regex_metrics['accuracy']*100:.2f}%':<18} | {f'{ml_metrics['accuracy']*100:.2f}%':<15}")
    print(f"{'Precision':<15} | {f'{regex_metrics['precision']*100:.2f}%':<18} | {f'{ml_metrics['precision']*100:.2f}%':<15}")
    print(f"{'Recall':<15} | {f'{regex_metrics['recall']*100:.2f}%':<18} | {f'{ml_metrics['recall']*100:.2f}%':<15}")
    print(f"{'F1-Score':<15} | {f'{regex_metrics['f1']*100:.2f}%':<18} | {f'{ml_metrics['f1']*100:.2f}%':<15}")
    print("--------------------------------------------------")
    print("Note: Regex runs with high precision on exact patterns but might skip general context.")
    print("ML provides broader context detection but might flag generic items (trade-offs).")
    print("==================================================")

if __name__ == "__main__":
    run_benchmark(dataset_size=200)
