# VeriGate — Project Memory

Flask + MongoDB "verification API gateway" take-home assignment (Valuepitch E-Technologies).
Repo root: `D:\VeriGate`; Python package lives in `D:\VeriGate\verigate\`. Run tests/imports from repo root so the `verigate` package resolves.

## Architecture (CLAUDE.md — strict layered)
Request flow: Routes -> Services -> Repositories -> MongoDB.
- Business logic ONLY in services; DB access ONLY in repositories; routes stay thin.
- App Factory pattern: `verigate/app.py` -> `create_app()`. Wires services into `app.extensions` and registers blueprints (`verify_bp`, `mis_bp`).
- Config via `verigate/config.py` `Config` class (env vars + python-dotenv). Never hardcode secrets.
- MongoDB: `verigate/database/mongo.py` singleton `MongoClient` (`init_mongo` pings; `get_db()`/`get_client()` via `current_app.extensions`). Repos call `get_db()["<coll>"]`.
- Errors: `exceptions/api_exception.py` `ApiException` subclasses; `app.py` `@app.errorhandler(ApiException)` returns uniform envelope `{request_id, status, error_code, message}`. Codes in `exceptions/error_codes.py` (`ErrorCodes`, `HttpStatus`): VP2000/2001/2002, VP4001, VP4003, VP4022, VP4029, VP5001, VP5000.
- PII rule: never store raw `name`/`id_number` — store masked (last 4) + SHA-256 hash.

## Service registration pattern (every new service follows this)
1. Create `services/<name>_service.py` (logic + result dataclasses).
2. Add `build_<name>_service()` in `services/__init__.py`.
3. Register `app.extensions["<name>_service"] = build_<name>_service()` in `create_app()`.

## verify_routes.py flow (post /api/v1/verify)
`before_request` (enforce_access_control): auth -> IP whitelist -> TPS -> payload validation, each via its service, storing context on Flask `g` (incremental: g.client/g.user right after auth, g.client_ip before IP enforce so rejected IPs are still logged). `teardown_request` calls LoggingService once per request (logs ALL outcomes). Handler calls VendorService, maps VendorResult to success envelope (VP2000 PRIMARY / VP2001 FALLBACK).

## Features completed this session (in order)
- Project setup: app.py, config.py, database/mongo.py, routes (verify_bp/mis_bp), /health.
- AuthService + ClientRepository + UserRepository (VP4001).
- scripts/seed.py (3 clients alphabank/zetafin/novahr, 3 users each, clears clients+users only, idempotent).
- IpWhitelistService (X-Forwarded-For first IP -> remote_addr; VP4003).
- RateLimiterService (in-memory Fixed Window Counter, time.monotonic, per-client; VP4029).
- PayloadValidationService (required fields client_ref_id/id_type/id_number/name, str+non-empty+id_type in {PAN,DL,VOTER}; VP4022).
- VendorService + VendorA/VendorB (simulated latency/failure/timeout via env; fallback A->B; VendorError internal; VP5001 on both fail). VendorResult dataclass {verified,name_match_score,source,latency_ms}.
- Request Logging: repositories/api_log_repository.py (insert + ensure_indexes (client_id,created_at) & error_code), services/logging_service.py (mask_name/mask_id_number/sha256_hash, UTC created_at), utils/hashing.py sha256_hash. Indexes created in create_app via app_context.

## CLAUDE.md progress checklist (complete through Request Logging)
Setup, MongoDB connection, Seed data, Authentication, User validation, IP Whitelisting, TPS Limiter, Payload Validation, Vendor Simulation, Fallback Logic, Request Logging = DONE.
Remaining (NOT done): MIS APIs, CSV Export, Load Testing, Unit Testing, Docker, Documentation.

## Known pitfalls / corrections made during session
- `app.extensions["auth_service"]` must be set in create_app or before_request raises RuntimeError (found & fixed via Option A: wire in create_app).
- `teardown_request` is a blueprint METHOD, not imported from flask.
- `ensure_indexes()` must run inside `app.app_context()`.
- Bug: context (g.client etc.) was assigned only at END of before_request, so early rejections lost client_id/user_id/ip in logs. Fixed by storing incrementally as each step passes; resolved IP stored before enforce so bad-IP attempts are logged with the offending IP.
- `verify_routes.py` uses `payload_service.validate_verify_request(payload)` and `vendor_service.verify(g.payload)` (names evolved across session).

## User feedback / working style
- User wants SLOW, reviewable steps: implement ONE feature, explain decisions, let them review — do NOT bundle many files/features in one turn. The assignment is about understanding every file, not speed.
- Always review documentation (CLAUDE.md) — AI duplicated a checklist item once; user caught it.
- For each new file: explain why it exists and how it interacts with the rest.
