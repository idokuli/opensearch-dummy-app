"""
dummy_app_http.py
Fake application that POSTs JSON log events straight to Data Prepper's http
source (no shipper in between). Uses only the Python standard library.

Data Prepper's http source accepts POST requests to /log/ingest with a JSON
array of objects, e.g. [{"key1": "value1"}, {"key2": "value2"}].
"""
import json
import os
import random
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone

# PRIVATE NETWORK: no change needed here — this is the in-cluster Service name
# for Data Prepper, resolved via Kubernetes/OpenShift DNS, not an external host.
DATA_PREPPER_URL = os.environ.get(
    "DATA_PREPPER_URL", "http://data-prepper:2021/log/ingest"
)

LEVELS = ["INFO", "INFO", "INFO", "WARN", "ERROR"]
ROUTES = ["/api/users", "/api/orders", "/api/orders/{id}", "/api/health", "/api/checkout"]
METHODS = ["GET", "GET", "POST", "PUT", "DELETE"]
MESSAGES = {
    "INFO": "request handled successfully",
    "WARN": "slow downstream response",
    "ERROR": "unhandled exception while processing request",
}


def make_log_event():
    level = random.choice(LEVELS)
    status = 200 if level == "INFO" else random.choice([200, 400, 404, 500, 503])
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": "dummy-app",
        "trace_id": str(uuid.uuid4()),
        "method": random.choice(METHODS),
        "route": random.choice(ROUTES),
        "status": status,
        "duration_ms": round(random.uniform(5, 800), 2),
        "message": MESSAGES[level],
    }


def send_batch(events):
    body = json.dumps(events).encode("utf-8")
    req = urllib.request.Request(
        DATA_PREPPER_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status


def main():
    print(f"dummy-app-http POSTing logs to {DATA_PREPPER_URL}", flush=True)
    while True:
        batch = [make_log_event() for _ in range(random.randint(1, 3))]
        try:
            status = send_batch(batch)
            print(f"sent {len(batch)} event(s), status={status}", flush=True)
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"failed to send batch: {e}", flush=True)
        time.sleep(random.uniform(0.5, 2.0))


if __name__ == "__main__":
    main()
