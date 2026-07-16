"""Static seed fixtures for VeriGate clients and users.

Keeping data separate from the seeding script (`seed.py`) means each file stays
focused on a single responsibility:

- seed_data.py  → what to insert  (pure data, no DB calls)
- seed.py       → how to insert it (DB connection, print summary, etc.)

To add a new client or change user IDs, edit only this file.
"""

CLIENTS: list[dict] = [
    {
        "client_id": "alphabank",
        "client_name": "Alpha Bank",
        "api_key": "alpha-bank-api-key",
        "whitelisted_ips": ["127.0.0.1", "103.24.10.5"],
        "tps_limit": 5,
        "status": "active",
    },
    {
        "client_id": "zetafin",
        "client_name": "Zeta Fin",
        "api_key": "zeta-fin-api-key",
        "whitelisted_ips": ["127.0.0.1", "103.24.20.5"],
        "tps_limit": 10,
        "status": "active",
    },
    {
        "client_id": "novahr",
        "client_name": "Nova HR",
        "api_key": "nova-hr-api-key",
        "whitelisted_ips": ["127.0.0.1", "103.24.30.5"],
        "tps_limit": 3,
        "status": "active",
    },
]

# Explicit user list — realistic IDs that read well in MIS reports.
USERS: list[dict] = [
    # Alpha Bank
    {"client_id": "alphabank", "user_id": "ab_ops_01"},
    {"client_id": "alphabank", "user_id": "ab_ops_02"},
    {"client_id": "alphabank", "user_id": "ab_manager"},
    # Zeta Fin
    {"client_id": "zetafin", "user_id": "zf_ops_01"},
    {"client_id": "zetafin", "user_id": "zf_ops_02"},
    {"client_id": "zetafin", "user_id": "zf_manager"},
    # Nova HR
    {"client_id": "novahr", "user_id": "nh_ops_01"},
    {"client_id": "novahr", "user_id": "nh_ops_02"},
    {"client_id": "novahr", "user_id": "nh_manager"},
]
