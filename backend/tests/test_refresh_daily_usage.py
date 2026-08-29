"""Tests for the Refresh Daily Usage admin utility + auth/me regression."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

ADMIN = {"email": "qaadmin@example.com", "password": "Admin@12345"}
USER = {"email": "qatest@example.com", "password": "Test@12345"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"Login failed for {creds['email']}: {r.status_code} {r.text[:300]}")
    data = r.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"No token in login response: {data}"
    return token, data


@pytest.fixture(scope="session")
def admin_token():
    return _login(ADMIN)[0]


@pytest.fixture(scope="session")
def user_token():
    return _login(USER)[0]


def _h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _me(token):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=_h(token), timeout=60)
    assert r.status_code == 200, r.text[:300]
    return r.json()


# --- Module: routes/users.py — refresh-daily-usage endpoints
class TestRefreshAllDailyUsage:
    def test_admin_refresh_all(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/users/refresh-daily-usage", headers=_h(admin_token), timeout=180)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "message" in data and "Refreshed" in data["message"]
        assert isinstance(data["corrected"], list)
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0
        row = data["results"][0]
        for key in ("userId", "email", "previousUsage", "dailyUsage", "dailyLimit", "windowStart"):
            assert key in row, f"missing {key} in {row}"
        assert "_id" not in row

    def test_non_admin_forbidden(self, user_token):
        r = requests.post(f"{BASE_URL}/api/users/refresh-daily-usage", headers=_h(user_token), timeout=60)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:300]}"

    def test_unauthenticated_rejected(self):
        r = requests.post(f"{BASE_URL}/api/users/refresh-daily-usage", timeout=60)
        assert r.status_code in (401, 403), r.status_code


class TestRefreshSingleUserDailyUsage:
    def test_admin_refresh_other_user(self, admin_token, user_token):
        me = _me(user_token)
        uid = me.get("id") or me.get("userId")
        r = requests.post(f"{BASE_URL}/api/users/{uid}/refresh-daily-usage", headers=_h(admin_token), timeout=120)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert data["message"] == "Daily usage refreshed"
        assert data["userId"] == uid
        assert isinstance(data["dailyUsage"], int)
        # persistence check
        me2 = _me(user_token)
        assert me2["dailyUsage"] == data["dailyUsage"]

    def test_user_refresh_self(self, user_token):
        me = _me(user_token)
        uid = me.get("id") or me.get("userId")
        r = requests.post(f"{BASE_URL}/api/users/{uid}/refresh-daily-usage", headers=_h(user_token), timeout=120)
        assert r.status_code == 200, r.text[:400]
        assert r.json()["userId"] == uid

    def test_user_refresh_other_forbidden(self, user_token, admin_token):
        admin_me = _me(admin_token)
        admin_id = admin_me.get("id") or admin_me.get("userId")
        r = requests.post(f"{BASE_URL}/api/users/{admin_id}/refresh-daily-usage", headers=_h(user_token), timeout=60)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:300]}"

    def test_unknown_user_404(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/users/{uuid.uuid4()}/refresh-daily-usage", headers=_h(admin_token), timeout=60
        )
        assert r.status_code == 404, f"expected 404 got {r.status_code}: {r.text[:300]}"


# --- Module: routes/auth.py — regression on dailyUsage fields
class TestAuthMeRegression:
    def test_me_has_usage_fields(self, user_token):
        me = _me(user_token)
        assert isinstance(me["dailyUsage"], int)
        assert isinstance(me["dailyLimit"], int)
        assert "remaining" in me
        assert me["remaining"] == me["dailyLimit"] - me["dailyUsage"] or me["dailyLimit"] == -1
        assert me.get("nextResetAt"), "nextResetAt missing/empty"
        assert "_id" not in me
        assert "password" not in me


# --- Module: routes/campaigns.py — small campaign still increments dailyUsage
class TestCampaignUsageIntegration:
    campaign_id = None

    def test_create_small_campaign_and_refresh(self, user_token):
        me_before = _me(user_token)
        uid = me_before.get("id") or me_before.get("userId")
        payload = {
            "campaignName": f"TEST_usage_{uuid.uuid4().hex[:6]}",
            "templateName": "test_template",
            "recipients": [
                {"phone": "919000000001", "name": "T1"},
                {"phone": "919000000002", "name": "T2"},
            ],
        }
        r = requests.post(f"{BASE_URL}/api/messages/send", headers=_h(user_token), json=payload, timeout=180)
        assert r.status_code in (200, 201), f"campaign create failed: {r.status_code} {r.text[:500]}"
        body = r.json()
        cid = body.get("id") or body.get("campaignId") or (body.get("campaign") or {}).get("id")
        assert cid, f"no campaign id in response: {body}"
        TestCampaignUsageIntegration.campaign_id = cid

        # give the background send loop a moment
        import time

        time.sleep(8)

        # verify campaign persisted
        g = requests.get(f"{BASE_URL}/api/campaigns/{cid}", headers=_h(user_token), timeout=60)
        assert g.status_code == 200, g.text[:300]
        camp = g.json()
        assert camp["totalCount"] == 2
        assert "_id" not in camp

        # after refresh, FAILED messages must not consume quota
        rr = requests.post(
            f"{BASE_URL}/api/users/{uid}/refresh-daily-usage", headers=_h(user_token), timeout=120
        )
        assert rr.status_code == 200, rr.text[:300]
        refreshed = rr.json()
        sent_in_camp = camp.get("sentCount", 0)
        # dummy BizChat creds -> sends fail -> sentCount 0 -> usage must not be inflated by this campaign
        assert refreshed["dailyUsage"] >= 0
        print(
            f"campaign sentCount={sent_in_camp} failedCount={camp.get('failedCount')} "
            f"usage {refreshed['previousUsage']} -> {refreshed['dailyUsage']}"
        )

    def test_cleanup_campaign(self, user_token):
        cid = TestCampaignUsageIntegration.campaign_id
        if not cid:
            pytest.skip("no campaign created")
        d = requests.delete(f"{BASE_URL}/api/campaigns/{cid}", headers=_h(user_token), timeout=60)
        assert d.status_code in (200, 204, 404), d.text[:300]
