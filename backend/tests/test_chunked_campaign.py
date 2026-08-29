"""Tests for the chunked campaign creation flow (init -> recipients -> start).

Covers: happy path with 30k recipients, validation/negative cases,
draft campaigns hidden from lists, and the small-list single-request regression.
"""
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

QA_EMAIL = "qatest@example.com"
QA_PASSWORD = "Test@12345"


def future_iso(days=5):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:300]}")
    body = r.json()
    token = body.get("token") or body.get("access_token")
    assert token, f"No token in login response: {body}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def account_limit(client):
    r = client.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json().get("dailyLimit", 1000)


@pytest.fixture(scope="session")
def created_campaigns():
    return []


@pytest.fixture(scope="session", autouse=True)
def cleanup(client, created_campaigns):
    yield
    for cid in created_campaigns:
        try:
            client.post(f"{BASE_URL}/api/campaigns/{cid}/cancel", timeout=30)
            client.delete(f"{BASE_URL}/api/campaigns/{cid}", timeout=30)
        except Exception as e:  # noqa
            print(f"cleanup failed for {cid}: {e}")


def init_payload(name, total, drip_limit=5000, **extra):
    p = {
        "campaignName": name,
        "templateName": "test_template",
        "countryCode": "91",
        "recipients": [],
        "totalCount": total,
        "dripEnabled": True,
        "dripDailyLimit": drip_limit,
        "dripStartAt": future_iso(5),
    }
    p.update(extra)
    return p


# === BUG VERIFICATION: chunked flow with 30k recipients ===
class TestChunkedHappyPath:
    def test_init_chunks_start_30k(self, client, created_campaigns, account_limit):
        drip_limit = 5000 if account_limit == -1 or account_limit >= 5000 else max(1, account_limit)
        payload = init_payload("TEST_chunked_30k", 30000, drip_limit=drip_limit)
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=payload, timeout=60)
        assert r.status_code == 200, f"init failed: {r.status_code} {r.text[:300]}"
        data = r.json()
        cid = data["campaignId"]
        created_campaigns.append(cid)
        assert data["expectedCount"] == 30000

        # draft should be hidden from campaign list
        lst = client.get(f"{BASE_URL}/api/campaigns", timeout=60)
        assert lst.status_code == 200
        items = lst.json()
        items = items.get("campaigns", items) if isinstance(items, dict) else items
        assert cid not in [c.get("id") for c in items], "Draft campaign visible in GET /api/campaigns"

        summary = client.get(f"{BASE_URL}/api/campaigns/summary", timeout=60)
        assert summary.status_code == 200
        recent = summary.json().get("recentCampaigns", [])
        assert cid not in [c.get("id") for c in recent], "Draft campaign visible in summary recentCampaigns"

        max_body = 0
        for chunk in range(30):
            recipients = [
                {"phone": f"98765{(chunk * 1000 + i):05d}", "name": f"TEST_{chunk}_{i}"}
                for i in range(1000)
            ]
            body = json.dumps({"recipients": recipients})
            max_body = max(max_body, len(body.encode()))
            cr = client.post(
                f"{BASE_URL}/api/messages/campaigns/{cid}/recipients",
                data=body, timeout=120,
            )
            assert cr.status_code == 200, f"chunk {chunk} failed: {cr.status_code} {cr.text[:300]}"
            assert cr.json()["added"] == 1000
        print(f"Max chunk request body size: {max_body} bytes")
        assert max_body < 150_000, f"chunk body too large: {max_body}"

        sr = client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/start", timeout=120)
        assert sr.status_code == 200, f"start failed: {sr.status_code} {sr.text[:300]}"
        sd = sr.json()
        assert sd["totalCount"] == 30000
        assert sd["status"] == "scheduled", f"expected scheduled, got {sd}"

        det = client.get(f"{BASE_URL}/api/campaigns/{cid}", timeout=60)
        assert det.status_code == 200
        c = det.json()
        assert c["totalCount"] == 30000
        assert c["pendingCount"] == 30000
        assert c["status"] == "scheduled"
        assert c["name"] == "TEST_chunked_30k"

        # now visible in list
        lst2 = client.get(f"{BASE_URL}/api/campaigns", timeout=60)
        items2 = lst2.json()
        items2 = items2.get("campaigns", items2) if isinstance(items2, dict) else items2
        assert cid in [x.get("id") for x in items2], "Started campaign not in GET /api/campaigns"


