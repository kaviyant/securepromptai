# SecurePrompt AI - Testing Documentation

This document explains the test suite layout, execution commands, and test verification procedures.

## 📂 Testing Layout

The test files reside under `/tests` in the workspace root:

1. **`tests/test_unit.py`**:
   - Focus: Mathematical validations and basic regex matching.
   - Asserts: Population Stability Index (PSI) calculations, risk severity weight math, Luhn CC validations, and ContentClassifier heuristic accuracy.
2. **`tests/test_integration.py`**:
   - Focus: Databases, connection pipelines, and state transitions.
   - Asserts: MongoDB record saving/reading, and Retraining database log extraction.
3. **`tests/test_extension.py`**:
   - Focus: Extension client compatibility.
   - Asserts: Mimics browser extension POST payloads to `/api/scan` and checks response schemas (keys: `action`, `risk_score`, `sanitized_prompt`).
4. **`tests/test_api.py`**:
   - Focus: Web server routing gates and security permissions.
   - Asserts: JWT Login, Swagger UI health endpoints, and metrics scrape targets.
5. **`tests/load_test.py`**:
   - Focus: System throughput and concurrent load handling.
   - Asserts: Fires concurrent async requests to `/api/scan` and reports average latency and Requests Per Second (RPS) statistics.

---

## 🏃 Execution Commands

Ensure you have activated your virtual environment:

### 1. Run Unit Tests
```bash
python -m unittest tests/test_unit.py -v
```

### 2. Run API and Extension Mock Tests
```bash
python -m unittest tests/test_api.py tests/test_extension.py -v
```

### 3. Run Integration Tests
*Ensure a local MongoDB server is active on `27017` or configured via MONGODB_URL env*:
```bash
python -m unittest tests/test_integration.py -v
```

### 4. Run All Test Suites under Pytest
```bash
python -m pytest tests/ -v
```

### 5. Execute Concurrency Load Testing
Generate concurrent queries to evaluate throughput:
```bash
# Simulates 20 concurrent client workers spamming requests for 10 seconds
python tests/load_test.py --url http://localhost:8000 --concurrency 20 --duration 10
```

---

## 📈 Interpreting Load Test Outputs

Upon running `load_test.py`, the terminal outputs:
- **Total Requests**: Sum of queries sent.
- **Throughput (RPS)**: Transactions processed per second.
- **Average Latency**: Round-trip request processing time in milliseconds.
- **95th Percentile (p95)**: Tail latency benchmark (95% of queries completed under this threshold).
- **Failed/Errors**: Request timeouts or network disconnect counts.
