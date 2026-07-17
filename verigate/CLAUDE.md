# CLAUDE.md

# Project Overview

Project Name: VeriGate

VeriGate is a Flask + MongoDB based API Gateway that simulates an enterprise Background Verification (BGV) platform.

The application authenticates clients using API Keys, validates sub-users, enforces IP whitelisting and per-client TPS limits, performs verification using simulated vendors with automatic fallback, logs every request with masked PII, and provides MIS/Analytics APIs using MongoDB Aggregation Pipelines.

This project is being developed as a take-home assignment for Valuepitch E-Technologies.

---

# Technology Stack

- Python 3.11+
- Flask
- PyMongo
- MongoDB
- python-dotenv
- pytest

---

# Project Architecture

Use a layered architecture.

Request Flow:

Routes
    ↓
Services
    ↓
Repositories
    ↓
MongoDB

Business logic belongs only inside Services.

Database operations belong only inside Repositories.

Routes should remain thin.

---

# Folder Structure

app.py

config.py

database/

routes/

services/

repositories/

utils/

scripts/

tests/

docs/

---

# Coding Standards

- Follow PEP8.
- Use type hints wherever appropriate.
- Write readable and maintainable code.
- Keep functions small and focused.
- Use descriptive variable names.
- Avoid duplicate code.
- Add docstrings to public functions.

---

# Configuration

Never hardcode secrets.

Read configuration from environment variables.

Use config.py for configuration management.

---

# MongoDB

Use a singleton MongoClient.

Collections:

- clients
- users
- api_logs

Required indexes:

- client_id + created_at
- error_code

Use UTC timestamps.

---

# API Design

Always return JSON.

Use appropriate HTTP status codes.

Use the standard error codes defined in the assignment.

Never expose stack traces to clients.

---

# Logging

Every request must be logged.

Log successful requests.

Log rejected requests.

Log failed requests.

Never log raw PII.

Mask sensitive values before storing.

Store SHA-256 hashes where required.

---

# Vendor Simulation

Implement:

Vendor A (Primary)

Vendor B (Fallback)

Vendor behavior should be configurable using environment variables.

Do not call external APIs.

---

# Rate Limiting

Implement an in-memory per-client TPS limiter.

Keep the implementation modular so it can later be replaced by Redis.

---

# Analytics

MIS endpoints must use MongoDB Aggregation Pipelines.

Avoid processing large datasets in Python.

---

# Testing

Use pytest.

Write unit tests for:

- Invalid API Key
- Invalid User
- Non-whitelisted IP
- Payload validation
- TPS limit
- Vendor fallback
- MIS aggregation

---

# Development Rules

Implement one feature at a time.

Do not generate multiple unrelated features in one response.

Always explain architectural decisions.

When creating new files:

- Explain why the file exists.
- Explain how it interacts with the rest of the project.

When modifying existing code:

- Prefer improving existing code instead of rewriting everything.

---

# Assistant Behavior

Act as a senior backend engineer.

Prioritize maintainability over clever solutions.

If requirements are ambiguous, explain assumptions before implementing.

Always explain important design decisions.

# Project Progress

- [x] Project setup
- [x] MongoDB connection
- [x] Seed data
- [x] Authentication
- [x] User validation
- [x] IP Whitelisting
- [x] TPS Limiter
- [x] Payload Validation
- [x] Vendor Simulation
- [x] Fallback Logic
- [x] Request Logging
- [ ] MIS APIs
- [ ] CSV Export
- [ ] Load Testing
- [ ] Unit Testing
- [ ] Docker
- [ ] Documentation