# === Validation / negative cases ===
class TestChunkedValidation:
    def test_init_blank_name(self, client):
        p = init_payload("   ", 100)
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=p, timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert "Campaign name is required" in r.text

    def test_init_missing_total_count(self, client):
        p = init_payload("TEST_no_total", 100)
        p.pop("totalCount")
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=p, timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert "totalCount" in r.text

    def test_init_drip_limit_above_account_limit(self, client, account_limit):
        if account_limit == -1:
            pytest.skip("account has unlimited dailyLimit")
        p = init_payload("TEST_drip_over", 100, drip_limit=account_limit + 500)
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=p, timeout=30)
        assert r.status_code == 400, r.text[:300]
        assert "daily limit" in r.text.lower()

    def test_append_after_start_and_start_twice(self, client, created_campaigns, account_limit):
        drip_limit = 10 if account_limit != -1 and account_limit < 10 else 10
        p = init_payload("TEST_append_after_start", 3, drip_limit=drip_limit)
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=p, timeout=30)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created_campaigns.append(cid)

        cr = client.post(
            f"{BASE_URL}/api/messages/campaigns/{cid}/recipients",
            json={"recipients": [{"phone": "9876500001", "name": "TEST_a"}]}, timeout=30)
        assert cr.status_code == 200, cr.text[:300]

        sr = client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/start", timeout=30)
        assert sr.status_code == 200, sr.text[:300]
        assert sr.json()["status"] == "scheduled"

        cr2 = client.post(
            f"{BASE_URL}/api/messages/campaigns/{cid}/recipients",
            json={"recipients": [{"phone": "9876500002"}]}, timeout=30)
        assert cr2.status_code == 400, cr2.text[:300]
        assert "Campaign already started" in cr2.text

        sr2 = client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/start", timeout=30)
        assert sr2.status_code == 400
        assert "Campaign already started" in sr2.text

    def test_start_with_zero_recipients(self, client, created_campaigns):
        p = init_payload("TEST_zero_recipients", 10, drip_limit=10)
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=p, timeout=30)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created_campaigns.append(cid)
        sr = client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/start", timeout=30)
        assert sr.status_code == 400, sr.text[:300]
        assert "No recipients were uploaded" in sr.text

    def test_other_users_campaign_404(self, client):
        bogus = "00000000-0000-0000-0000-0000000000ff"
        r1 = client.post(
            f"{BASE_URL}/api/messages/campaigns/{bogus}/recipients",
            json={"recipients": [{"phone": "9876500003"}]}, timeout=30)
        assert r1.status_code == 404, r1.text[:300]
        r2 = client.post(f"{BASE_URL}/api/messages/campaigns/{bogus}/start", timeout=30)
        assert r2.status_code == 404, r2.text[:300]

    def test_unauthenticated_rejected(self):
        r = requests.post(f"{BASE_URL}/api/messages/campaigns/init", json=init_payload("TEST_noauth", 5), timeout=30)
        assert r.status_code in (401, 403), f"unauth got {r.status_code}"


# === Regression: single-request path for small lists ===
class TestSingleRequestRegression:
    def test_send_50_recipients_normalizes_phone(self, client, created_campaigns):
        recipients = [{"phone": "9876543210", "name": "TEST_first"}]
        recipients += [{"phone": f"98765{40000 + i:05d}", "name": f"TEST_{i}"} for i in range(49)]
        payload = {
            "campaignName": "TEST_small_single_request",
            "templateName": "test_template",
            "countryCode": "91",
            "recipients": recipients,
        }
        r = client.post(f"{BASE_URL}/api/messages/send", json=payload, timeout=60)
        assert r.status_code == 200, f"send failed {r.status_code}: {r.text[:300]}"
        d = r.json()
        cid = d["campaignId"]
        created_campaigns.append(cid)
        assert d["status"] == "processing"

        # pause quickly to limit dispatch attempts with the dummy token
        client.post(f"{BASE_URL}/api/campaigns/{cid}/pause", timeout=30)

        det = client.get(f"{BASE_URL}/api/campaigns/{cid}", timeout=60)
        assert det.status_code == 200
        c = det.json()
        assert c["totalCount"] == 50
        phones = [x["phone"] for x in c["recipients"]]
        assert "+919876543210" in phones, f"phone normalization failed: {phones[:3]}"
        client.post(f"{BASE_URL}/api/campaigns/{cid}/cancel", timeout=30)

    def test_send_blank_name_rejected(self, client):
        payload = {
            "campaignName": "",
            "templateName": "test_template",
            "countryCode": "91",
            "recipients": [{"phone": "9876500009"}],
        }
        r = client.post(f"{BASE_URL}/api/messages/send", json=payload, timeout=30)
        assert r.status_code == 400
        assert "Campaign name is required" in r.text


