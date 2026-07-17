# VeriGate

Flask + MongoDB mini verification API gateway for the Valuepitch assignment.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set values:

```bash
SECRET_KEY=dev-secret-key
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=verigate
ADMIN_KEY=change-me
VENDOR_A_FAILURE_RATE=0.2
VENDOR_A_TIMEOUT_RATE=0.1
```

4. Seed clients and users:

```bash
python -m verigate.scripts.seed
```

5. Run the app:

```bash
python -m verigate.app
```

## Verification API

`POST /api/v1/verify`

Required headers:

```text
X-API-Key: alpha-bank-api-key
X-User-Id: ab_ops_01
X-Forwarded-For: 127.0.0.1
```

Example body:

```json
{
  "client_ref_id": "ALB-2026-000123",
  "id_type": "PAN",
  "id_number": "ABCDE1234F",
  "name": "Rahul Sharma"
}
```

## MIS APIs

All MIS endpoints require the admin header:

```text
X-Admin-Key: <ADMIN_KEY from .env>
```

Endpoints:

```text
GET /api/v1/mis/usage?from=2026-07-01&to=2026-07-07&group_by=client
GET /api/v1/mis/errors?from=2026-07-01&to=2026-07-07
GET /api/v1/mis/tps?client_id=alphabank&date=2026-07-17
GET /api/v1/mis/fallback?from=2026-07-01&to=2026-07-07
GET /api/v1/mis/ips?client_id=alphabank&from=2026-07-01&to=2026-07-07
```

Missing or invalid admin keys return the standard error envelope with `VP4001`.

## Notes

`X-Forwarded-For` is accepted for local assignment testing so different source
IPs can be simulated. In production, this header should only be trusted when the
application is behind a trusted load balancer or reverse proxy that overwrites
untrusted client-supplied values.

The in-memory TPS limiter is suitable for this single-process assignment. With
multiple Gunicorn workers or pods, each process would have its own counter; a
shared store such as Redis would be needed for consistent rate limiting.

## MongoDB Indexes

The app creates these `api_logs` indexes on startup:

```text
client_id_created_at: supports client/date MIS range queries.
error_code: supports error-distribution reporting.
```
