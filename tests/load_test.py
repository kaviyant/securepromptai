import asyncio
import time
import argparse
import sys
import httpx
from typing import List

# Mock prompts of varying lengths and threat signatures
PROMPTS = [
    "How do I cook pasta at home?",
    "AWS credentials: AWS_KEY='AKIA1234567890ABCDEF'",
    "My email is test@secureprompt.ai and phone is +1-202-555-0143.",
    "We need to analyze Q4 EBITDA margins and forecast balance sheet profiles.",
    "Connect DB using password: 'super_secret_db_pass_123'",
    "def parse_token(auth_header): return auth_header.split(' ')[1]"
]

async def send_scan_request(client: httpx.AsyncClient, url: str) -> float:
    """
    Sends a single prompt scan request and returns the latency in milliseconds.
    """
    # Pick a prompt based on time modulo
    idx = int(time.time() * 1000) % len(PROMPTS)
    payload = {
        "prompt": PROMPTS[idx],
        "website": "loadtest.secureprompt.ai",
        "timestamp": int(time.time() * 1000),
        "session_id": "loadtest-session",
        "browser_info": {
            "userAgent": "LoadTestRunner/1.0",
            "language": "en-US",
            "platform": "Linux"
        }
    }
    
    start = time.time()
    try:
        response = await client.post(f"{url}/api/scan", json=payload, timeout=5.0)
        latency = (time.time() - start) * 1000
        if response.status_code == 200:
            return latency
        else:
            return -response.status_code # Encode error code as negative
    except httpx.RequestError:
        return -1 # Request exception

async def worker(url: str, duration: int, latencies: List[float]):
    """
    Worker task sending continuous requests for the duration.
    """
    end_time = time.time() + duration
    async with httpx.AsyncClient() as client:
        while time.time() < end_time:
            lat = await send_scan_request(client, url)
            latencies.append(lat)
            # Minimal sleep to prevent instant socket exhaustion
            await asyncio.sleep(0.01)

async def main(url: str, concurrency: int, duration: int):
    print("================================================================")
    print(f"STARTING SECUREPROMPT AI LOAD TEST")
    print(f"Target URL:    {url}")
    print(f"Concurrency:   {concurrency} workers")
    print(f"Duration:      {duration} seconds")
    print("================================================================")
    
    latencies = []
    start_time = time.time()
    
    # Spawn concurrent workers
    tasks = [worker(url, duration, latencies) for _ in range(concurrency)]
    await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # Process results
    valid_latencies = [l for l in latencies if l >= 0]
    errors = [l for l in latencies if l < 0]
    
    total_reqs = len(latencies)
    success_reqs = len(valid_latencies)
    err_reqs = len(errors)
    
    rps = total_reqs / total_time if total_time > 0 else 0
    avg_latency = sum(valid_latencies) / len(valid_latencies) if valid_latencies else 0
    
    # Percentiles
    valid_latencies.sort()
    p50 = valid_latencies[int(len(valid_latencies) * 0.5)] if valid_latencies else 0
    p95 = valid_latencies[int(len(valid_latencies) * 0.95)] if valid_latencies else 0
    
    print("\n------------------------- RESULTS -------------------------")
    print(f"Total Requests:       {total_reqs}")
    print(f"Successful Requests:  {success_reqs}")
    print(f"Failed/Errors:        {err_reqs}")
    print(f"Throughput (RPS):     {rps:.2f} req/sec")
    print(f"Average Latency:      {avg_latency:.2f} ms")
    print(f"50th Percentile (p50):{p50:.2f} ms")
    print(f"95th Percentile (p95):{p95:.2f} ms")
    print("------------------------------------------------------------\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SecurePrompt AI Load Stress Tester")
    parser.add_argument("--url", default="http://localhost:8000", help="Root URL of the target API")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--duration", type=int, default=5, help="Test duration in seconds")
    
    # Parse args while ignoring Jupyter notebooks artifacts if run in interactive environments
    args, unknown = parser.parse_known_args()
    
    asyncio.run(main(args.url, args.concurrency, args.duration))