# === Regression: drip fields, templateReference, phone normalization, /lite on chunked path ===
class TestChunkedPersistence:
    def test_chunked_persists_drip_template_and_phones(self, client, created_campaigns, account_limit):
        drip_limit = 2000 if account_limit == -1 or account_limit >= 2000 else max(1, account_limit)
        start_at = future_iso(3)
        payload = init_payload(
            "TEST_chunked_persist", 3000, drip_limit=drip_limit,
            templateReference="REF-CHUNK-001",
        )
        payload["dripStartAt"] = start_at
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=payload, timeout=60)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created_campaigns.append(cid)

        for chunk in range(3):
            recipients = [
                {"phone": f"98761{(chunk * 1000 + i):05d}", "name": f"TEST_{i}",
                 "field_1": "hello", "template_language": "en_US"}
                for i in range(1000)
            ]
            cr = client.post(
                f"{BASE_URL}/api/messages/campaigns/{cid}/recipients",
                json={"recipients": recipients}, timeout=120)
            assert cr.status_code == 200, cr.text[:300]
            assert cr.json()["added"] == 1000
            assert cr.json()["totalCount"] == (chunk + 1) * 1000

        sr = client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/start", timeout=120)
        assert sr.status_code == 200, sr.text[:300]
        assert sr.json()["status"] == "scheduled"
        assert sr.json()["totalCount"] == 3000

        lite = client.get(f"{BASE_URL}/api/campaigns/{cid}/lite", timeout=60)
        assert lite.status_code == 200, lite.text[:300]
        L = lite.json()
        assert L["totalCount"] == 3000, L
        assert L["pendingCount"] == 3000, L
        assert L["status"] == "scheduled"
        assert L.get("dripEnabled") is True
        assert L.get("dripDailyLimit") == drip_limit
        assert L.get("dripStartAt"), "dripStartAt missing on /lite"
        assert L.get("templateReference") == "REF-CHUNK-001"
        assert "_id" not in json.dumps(L), "MongoDB _id leaked in /lite response"

        rec = client.get(f"{BASE_URL}/api/campaigns/{cid}/recipients?page=1&limit=5", timeout=60)
        assert rec.status_code == 200, rec.text[:300]
        body = rec.json()
        items = body.get("recipients", body) if isinstance(body, dict) else body
        phones = [x["phone"] for x in items]
        assert all(p.startswith("+91") and len(p) == 13 for p in phones), phones
        assert items[0].get("field_1") == "hello"
        assert items[0].get("status") == "pending"

    def test_chunked_campaign_appears_once_in_list(self, client, created_campaigns, account_limit):
        drip_limit = 100 if account_limit == -1 or account_limit >= 100 else max(1, account_limit)
        p = init_payload("TEST_chunked_dup_check", 1500, drip_limit=drip_limit)
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=p, timeout=30)
        cid = r.json()["campaignId"]
        created_campaigns.append(cid)
        client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/recipients",
                    json={"recipients": [{"phone": f"98762{i:05d}"} for i in range(1500)]}, timeout=120)
        client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/start", timeout=60)
        lst = client.get(f"{BASE_URL}/api/campaigns", timeout=60)
        items = lst.json()
        items = items.get("campaigns", items) if isinstance(items, dict) else items
        ids = [c.get("id") for c in items]
        assert ids.count(cid) == 1, f"campaign listed {ids.count(cid)} times"
        assert not any(c.get("status") == "draft" for c in items), "draft campaigns leaked into list"
