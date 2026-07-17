# VeriGate

VeriGate is a Flask + MongoDB mini API gateway for background verification. It
authenticates clients with API keys, validates sub-users, enforces IP
whitelisting and TPS limits, simulates primary/fallback vendors, logs every
verification request with masked PII, and exposes MIS analytics backed by
MongoDB aggregation pipelines.

---

## Prerequisites

- **Python 3.11+** — install from [python.org](https://www.python.org/downloads/)
- **pip** — included with Python
- **MongoDB** — either [MongoDB Community Server](https://www.mongodb.com/try/download/community) (local) or Docker Desktop
- **Docker Desktop** — required only for the Docker setup ([docker.com](https://www.docker.com/products/docker-desktop/))

### Windows note: `py` vs `python`

On Windows, the Python installer may not add `python.exe` to your `PATH`. If
`python` is not recognized, use the **`py` launcher** instead:

```powershell
py --version
py -m venv venv
py -m pip install -r verigate/requirements.txt
py -m verigate.scripts.seed
py -m verigate.app
py -m pytest verigate/tests
```

All commands below show both forms. Pick the one that works on your machine.

---

## Virtual Environment Setup

### Command Prompt (cmd.exe)

```cmd
python -m venv venv
venv\Scripts\activate.bat
pip install -r verigate/requirements.txt
```

### PowerShell

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r verigate/requirements.txt
```

### PowerShell execution policy workaround

If PowerShell blocks the activation script with an error like:

> "running scripts is disabled on this system"

run this command **once** in an elevated (Run as Administrator) PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then close and reopen PowerShell, then activate the virtual environment again.

---

## Local Development Setup

### 1. Create `.env`

Copy the example environment file and edit values as needed:

```bash
copy .env.example .env
```

Minimum required values:

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

> **Note:** `MONGO_URI=mongodb://localhost:27017` is for local MongoDB. If you
> are using Docker, use `mongodb://mongodb:27017` instead (the Docker Compose
> file handles this automatically).

### 2. Install dependencies

```bash
pip install -r verigate/requirements.txt
```

Expected output:

```text
Collecting blinker==1.9.0
...
Successfully installed Flask-3.1.3 Jinja2-3.1.6 ...
```

### 3. Seed the database

```bash
python -m verigate.scripts.seed
```

Expected output:

```text
================================================
  VeriGate seed complete
================================================

  Alpha Bank
    API Key  : alpha-bank-api-key
    TPS Limit: 5
    IPs      : 127.0.0.1, 103.24.10.5
    Users    : ab_ops_01, ab_ops_02, ab_manager

  Zeta Fin
    API Key  : zeta-fin-api-key
    TPS Limit: 10
    IPs      : 127.0.0.1, 103.24.20.5
    Users    : zf_ops_01, zf_ops_02, zf_manager

  Nova HR
    API Key  : nova-hr-api-key
    TPS Limit: 3
    IPs      : 127.0.0.1, 103.24.30.5
    Users    : nh_ops_01, nh_ops_02, nh_manager

  Historical logs inserted: 3000

================================================
```

The seed script creates:
- 3 clients (`alphabank`, `zetafin`, `novahr`)
- 9 sub-users (2–3 per client)
- 3000 synthetic `api_logs` spread across the last 14 days

### 4. Run the Flask app

```bash
python -m verigate.app
```

Expected output:

```text
 * Serving Flask app 'verigate.app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press Ctrl+C to quit
```

### 5. Run tests

In a separate terminal (with the virtual environment activated):

```bash
pytest verigate/tests -v
```

Expected output:

```text
============================= test session starts =============================
...
verigate/tests/test_api_flows.py::test_invalid_api_key_returns_vp4001 PASSED
verigate/tests/test_api_flows.py::test_non_whitelisted_ip_returns_vp4003 PASSED
verigate/tests/test_api_flows.py::test_payload_validation_returns_vp4022 PASSED
verigate/tests/test_api_flows.py::test_tps_limit_returns_vp4029 PASSED
verigate/tests/test_api_flows.py::test_vendor_fallback_returns_vp2001 PASSED
verigate/tests/test_api_flows.py::test_mis_usage_aggregation_counts_success_and_failures PASSED
verigate/tests/test_api_flows.py::test_usage_export_returns_csv PASSED
verigate/tests/test_api_flows.py::test_errors_export_returns_csv PASSED
verigate/tests/test_api_flows.py::test_tps_export_returns_csv PASSED
verigate/tests/test_api_flows.py::test_fallback_export_returns_csv PASSED
verigate/tests/test_api_flows.py::test_ips_export_returns_csv PASSED
verigate/tests/test_api_flows.py::test_export_empty_result_returns_only_headers PASSED

======================== 12 passed in 2.3s =========================
```

### 6. Run the load test

While the Flask app is running, open another terminal and run:

```bash
python -m verigate.scripts.load_test
```

Expected output:

```text
VeriGate load test summary
================================
alphabank: sent=240 succeeded=180 rate_limited=30 blocked=30 failed=0
zetafin: sent=400 succeeded=350 rate_limited=20 blocked=30 failed=0
novahr: sent=720 succeeded=600 rate_limited=120 blocked=0 failed=0
```

The load test runs for ~60 seconds, fires mixed traffic from all 3 clients,
spoofs blocked IPs, and deliberately exceeds Nova HR's TPS limit (3 req/s) to
demonstrate rate limiting.

---

## Docker Setup

### 1. Start services

```bash
docker compose up --build
```

This builds the Flask image and starts both MongoDB and Flask containers.

### 2. Verify containers are healthy

```bash
docker compose ps
```

Expected output:

```text
NAME               IMAGE            STATUS                    PORTS
verigate-flask     verigate-flask   Up 10 seconds (healthy)   0.0.0.0:5000->5000/tcp
verigate-mongodb   mongo:7          Up 10 seconds (healthy)   0.0.0.0:27017->27017/tcp
```

Both containers must show `healthy` status before proceeding.

### 3. Seed the database

The Docker MongoDB starts empty. Seed it from inside the Flask container:

```bash
docker compose exec flask python -m verigate.scripts.seed
```

Expected output: same as the local seed output shown above.

### 4. Verify the app

```bash
curl http://localhost:5000/health
```

Expected output:

```json
{"status":"healthy","application":"VeriGate"}
```

The app is now available at `http://localhost:5000`.

### 5. Stop services

```bash
docker compose down
```

To also remove the MongoDB data volume (fresh start next time):

```bash
docker compose down -v
```

---

## Local MongoDB vs Docker MongoDB

| Aspect | Local MongoDB | Docker MongoDB |
|--------|--------------|----------------|
| **Installation** | Install MongoDB Community Server on your machine | `mongo:7` image pulled by Docker Compose |
| **Connection** | `MONGO_URI=mongodb://localhost:27017` | `MONGO_URI=mongodb://mongodb:27017` (service name) |
| **Data location** | `/data/db` on your host filesystem | Docker volume `verigate_mongodb_data` |
| **Starting/stopping** | Run `mongod` as a service or manually | `docker compose up` / `docker compose down` |
| **Best for** | Development with existing MongoDB install | One-command setup, clean environment |

If you run Docker, `.env` should already contain `mongodb://mongodb:27017` (set
by `docker-compose.yml`). For local development, change it to
`mongodb://localhost:27017`.

---

## Verify Installation

After setup, run these checks:

```bash
# 1. Health check
curl http://localhost:5000/health
# Expected: {"status":"healthy","application":"VeriGate"}

# 2. Verify endpoint (success)
curl -X POST http://localhost:5000/api/v1/verify ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: alpha-bank-api-key" ^
  -H "X-User-Id: ab_ops_01" ^
  -H "X-Forwarded-For: 127.0.0.1" ^
  -d "{\"client_ref_id\":\"ALB-2026-000123\",\"id_type\":\"PAN\",\"id_number\":\"ABCDE1234F\",\"name\":\"Rahul Sharma\"}"
# Expected: {"status":"SUCCESS","error_code":"VP2000",...}
```

MIS endpoints require the admin key from your `.env`:

```bash
# 3. MIS usage report
curl "http://localhost:5000/api/v1/mis/usage?from=2026-07-01&to=2026-07-17&group_by=client" ^
  -H "X-Admin-Key: admin123"
# Expected: JSON array with total, success, success_via_fallback, etc.

# 4. CSV export
curl "http://localhost:5000/api/v1/mis/usage/export?from=2026-07-01&to=2026-07-17&group_by=client" ^
  -H "X-Admin-Key: admin123" --output usage.csv
# Expected: CSV file with header row and data rows
```

---

## Troubleshooting

### `python` is not recognized

Use `py` instead of `python`:

```bash
py -m venv venv
venv\Scripts\activate
py -m pip install -r verigate/requirements.txt
```

### PowerShell blocks virtual environment activation

If you see an error about execution policy:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then close and reopen PowerShell, then activate the venv again.

### Docker returns `VP4001` (invalid API key)

This usually means the database is empty. Seed it:

```bash
docker compose exec flask python -m verigate.scripts.seed
```

### MongoDB connection failures

**Local:** Ensure `mongod` is running:

```bash
mongod --version
```

**Docker:** Check container health:

```bash
docker compose ps
```

Both `verigate-flask` and `verigate-mongodb` must show `healthy`.

If MongoDB is running but Flask cannot connect, verify `MONGO_URI` in `.env`
matches the target (`localhost:27017` for local, `mongodb:27017` for Docker).

### Health endpoint fails

If `GET /health` returns `VP5000` or does not respond:

1. Check Flask logs: `docker compose logs flask` or console output
2. Verify MongoDB is reachable: `docker compose exec flask python -c "from verigate.database.mongo import get_client; print(get_client().admin.command('ping'))"`
3. Ensure `ADMIN_KEY` is set (MIS endpoints only; health does not need it)

### Port already in use

If port 5000 or 27017 is occupied:

```bash
# Check what is using the port (Windows)
netstat -ano | findstr :5000
netstat -ano | findstr :27017
```

Stop the conflicting process or change the port mapping in `docker-compose.yml`.

---

## Project Structure

```
verigate/
  app.py                    # Flask Application Factory
  config.py                 # Environment-based configuration
  database/
    mongo.py                # MongoDB singleton connection
  routes/
    verify_routes.py        # POST /api/v1/verify
    mis_routes.py           # MIS + CSV export endpoints
  services/
    auth_service.py         # API key + sub-user validation
    ip_whitelist_service.py # X-Forwarded-For IP check
    rate_limiter_service.py # Per-client TPS limiting
    payload_validation_service.py  # Request body validation
    vendor_service.py       # Vendor A / Vendor B + fallback
    logging_service.py      # Request logging with masked PII
    mis_service.py          # MIS analytics pass-through
    csv_export_service.py   # CSV export formatting
  repositories/
    client_repository.py    # MongoDB client access
    user_repository.py      # MongoDB user access
    api_log_repository.py   # MongoDB log access + aggregation pipelines
  utils/
    hashing.py              # SHA-256 PII hashing
  scripts/
    seed.py                 # Seed clients, users, and synthetic logs
    seed_data.py            # Static seed fixtures
    load_test.py            # 60-second mixed-traffic load test
  tests/
    test_api_flows.py       # Integration tests (pytest)
  docs/
    AI_WORKFLOW.md          # Claude Code workflow write-up
    curl_examples.md        # curl examples for every endpoint
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key` | Flask secret key |
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `DATABASE_NAME` | `verigate` | MongoDB database name |
| `ADMIN_KEY` | *(empty)* | Required for all MIS endpoints |
| `VENDOR_A_FAILURE_RATE` | `0.2` | Probability Vendor A fails |
| `VENDOR_A_TIMEOUT_RATE` | `0.1` | Probability Vendor A times out |
| `VENDOR_MIN_LATENCY_MS` | `100` | Minimum simulated vendor latency (ms) |
| `VENDOR_MAX_LATENCY_MS` | `800` | Maximum simulated vendor latency (ms) |
| `VENDOR_B_FAILURE_RATE` | `0.0` | Probability Vendor B fails |

---

## MongoDB Indexes

The app creates these `api_logs` indexes on startup:

```text
client_id_created_at: supports client/date MIS range queries.
error_code: supports error-distribution reporting.
```

---

## Notes

- `X-Forwarded-For` is supported for local assignment testing so requests can
  simulate different source IPs. In production, this header should only be trusted
  behind a trusted load balancer or reverse proxy that overwrites untrusted
  client-supplied values.

- The TPS limiter is in-memory and suitable for this single-process assignment.
  With multiple Gunicorn workers or pods, counters would not be shared; Redis
  would be the natural replacement.

- All MIS endpoints return JSON by default. Append `?format=csv` to `/usage` or
  `/errors` for a CSV download, or use the dedicated `/export` endpoints.

- The seed script clears and recreates `clients`, `users`, and `api_logs` on
  every run. Do not run it in production.
