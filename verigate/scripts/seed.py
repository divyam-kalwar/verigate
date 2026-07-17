"""Seed script for VeriGate.

Populates `clients`, `users`, and synthetic historical `api_logs` data. Run:

    python -m verigate.scripts.seed

The script is idempotent: it clears and recreates the demo collections so MIS
reports always have predictable sample data.
"""

import random
from datetime import datetime, timedelta, timezone

from verigate.app import create_app
from verigate.database.mongo import get_db
from verigate.scripts.seed_data import CLIENTS, USERS
from verigate.utils.hashing import sha256_hash


LOG_COUNT = 3000
SYNTHETIC_NAMES = [
    "Rahul Sharma",
    "Ananya Mehta",
    "Vikram Rao",
    "Priya Nair",
    "Amit Verma",
    "Neha Iyer",
]
ID_TYPES = ["PAN", "DL", "VOTER"]
SUCCESS_CODES = ["VP2000", "VP2001", "VP2002"]
FAILURE_CODES = ["VP4003", "VP4022", "VP4029", "VP5001"]


def seed() -> None:
    """Clear and reseed clients, users, and historical API logs."""
    db = get_db()

    db["clients"].delete_many({})
    db["users"].delete_many({})
    db["api_logs"].delete_many({})

    db["clients"].insert_many(CLIENTS)
    db["users"].insert_many(USERS)
    db["api_logs"].insert_many(_generate_api_logs())

    users_by_client: dict[str, list[str]] = {}
    for user in USERS:
        users_by_client.setdefault(user["client_id"], []).append(user["user_id"])

    separator = "=" * 48
    print(f"\n{separator}")
    print("  VeriGate seed complete")
    print(separator)
    for client in CLIENTS:
        client_id = client["client_id"]
        print(f"\n  {client['client_name']}")
        print(f"    API Key  : {client['api_key']}")
        print(f"    TPS Limit: {client['tps_limit']}")
        print(f"    IPs      : {', '.join(client['whitelisted_ips'])}")
        print(f"    Users    : {', '.join(users_by_client.get(client_id, []))}")
    print(f"\n  Historical logs inserted: {LOG_COUNT}")
    print(f"\n{separator}\n")


def _generate_api_logs() -> list[dict]:
    """Create deterministic synthetic logs spread across the last 14 days."""
    rng = random.Random(42)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    users_by_client: dict[str, list[str]] = {}
    for user in USERS:
        users_by_client.setdefault(user["client_id"], []).append(user["user_id"])

    logs = []
    for index in range(LOG_COUNT):
        client = CLIENTS[index % len(CLIENTS)]
        client_id = client["client_id"]
        user_id = rng.choice(users_by_client[client_id])
        created_at = now - timedelta(
            days=rng.randint(0, 13),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59),
        )
        id_type = rng.choice(ID_TYPES)
        id_number = f"{id_type}{100000 + index:06d}"
        name = rng.choice(SYNTHETIC_NAMES)

        roll = rng.random()
        if roll < 0.78:
            error_code = rng.choices(SUCCESS_CODES, weights=[82, 12, 6], k=1)[0]
            http_status = 200
            vendor_used = "FALLBACK" if error_code == "VP2001" else "PRIMARY"
            fallback_used = error_code == "VP2001"
            latency_ms = rng.randint(120, 780)
            ip = rng.choice(client["whitelisted_ips"])
        else:
            error_code = rng.choice(FAILURE_CODES)
            http_status = {"VP4003": 403, "VP4022": 422, "VP4029": 429, "VP5001": 502}[error_code]
            vendor_used = None
            fallback_used = False
            latency_ms = rng.randint(0, 900)
            ip = rng.choice(["8.8.8.8", "1.1.1.1", *client["whitelisted_ips"]])

        logs.append(
            {
                "request_id": f"req_seed_{index:06d}",
                "client_id": client_id,
                "user_id": user_id,
                "ip": ip,
                "endpoint": "/api/v1/verify",
                "id_type": id_type,
                "http_status": http_status,
                "error_code": error_code,
                "vendor_used": vendor_used,
                "fallback_used": fallback_used,
                "latency_ms": latency_ms,
                "created_at": created_at,
                "name": _mask(name),
                "name_hash": sha256_hash(name),
                "id_number": _mask(id_number),
                "id_number_hash": sha256_hash(id_number),
            }
        )
    return logs


def _mask(value: str) -> str:
    """Mask all but the last four characters."""
    if len(value) <= 4:
        return "X" * len(value)
    return "X" * (len(value) - 4) + value[-4:]


def main() -> None:
    """Entrypoint: build the app and seed inside an app context."""
    app = create_app()
    with app.app_context():
        seed()


if __name__ == "__main__":
    main()
