# VeriGate Project Context

VeriGate is a Flask + MongoDB background-verification API gateway assignment.

## Stack

- Python 3.11+
- Flask
- PyMongo
- MongoDB
- python-dotenv
- pytest
- Docker / Docker Compose

## Architecture

Use a layered architecture:

```text
Routes -> Services -> Repositories -> MongoDB
```

Business logic belongs in services. MongoDB access belongs in repositories.
Routes should stay thin and only map HTTP requests/responses.

## Key Features

- API-key authentication with sub-user validation
- IP whitelisting using `X-Forwarded-For` for local testing
- In-memory per-client TPS limiting
- Payload validation for `/api/v1/verify`
- Simulated primary/fallback vendors
- Request logging with masked PII and SHA-256 hashes
- MIS analytics via MongoDB aggregation pipelines
- CSV export for usage and error reports
- Docker / Docker Compose support

## Commands

Install dependencies:

```bash
pip install -r verigate/requirements.txt
```

Seed data:

```bash
python -m verigate.scripts.seed
```

Run app:

```bash
python -m verigate.app
```

Run tests:

```bash
pytest verigate/tests
```

Run load test:

```bash
python -m verigate.scripts.load_test
```

Run Docker:

```bash
docker compose up --build
```

## Coding Rules

- Keep functions small and readable.
- Use type hints for public service/repository methods.
- Do not log raw PII.
- Use standard VP error codes.
- Keep configuration in environment variables.
- Prefer improving existing modules over broad rewrites.

## Project Progress

- [x] Project setup
- [x] MongoDB connection
- [x] Seed data
- [x] Authentication
- [x] User validation
- [x] IP whitelisting
- [x] TPS limiter
- [x] Payload validation
- [x] Vendor simulation
- [x] Fallback logic
- [x] Request logging
- [x] MIS APIs
- [x] CSV export
- [x] Docker
- [x] Documentation
- [x] Tests
- [x] Load testing
