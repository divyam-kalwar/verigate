"""Integration tests for the core VeriGate assignment flows."""

import csv
import io
from datetime import datetime, timezone

import pytest

from verigate.app import create_app
from verigate.database.mongo import get_client, get_db
from verigate.scripts.seed_data import CLIENTS, USERS
from verigate.services.vendor_service import VendorA, VendorB, VendorService


class TestConfig:
    SECRET_KEY = "test-secret"
    MONGO_URI = "mongodb://localhost:27017"
    DATABASE_NAME = "verigate_pytest"
    ADMIN_KEY = "test-admin-key"
    VENDOR_A_FAILURE_RATE = 0.0
    VENDOR_A_TIMEOUT_RATE = 0.0
    VENDOR_MIN_LATENCY_MS = 1
    VENDOR_MAX_LATENCY_MS = 1
    VENDOR_B_FAILURE_RATE = 0.0

    def to_mapping(self) -> dict:
        return {
            "SECRET_KEY": self.SECRET_KEY,
            "MONGO_URI": self.MONGO_URI,
            "DATABASE_NAME": self.DATABASE_NAME,
            "ADMIN_KEY": self.ADMIN_KEY,
            "VENDOR_A_FAILURE_RATE": self.VENDOR_A_FAILURE_RATE,
            "VENDOR_A_TIMEOUT_RATE": self.VENDOR_A_TIMEOUT_RATE,
            "VENDOR_MIN_LATENCY_MS": self.VENDOR_MIN_LATENCY_MS,
            "VENDOR_MAX_LATENCY_MS": self.VENDOR_MAX_LATENCY_MS,
            "VENDOR_B_FAILURE_RATE": self.VENDOR_B_FAILURE_RATE,
        }


@pytest.fixture()
def app():
    test_app = create_app(TestConfig())
    test_app.config.update(TESTING=True)

    with test_app.app_context():
        db = get_db()
        db["clients"].delete_many({})
        db["users"].delete_many({})
        db["api_logs"].delete_many({})
        db["clients"].insert_many(CLIENTS)
        db["users"].insert_many(USERS)

    yield test_app

    with test_app.app_context():
        get_client().drop_database(TestConfig.DATABASE_NAME)


@pytest.fixture()
def client(app):
    return app.test_client()


def valid_payload() -> dict:
    return {
        "client_ref_id": "ALB-2026-000123",
        "id_type": "PAN",
        "id_number": "ABCDE1234F",
        "name": "Rahul Sharma",
    }


def auth_headers(
    api_key: str = "alpha-bank-api-key",
    user_id: str = "ab_ops_01",
    ip: str = "127.0.0.1",
) -> dict:
    return {
        "X-API-Key": api_key,
        "X-User-Id": user_id,
        "X-Forwarded-For": ip,
    }


def test_invalid_api_key_returns_vp4001(client):
    response = client.post(
        "/api/v1/verify",
        headers=auth_headers(api_key="bad-api-key"),
        json=valid_payload(),
    )

    assert response.status_code == 401
    assert response.get_json()["error_code"] == "VP4001"


def test_non_whitelisted_ip_returns_vp4003(client):
    response = client.post(
        "/api/v1/verify",
        headers=auth_headers(ip="8.8.8.8"),
        json=valid_payload(),
    )

    assert response.status_code == 403
    assert response.get_json()["error_code"] == "VP4003"


def test_payload_validation_returns_vp4022(client):
    payload = valid_payload()
    payload.pop("id_number")

    response = client.post(
        "/api/v1/verify",
        headers=auth_headers(),
        json=payload,
    )

    assert response.status_code == 422
    assert response.get_json()["error_code"] == "VP4022"


def test_tps_limit_returns_vp4029(client):
    headers = auth_headers(
        api_key="nova-hr-api-key",
        user_id="nh_ops_01",
        ip="127.0.0.1",
    )

    responses = [
        client.post("/api/v1/verify", headers=headers, json=valid_payload())
        for _ in range(4)
    ]

    assert [response.status_code for response in responses[:3]] == [200, 200, 200]
    assert responses[3].status_code == 429
    assert responses[3].get_json()["error_code"] == "VP4029"


