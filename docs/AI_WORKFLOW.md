# AI Workflow

This project was built iteratively with AI assistance, using the assistant as a
pair-programming partner for scaffolding, implementation, review, and fixes.

## What Was Delegated

- Flask application factory and blueprint wiring.
- MongoDB connection setup with a singleton `MongoClient`.
- Repository/service layering.
- Authentication and sub-user validation.
- IP whitelisting and TPS limiting.
- Payload validation.
- Vendor simulation and fallback behavior.
- Request logging with masked PII.
- MIS aggregation endpoints.
- Docker and Docker Compose setup.
- Test scaffolding for core assignment flows.

## Representative Prompts

1. Analyze the current project.
2. Create a custom exception and one global error handler.
3. Add IP whitelisting after authentication.
4. Add TPS limiting and explain why `time.monotonic()` is preferred.
5. Add payload validation for the verify request.
6. Add vendor simulation with fallback.
7. Log every request with masked PII.
8. Add MIS reports using MongoDB aggregation pipelines.

## Example Of AI Output That Needed Correction

The assistant initially changed request state from separate Flask `g` attributes
to a single `g.request_context` dictionary. That was technically valid, but it
changed the project's established style midstream. We reverted to the existing
pattern:

```text
g.client
g.user
g.client_ip
```

This kept the codebase consistent and easier to follow.

Another issue was successful logs storing `error_code=None` while MIS reports
expected success codes such as `VP2000` and `VP2001`. We corrected the verify
route so successful logs are self-describing and aggregation results count
successes correctly.

## Ownership Notes

All AI-generated changes were reviewed manually. The main focus during review
was correctness against the assignment requirements, consistent architecture,
PII safety, and whether MIS reports could be derived from the logs.

Estimated split: roughly 70% AI-assisted implementation and 30% manual review,
testing, correction, and architectural direction.
