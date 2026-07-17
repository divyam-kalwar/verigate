# VeriGate curl Examples

Assumes the app is running at `http://localhost:5000` and seed data has been
loaded with:

```bash
python -m verigate.scripts.seed
```

## Health

```bash
curl http://localhost:5000/health
```

## Verify Success

```bash
curl -X POST http://localhost:5000/api/v1/verify ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: alpha-bank-api-key" ^
  -H "X-User-Id: ab_ops_01" ^
  -H "X-Forwarded-For: 127.0.0.1" ^
  -d "{\"client_ref_id\":\"ALB-2026-000123\",\"id_type\":\"PAN\",\"id_number\":\"ABCDE1234F\",\"name\":\"Rahul Sharma\"}"
```

## Invalid API Key

```bash
curl -X POST http://localhost:5000/api/v1/verify ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: bad-api-key" ^
  -H "X-User-Id: ab_ops_01" ^
  -H "X-Forwarded-For: 127.0.0.1" ^
  -d "{\"client_ref_id\":\"ALB-2026-000123\",\"id_type\":\"PAN\",\"id_number\":\"ABCDE1234F\",\"name\":\"Rahul Sharma\"}"
```

## Non-Whitelisted IP

```bash
curl -X POST http://localhost:5000/api/v1/verify ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: alpha-bank-api-key" ^
  -H "X-User-Id: ab_ops_01" ^
  -H "X-Forwarded-For: 8.8.8.8" ^
  -d "{\"client_ref_id\":\"ALB-2026-000123\",\"id_type\":\"PAN\",\"id_number\":\"ABCDE1234F\",\"name\":\"Rahul Sharma\"}"
```

## Payload Validation Failure

```bash
curl -X POST http://localhost:5000/api/v1/verify ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: alpha-bank-api-key" ^
  -H "X-User-Id: ab_ops_01" ^
  -H "X-Forwarded-For: 127.0.0.1" ^
  -d "{\"client_ref_id\":\"ALB-2026-000123\",\"id_type\":\"BAD\",\"id_number\":\"ABCDE1234F\",\"name\":\"Rahul Sharma\"}"
```

## MIS Usage

```bash
curl "http://localhost:5000/api/v1/mis/usage?from=2026-07-01&to=2026-07-17&group_by=client" ^
  -H "X-Admin-Key: admin123"
```

## MIS Usage CSV

```bash
curl "http://localhost:5000/api/v1/mis/usage?from=2026-07-01&to=2026-07-17&group_by=client&format=csv" ^
  -H "X-Admin-Key: admin123"
```

## MIS Errors

```bash
curl "http://localhost:5000/api/v1/mis/errors?from=2026-07-01&to=2026-07-17" ^
  -H "X-Admin-Key: admin123"
```

## MIS TPS

```bash
curl "http://localhost:5000/api/v1/mis/tps?client_id=alphabank&date=2026-07-17" ^
  -H "X-Admin-Key: admin123"
```

## MIS Fallback

```bash
curl "http://localhost:5000/api/v1/mis/fallback?from=2026-07-01&to=2026-07-17" ^
  -H "X-Admin-Key: admin123"
```

## MIS IP Report

```bash
curl "http://localhost:5000/api/v1/mis/ips?client_id=alphabank&from=2026-07-01&to=2026-07-17" ^
  -H "X-Admin-Key: admin123"
```

## Missing Admin Key

```bash
curl "http://localhost:5000/api/v1/mis/usage?from=2026-07-01&to=2026-07-17"
```