def test_vendor_fallback_returns_vp2001(app, client):
    app.extensions["vendor_service"] = VendorService(
        vendor_a=VendorA(
            failure_rate=1.0,
            timeout_rate=0.0,
            min_latency_ms=1,
            max_latency_ms=1,
        ),
        vendor_b=VendorB(
            failure_rate=0.0,
            min_latency_ms=1,
            max_latency_ms=1,
        ),
    )

    response = client.post(
        "/api/v1/verify",
        headers=auth_headers(),
        json=valid_payload(),
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["error_code"] == "VP2001"
    assert body["data"]["source"] == "FALLBACK"


def test_mis_usage_aggregation_counts_success_and_failures(app, client):
    with app.app_context():
        get_db()["api_logs"].insert_many(
            [
                {
                    "request_id": "req_success_primary",
                    "client_id": "alphabank",
                    "user_id": "ab_ops_01",
                    "ip": "127.0.0.1",
                    "endpoint": "/api/v1/verify",
                    "id_type": "PAN",
                    "http_status": 200,
                    "error_code": "VP2000",
                    "vendor_used": "PRIMARY",
                    "fallback_used": False,
                    "latency_ms": 100,
                    "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
                },
                {
                    "request_id": "req_success_fallback",
                    "client_id": "alphabank",
                    "user_id": "ab_ops_01",
                    "ip": "127.0.0.1",
                    "endpoint": "/api/v1/verify",
                    "id_type": "PAN",
                    "http_status": 200,
                    "error_code": "VP2001",
                    "vendor_used": "FALLBACK",
                    "fallback_used": True,
                    "latency_ms": 200,
                    "created_at": datetime(2026, 7, 17, 10, 0, 1, tzinfo=timezone.utc),
                },
                {
                    "request_id": "req_failed",
                    "client_id": "alphabank",
                    "user_id": "ab_ops_01",
                    "ip": "8.8.8.8",
                    "endpoint": "/api/v1/verify",
                    "id_type": "PAN",
                    "http_status": 403,
                    "error_code": "VP4003",
                    "vendor_used": None,
                    "fallback_used": False,
                    "latency_ms": 0,
                    "created_at": datetime(2026, 7, 17, 10, 0, 2, tzinfo=timezone.utc),
                },
            ]
        )

    response = client.get(
        "/api/v1/mis/usage?client_id=alphabank&from=2026-07-17&to=2026-07-17",
        headers={"X-Admin-Key": TestConfig.ADMIN_KEY},
    )

    assert response.status_code == 200
    [row] = response.get_json()
    assert row["total"] == 3
    assert row["success"] == 2
    assert row["success_via_fallback"] == 1
    assert row["failed"] == 1


def _parse_csv(response_text: str):
    return list(csv.DictReader(io.StringIO(response_text)))


def _seed_logs(app, logs):
    with app.app_context():
        get_db()["api_logs"].insert_many(logs)


def test_usage_export_returns_csv(client):
    _seed_logs(
        client.application,
        [
            {
                "request_id": "req_1",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 200,
                "error_code": "VP2000",
                "vendor_used": "PRIMARY",
                "fallback_used": False,
                "latency_ms": 100,
                "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
            },
            {
                "request_id": "req_2",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 200,
                "error_code": "VP2001",
                "vendor_used": "FALLBACK",
                "fallback_used": True,
                "latency_ms": 200,
                "created_at": datetime(2026, 7, 17, 10, 0, 1, tzinfo=timezone.utc),
            },
        ],
    )

    response = client.get(
        "/api/v1/mis/usage/export?client_id=alphabank&from=2026-07-17&to=2026-07-17",
        headers={"X-Admin-Key": TestConfig.ADMIN_KEY},
    )

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "usage_report.csv" in response.headers.get("Content-Disposition", "")
    rows = _parse_csv(response.data.decode())
    assert len(rows) == 1
    assert rows[0]["client_id"] == "alphabank"
    assert rows[0]["total"] == "2"
    assert rows[0]["success"] == "2"
    assert rows[0]["success_via_fallback"] == "1"
    assert rows[0]["failed"] == "0"


def test_errors_export_returns_csv(client):
    _seed_logs(
        client.application,
        [
            {
                "request_id": "req_3",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 403,
                "error_code": "VP4003",
                "vendor_used": None,
                "fallback_used": False,
                "latency_ms": 0,
                "created_at": datetime(2026, 7, 17, 10, 0, 2, tzinfo=timezone.utc),
            },
            {
                "request_id": "req_4",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 403,
                "error_code": "VP4003",
                "vendor_used": None,
                "fallback_used": False,
                "latency_ms": 0,
                "created_at": datetime(2026, 7, 17, 10, 0, 3, tzinfo=timezone.utc),
            },
        ],
    )

    response = client.get(
        "/api/v1/mis/errors/export?client_id=alphabank&from=2026-07-17&to=2026-07-17",
        headers={"X-Admin-Key": TestConfig.ADMIN_KEY},
    )

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "error_distribution.csv" in response.headers.get("Content-Disposition", "")
    rows = _parse_csv(response.data.decode())
    assert len(rows) == 1
    assert rows[0]["client_id"] == "alphabank"
    assert rows[0]["error_code"] == "VP4003"
    assert rows[0]["count"] == "2"


def test_tps_export_returns_csv(client):
    _seed_logs(
        client.application,
        [
            {
                "request_id": "req_5",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 200,
                "error_code": "VP2000",
                "vendor_used": "PRIMARY",
                "fallback_used": False,
                "latency_ms": 100,
                "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
            },
            {
                "request_id": "req_6",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 200,
                "error_code": "VP2000",
                "vendor_used": "PRIMARY",
                "fallback_used": False,
                "latency_ms": 150,
                "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
            },
        ],
    )

    response = client.get(
        "/api/v1/mis/tps/export?client_id=alphabank&date=2026-07-17",
        headers={"X-Admin-Key": TestConfig.ADMIN_KEY},
    )

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "tps_report.csv" in response.headers.get("Content-Disposition", "")
    rows = _parse_csv(response.data.decode())
    assert len(rows) == 1
    assert rows[0]["client_id"] == "alphabank"
    assert int(rows[0]["peak_tps"]) == 2
    assert rows[0]["peak_second"] == "2026-07-17T10:00:00Z"


def test_fallback_export_returns_csv(client):
    _seed_logs(
        client.application,
        [
            {
                "request_id": "req_7",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 200,
                "error_code": "VP2001",
                "vendor_used": "FALLBACK",
                "fallback_used": True,
                "latency_ms": 200,
                "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
            },
            {
                "request_id": "req_8",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 200,
                "error_code": "VP2000",
                "vendor_used": "PRIMARY",
                "fallback_used": False,
                "latency_ms": 100,
                "created_at": datetime(2026, 7, 17, 10, 0, 1, tzinfo=timezone.utc),
            },
        ],
    )

    response = client.get(
        "/api/v1/mis/fallback/export?client_id=alphabank&from=2026-07-17&to=2026-07-17",
        headers={"X-Admin-Key": TestConfig.ADMIN_KEY},
    )

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "fallback_report.csv" in response.headers.get("Content-Disposition", "")
    rows = _parse_csv(response.data.decode())
    assert len(rows) == 1
    assert rows[0]["client_id"] == "alphabank"
    assert rows[0]["total_success"] == "2"
    assert rows[0]["served_by_fallback"] == "1"
    assert rows[0]["fallback_ratio_pct"] == "50.0"


def test_ips_export_returns_csv(client):
    _seed_logs(
        client.application,
        [
            {
                "request_id": "req_9",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "127.0.0.1",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 200,
                "error_code": "VP2000",
                "vendor_used": "PRIMARY",
                "fallback_used": False,
                "latency_ms": 100,
                "created_at": datetime(2026, 7, 17, 10, 0, 0, tzinfo=timezone.utc),
            },
            {
                "request_id": "req_10",
                "client_id": "alphabank",
                "user_id": "ab_ops_01",
                "ip": "8.8.8.8",
                "endpoint": "/api/v1/verify",
                "id_type": "PAN",
                "http_status": 403,
                "error_code": "VP4003",
                "vendor_used": None,
                "fallback_used": False,
                "latency_ms": 0,
                "created_at": datetime(2026, 7, 17, 10, 0, 1, tzinfo=timezone.utc),
            },
        ],
    )

    response = client.get(
        "/api/v1/mis/ips/export?client_id=alphabank&from=2026-07-17&to=2026-07-17",
        headers={"X-Admin-Key": TestConfig.ADMIN_KEY},
    )

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "ip_report.csv" in response.headers.get("Content-Disposition", "")
    rows = _parse_csv(response.data.decode())
    assert len(rows) == 2
    alphabank_rows = [r for r in rows if r["ip"] == "127.0.0.1"]
    blocked_rows = [r for r in rows if r["ip"] == "8.8.8.8"]
    assert len(alphabank_rows) == 1
    assert alphabank_rows[0]["total_hits"] == "1"
    assert alphabank_rows[0]["blocked_hits"] == "0"
    assert alphabank_rows[0]["whitelisted"] == "True"
    assert len(blocked_rows) == 1
    assert blocked_rows[0]["total_hits"] == "1"
    assert blocked_rows[0]["blocked_hits"] == "1"
    assert blocked_rows[0]["whitelisted"] == "False"


def test_export_empty_result_returns_only_headers(client):
    response = client.get(
        "/api/v1/mis/usage/export?client_id=alphabank&from=2099-01-01&to=2099-01-02",
        headers={"X-Admin-Key": TestConfig.ADMIN_KEY},
    )

    assert response.status_code == 200
    assert response.content_type == "text/csv"
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "usage_report.csv" in response.headers.get("Content-Disposition", "")
    rows = _parse_csv(response.data.decode())
    assert len(rows) == 0
    assert "client_id" in response.data.decode()
    assert "total" in response.data.decode()
