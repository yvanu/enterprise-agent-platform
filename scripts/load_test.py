import argparse
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed


def request(url: str, token: str) -> tuple[bool, float]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
            return 200 <= response.status < 400, (time.perf_counter() - started) * 1000
    except Exception:
        return False, (time.perf_counter() - started) * 1000


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percent)))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(request, args.url, args.token) for _ in range(args.requests)]
        results = [future.result() for future in as_completed(futures)]

    latencies = [latency for _, latency in results]
    success = sum(ok for ok, _ in results)
    print(f"requests={len(results)} success={success} failed={len(results)-success}")
    print(
        "latency_ms "
        f"avg={statistics.mean(latencies):.1f} "
        f"p50={percentile(latencies, 0.50):.1f} "
        f"p95={percentile(latencies, 0.95):.1f}"
    )
    return 0 if success == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
