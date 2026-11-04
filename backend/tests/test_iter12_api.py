# Iteration 12: phone normalization via API, refresh-daily-usage regression, retry-failed endpoint
import os, time, pytest, requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    with open('/app/frontend/.env') as f:
        for line in f:
            if line.startswith('REACT_APP_BACKEND_URL='):
                BASE_URL = line.split('=', 1)[1].strip().rstrip('/')


def _login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code}")
    d = r.json()
    return d["token"], d["user"]


@pytest.fixture(scope="module")
def user_h():
    t, u = _login("qatest@example.com", "Test@12345")
    return {"Authorization": f"Bearer {t}"}, u


@pytest.fixture(scope="module")
def admin_h():
    t, u = _login("qaadmin@example.com", "Admin@12345")
    return {"Authorization": f"Bearer {t}"}, u


created = []


@pytest.fixture(scope="module", autouse=True)
def cleanup(user_h):
    yield
    for cid in created:
        requests.delete(f"{BASE_URL}/api/campaigns/{cid}", headers=user_h[0])


def _send(h, recipients, name):
    r = requests.post(f"{BASE_URL}/api/messages/send", headers=h, json={
        "recipients": recipients, "templateName": "hello_world",
        "campaignName": name, "countryCode": "91"})
    assert r.status_code in (200, 201), r.text
    d = r.json()
    cid = d.get("campaignId") or d.get("id") or (d.get("campaign") or {}).get("id")
    assert cid, d
    created.append(cid)
    return cid


# Phone normalization - mixed country list
def test_mixed_country_phones(user_h):
    h = user_h[0]
    cid = _send(h, [{"phone": "9876543210", "name": "TEST_in"},
                    {"phone": "971501234567", "name": "TEST_ae"},
                    {"phone": "15551234567", "name": "TEST_us"},
                    {"phone": "447911123456", "name": "TEST_uk"}], "TEST_mixed_phones")
    r = requests.get(f"{BASE_URL}/api/campaigns/{cid}/recipients", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    recs = d.get("recipients", d) if isinstance(d, dict) else d
    phones = sorted(x["phone"] for x in recs)
    print("stored phones:", phones)
    assert phones == sorted(["+919876543210", "+971501234567", "+15551234567", "+447911123456"])


# Retry failed endpoint on an all-failed campaign (dummy creds)
def test_retry_failed(user_h):
    h = user_h[0]
    cid = _send(h, [{"phone": "9876500001", "name": "TEST_a"},
                    {"phone": "9876500002", "name": "TEST_b"}], "TEST_retry_failed")
    c = None
    for _ in range(30):
        c = requests.get(f"{BASE_URL}/api/campaigns/{cid}/lite", headers=h).json()
        if c.get("status") not in ("processing", "pending"):
            break
        time.sleep(2)
    print("campaign status:", c.get("status"), "failed:", c.get("failedCount"))
    assert c.get("failedCount", 0) > 0
    r = requests.post(f"{BASE_URL}/api/messages/campaigns/{cid}/retry-failed", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["retryCount"] == c["failedCount"]


def test_retry_failed_404(user_h):
    r = requests.post(f"{BASE_URL}/api/messages/campaigns/nonexistent-xyz/retry-failed", headers=user_h[0])
    assert r.status_code == 404


# Regression: refresh daily usage endpoints
def test_refresh_daily_usage_all(admin_h):
    r = requests.post(f"{BASE_URL}/api/users/refresh-daily-usage", headers=admin_h[0])
    assert r.status_code == 200, r.text


def test_refresh_daily_usage_one(admin_h, user_h):
    uid = user_h[1]["id"]
    r = requests.post(f"{BASE_URL}/api/users/{uid}/refresh-daily-usage", headers=admin_h[0])
    assert r.status_code == 200, r.text
