# VeriGate

VeriGate is a Flask + MongoDB mini API gateway for background verification. It
authenticates clients with API keys, validates sub-users, enforces IP
whitelisting and TPS limits, simulates primary/fallback vendors, logs every
verification request with masked PII, and exposes MIS analytics backed by
MongoDB aggregation pipelines.

## Quick Start

Create a virtual environment, install dependencies, and configure environment
variables:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r verigate/requirements.txt
copy .env.example .env
```

Set at least these values in `.env`:

```text
SECRET_KEY=dev-secret-key
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=verigate
ADMIN_KEY=change-me
VENDOR_A_FAILURE_RATE=0.2
VENDOR_A_TIMEOUT_RATE=0.1
VENDOR_MIN_LATENCY_MS=100
VENDOR_MAX_LATENCY_MS=800
VENDOR_B_FAILURE_RATE=0.0
```

Seed demo clients/users and run the app:

```bash
python -m verigate.scripts.seed
python -m verigate.app
```

The seed script also inserts synthetic historical `api_logs` spread across
recent dates so MIS reports show data immediately.

Run tests:

```bash
pytest verigate/tests
```

Run the load/TPS demonstration while the app is running:

```bash
python -m verigate.scripts.load_test
```

## Docker

Run app + MongoDB together:

```bash
docker compose up --build
```

The app is exposed at `http://localhost:5000`.

## Verification API

`POST /api/v1/verify`

Headers:

```text
X-API-Key: alpha-bank-api-key
X-User-Id: ab_ops_01
X-Forwarded-For: 127.0.0.1
```

Body:

```json
{
  "client_ref_id": "ALB-2026-000123",
  "id_type": "PAN",
  "id_number": "ABCDE1234F",
  "name": "Rahul Sharma"
}
```

## MIS APIs

All MIS endpoints require:

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

`format=csv` is supported on usage and errors endpoints.

Additional request examples are available in `docs/curl_examples.md`.

## Notes

`X-Forwarded-For` is supported for local assignment testing so requests can
simulate different source IPs. In production, this header should only be trusted
behind a trusted load balancer or reverse proxy that overwrites untrusted
client-supplied values.

The TPS limiter is in-memory and suitable for this single-process assignment.
With multiple Gunicorn workers or pods, counters would not be shared; Redis
would be the natural replacement.

## MongoDB Indexes

The app creates these `api_logs` indexes on startup:

```text
client_id_created_at: supports client/date MIS range queries.
error_code: supports error-distribution reporting.
```
