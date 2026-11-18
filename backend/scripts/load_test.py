import os
import json
import time
from datetime import date
from fastapi.testclient import TestClient
from app.main import app

def percentile_nearest_rank(data, p):
    if not data:
        return None
    sorted_data = sorted(data)
    n = len(sorted_data)
    rank = int((p / 100) * n)
    if rank < 1:
        rank = 1
    # nearest-rank: rank-th smallest, 1-indexed
    return sorted_data[rank - 1]

def main():
    os.makedirs("results", exist_ok=True)
    queries = [
        "hex bolt zinc",
        "steel nut 1/2",
        "washer 3/8",
        "M8x30 flange bolt",
        "hex nut",
        "stainless screw",
        "zzqxv qqwpl",
        "xyzzy plugh",
        "qqqq zzzz",
        "bolt " * 50,
    ]
    n_requests = 500
    server_latencies = []
    client_times = []
    engine_times = []
    routing_times = []
    error_count = 0

    with TestClient(app) as client:
        for i in range(n_requests):
            q = queries[i % len(queries)]
            try:
                start = time.perf_counter()
                r = client.post("/search", json={"query": q})
                elapsed = time.perf_counter() - start
            except Exception:
                error_count += 1
                client_times.append(None)
                continue
            client_times.append(elapsed)
            if r.status_code != 200:
                error_count += 1
                continue
            try:
                data = r.json()
            except Exception:
                error_count += 1
                continue
            server_latencies.append(float(data.get("latency_ms", 0)))
            timing = data.get("timing_ms", {})
            engine_times.append(float(timing.get("engine", 0)))
            routing_times.append(float(timing.get("routing", 0)))

    # filter None for client times where exception
    client_times_valid = [t for t in client_times if t is not None]

    def compute_percentiles(vals):
        return {
            "p50": percentile_nearest_rank(vals, 50),
            "p95": percentile_nearest_rank(vals, 95),
            "p99": percentile_nearest_rank(vals, 99),
        }

    result = {
        "date": str(date.today()),
        "n_requests": n_requests,
        "error_count": error_count,
        "server_latency_ms": compute_percentiles(server_latencies),
        "client_wall_time_s": compute_percentiles(client_times_valid),
        "engine_ms": compute_percentiles(engine_times),
        "routing_ms": compute_percentiles(routing_times),
    }

    out_path = os.path.join("results", "latency.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # print short table
    print(f"{'Metric':<20} {'p50':<15} {'p95':<15} {'p99':<15}")
    for name, vals in [
        ("server_latency_ms", result["server_latency_ms"]),
        ("client_wall_time_s", result["client_wall_time_s"]),
        ("engine_ms", result["engine_ms"]),
        ("routing_ms", result["routing_ms"]),
    ]:
        print(f"{name:<20} {vals['p50']:<15} {vals['p95']:<15} {vals['p99']:<15}")

if __name__ == "__main__":
    main()
