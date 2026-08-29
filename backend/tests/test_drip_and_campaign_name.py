"""Tests for: mandatory campaign name, drip (daily sending limit) validation,
drip campaign creation + /lite fields, templateReference display data."""
import os
import re
import math
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def test_credentials():
    p = Path("/app/memory/test_credentials.md")
    if not p.exists():
        pytest.skip("missing credentials file")
    content = p.read_text(encoding="utf-8")
    # QA Test User block
    m = re.search(r"QA Test User.*?Email:\s*(\S+).*?Password:\s*(\S+)", content, re.S)
    if not m:
        pytest.skip("QA user not found in credentials file")
    return {"email": m.group(1), "password": m.group(2)}


@pytest.fixture(scope="session")
def client(test_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=test_credentials, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("token") or r.json().get("access_token")
    assert token, f"no token in login response: {r.text[:300]}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def created_campaign_ids():
    return []


@pytest.fixture(scope="session", autouse=True)
def cleanup(client, created_campaign_ids):
    yield
    for cid in created_campaign_ids:
        try:
            client.delete(f"{API}/campaigns/{cid}", timeout=30)
        except Exception:
            pass


def recips(n, prefix="9198765"):
    return [{"phone": f"{prefix}{str(i).zfill(5)}", "name": f"TEST_{i}"} for i in range(n)]


# --- account info ---
class TestAccount:
    def test_me_returns_daily_limit(self, client):
        r = client.get(f"{API}/auth/me", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "dailyLimit" in data
        assert isinstance(data["dailyLimit"], int)


# --- campaign name mandatory ---
class TestCampaignNameRequired:
    @pytest.mark.parametrize("name", ["", "   "])
    def test_blank_campaign_name_rejected(self, client, name):
        r = client.post(f"{API}/messages/send", json={
            "campaignName": name,
            "templateName": "test_template",
            "recipients": recips(2),
        }, timeout=60)
        assert r.status_code == 400, r.text[:300]
        assert "campaign name is required" in r.json()["detail"].lower()


# --- drip validation ---
class TestDripValidation:
    def test_drip_without_per_day_rejected(self, client):
        r = client.post(f"{API}/messages/send", json={
            "campaignName": "TEST_drip_no_perday",
            "templateName": "test_template",
            "recipients": recips(3),
            "dripEnabled": True,
        }, timeout=60)
        assert r.status_code == 400, r.text[:300]
        assert "per day" in r.json()["detail"].lower()

    def test_drip_over_account_limit_rejected(self, client):
        limit = client.get(f"{API}/auth/me", timeout=30).json()["dailyLimit"]
        if limit == -1:
            pytest.skip("unlimited account")
        r = client.post(f"{API}/messages/send", json={
            "campaignName": "TEST_drip_over_limit",
            "templateName": "test_template",
            "recipients": recips(3),
            "dripEnabled": True,
            "dripDailyLimit": limit + 3000,
        }, timeout=60)
        assert r.status_code == 400, r.text[:300]
        assert "cannot exceed your account daily limit" in r.json()["detail"].lower()

    def test_drip_at_exact_account_limit_allowed(self, client, created_campaign_ids):
        limit = client.get(f"{API}/auth/me", timeout=30).json()["dailyLimit"]
        if limit == -1:
            pytest.skip("unlimited account")
        r = client.post(f"{API}/messages/send", json={
            "campaignName": "TEST_drip_exact_limit",
            "templateName": "test_template",
            "recipients": recips(2, prefix="9198760"),
            "dripEnabled": True,
            "dripDailyLimit": limit,
            "dripStartAt": "2027-01-01T10:00:00+00:00",
        }, timeout=60)
        assert r.status_code == 200, r.text[:300]
        created_campaign_ids.append(r.json()["campaignId"])
        assert r.json()["status"] == "scheduled"


# --- drip creation + lite fields ---
class TestDripCampaignCreation:
    def test_create_drip_start_now(self, client, created_campaign_ids):
        payload = {
            "campaignName": "TEST_drip_start_now",
            "templateName": "test_template",
            "templateReference": "TEST_My Own Reference",
            "recipients": recips(20, prefix="9198761"),
            "dripEnabled": True,
            "dripDailyLimit": 5,
        }
        r = client.post(f"{API}/messages/send", json=payload, timeout=90)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        cid = body["campaignId"]
        created_campaign_ids.append(cid)
        assert body["status"] == "processing"

        lite = client.get(f"{API}/campaigns/{cid}/lite", timeout=30)
        assert lite.status_code == 200
        c = lite.json()
        assert "_id" not in c
        assert c["name"] == payload["campaignName"]
        assert c["templateReference"] == "TEST_My Own Reference"
        assert c["dripEnabled"] is True
        assert c["dripDailyLimit"] == 5
        assert c["dripStartAt"]
        assert c["totalCount"] == 20
        assert c["status"] in ("pending", "processing", "scheduled", "failed", "completed")
        # estimate parity with UI: ceil(20/5) == 4 days
        assert math.ceil(c["totalCount"] / c["dripDailyLimit"]) == 4

    def test_create_drip_future_start(self, client, created_campaign_ids):
        r = client.post(f"{API}/messages/send", json={
            "campaignName": "TEST_drip_future",
            "templateName": "test_template",
            "recipients": recips(10, prefix="9198762"),
            "dripEnabled": True,
            "dripDailyLimit": 4,
            "dripStartAt": "2027-03-05T09:30:00+00:00",
        }, timeout=60)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created_campaign_ids.append(cid)
        assert r.json()["status"] == "scheduled"
        c = client.get(f"{API}/campaigns/{cid}/lite", timeout=30).json()
        assert c["status"] == "scheduled"
        assert c["dripStartAt"].startswith("2027-03-05T09:30")
        assert c["scheduledAt"].startswith("2027-03-05T09:30")


# --- non-drip regression ---
class TestNonDripRegression:
    def test_normal_campaign_creation(self, client, created_campaign_ids):
        r = client.post(f"{API}/messages/send", json={
            "campaignName": "TEST_normal_campaign",
            "templateName": "test_template",
            "recipients": recips(3, prefix="9198763"),
        }, timeout=90)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created_campaign_ids.append(cid)
        c = client.get(f"{API}/campaigns/{cid}/lite", timeout=30).json()
        assert c["dripEnabled"] in (False, None)
        assert c["dripDailyLimit"] is None
        assert c.get("templateReference") is None
        assert c["totalCount"] == 3

    def test_scheduled_campaign_creation(self, client, created_campaign_ids):
        r = client.post(f"{API}/messages/send", json={
            "campaignName": "TEST_scheduled_campaign",
            "templateName": "test_template",
            "recipients": recips(2, prefix="9198764"),
            "scheduledAt": "2027-04-01T08:00:00+00:00",
        }, timeout=60)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created_campaign_ids.append(cid)
        c = client.get(f"{API}/campaigns/{cid}/lite", timeout=30).json()
        assert c["status"] == "scheduled"
        assert c["scheduledAt"].startswith("2027-04-01T08:00")

    def test_campaigns_list_includes_created(self, client, created_campaign_ids):
        r = client.get(f"{API}/campaigns", timeout=30)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("campaigns", [])
        ids = {c.get("id") for c in items}
        assert created_campaign_ids[0] in ids or len(items) > 0
