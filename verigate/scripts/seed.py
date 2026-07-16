"""Seed script for VeriGate.

Populates the `clients` and `users` collections with the fixtures defined in
`seed_data.py`. Run manually:

    python -m verigate.scripts.seed

Design decisions
----------------
* All data lives in seed_data.py — this script only handles DB connection and
  print output. Adding a new client or user requires no change here.
* Connects through the existing DB layer: builds the real Flask app via
  `create_app()` so `init_mongo()` and python-dotenv run exactly as at runtime.
  One connection path, no duplicated credentials.
* Only clears `clients` and `users` — `api_logs` are never touched so
  historical log data is preserved across reseeds.
* Idempotent: drop-and-reinsert yields the same state on every run.
"""

from verigate.app import create_app
from verigate.database.mongo import get_db
from verigate.scripts.seed_data import CLIENTS, USERS


def seed() -> None:
    """Clear and reseed the clients and users collections."""
    db = get_db()

    db["clients"].delete_many({})
    db["users"].delete_many({})

    db["clients"].insert_many(CLIENTS)
    db["users"].insert_many(USERS)

    # Group users by client for the summary banner
    users_by_client: dict[str, list[str]] = {}
    for user in USERS:
        users_by_client.setdefault(user["client_id"], []).append(user["user_id"])

    separator = "=" * 48
    print(f"\n{separator}")
    print("  VeriGate seed complete")
    print(separator)
    for client in CLIENTS:
        cid = client["client_id"]
        print(f"\n  {client['client_name']}")
        print(f"    API Key  : {client['api_key']}")
        print(f"    TPS Limit: {client['tps_limit']}")
        print(f"    IPs      : {', '.join(client['whitelisted_ips'])}")
        print(f"    Users    : {', '.join(users_by_client.get(cid, []))}")
    print(f"\n{separator}\n")


def main() -> None:
    """Entrypoint: build the app (opens DB via the existing layer) and seed."""
    app = create_app()
    with app.app_context():
        seed()


if __name__ == "__main__":
    main()
