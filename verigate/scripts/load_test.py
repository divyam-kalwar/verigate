"""Small load script for demonstrating TPS limits and MIS logging.

Run while the Flask app is available at http://localhost:5000:

    python -m verigate.scripts.load_test

The script sends mixed traffic for all seeded clients, including invalid source
IPs and a burst for Nova HR that should exceed its TPS limit.
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "http://localhost:5000"
VERIFY_URL = f"{BASE_URL}/api/v1/verify"
RUN_SECONDS = 60


@dataclass(frozen=True)
class ClientTraffic:
    client_id: str
    api_key: str
    user_id: str
    allowed_ip: str
    blocked_ip: str
    delay_seconds: float


CLIENTS = [
    ClientTraffic("alphabank", "alpha-bank-api-key", "ab_ops_01", "127.0.0.1", "8.8.8.8", 0.25),
    ClientTraffic("zetafin", "zeta-fin-api-key", "zf_ops_01", "127.0.0.1", "8.8.4.4", 0.15),
    # Nova HR has tps_limit=3 in seed data; this delay intentionally exceeds it.
    ClientTraffic("novahr", "nova-hr-api-key", "nh_ops_01", "127.0.0.1", "1.1.1.1", 0.05),
]


def _payload(client_id: str, counter: int) -> dict:
    return {
        "client_ref_id": f"{client_id.upper()}-{counter:06d}",
        "id_type": "PAN",
        "id_number": "ABCDE1234F",
        "name": "Rahul Sharma",
    }


def _post_verify(client: ClientTraffic, ip: str, counter: int) -> tuple[int, str | None]:
    body = json.dumps(_payload(client.client_id, counter)).encode("utf-8")
    request = Request(
        VERIFY_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": client.api_key,
            "X-User-Id": client.user_id,
            "X-Forwarded-For": ip,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return response.status, data.get("error_code")
    except HTTPError as exc:
        data = json.loads(exc.read().decode("utf-8"))
        return exc.code, data.get("error_code")
    except URLError:
        return 0, "NETWORK_ERROR"


def _worker(client: ClientTraffic, stop_at: float, summary: Dict[str, Dict[str, int]]) -> None:
    counter = 0
    while time.monotonic() < stop_at:
        counter += 1
        ip = client.blocked_ip if counter % 7 == 0 else client.allowed_ip
        status, error_code = _post_verify(client, ip, counter)

        bucket = summary[client.client_id]
        bucket["sent"] += 1
        if status == 200:
            bucket["succeeded"] += 1
        elif error_code == "VP4029":
            bucket["rate_limited"] += 1
        elif error_code == "VP4003":
            bucket["blocked"] += 1
        else:
            bucket["failed"] += 1

        time.sleep(client.delay_seconds)


def main() -> None:
    """Run mixed traffic and print a compact per-client summary."""
    stop_at = time.monotonic() + RUN_SECONDS
    summary: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    threads = [
        threading.Thread(target=_worker, args=(client, stop_at, summary), daemon=True)
        for client in CLIENTS
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    print("\nVeriGate load test summary")
    print("=" * 32)
    for client in CLIENTS:
        row = summary[client.client_id]
        print(
            f"{client.client_id}: sent={row['sent']} "
            f"succeeded={row['succeeded']} "
            f"rate_limited={row['rate_limited']} "
            f"blocked={row['blocked']} "
            f"failed={row['failed']}"
        )


if __name__ == "__main__":
    main()
