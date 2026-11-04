# Creates TEST_ campaigns for UI test: one all-failed, one scheduled (future). Prints ids.
import time, requests
BASE = [l.split('=',1)[1].strip() for l in open('/app/frontend/.env') if l.startswith('REACT_APP_BACKEND_URL=')][0].rstrip('/')
t = requests.post(f"{BASE}/api/auth/login", json={"email":"qatest@example.com","password":"Test@12345"}).json()["token"]
h = {"Authorization": f"Bearer {t}"}
def send(name, extra):
    body = {"recipients":[{"phone":"9876500011","name":"TEST_a"},{"phone":"9876500012","name":"TEST_b"}],
            "templateName":"hello_world","campaignName":name,"countryCode":"91", **extra}
    d = requests.post(f"{BASE}/api/messages/send", headers=h, json=body).json()
    return d.get("campaignId") or d.get("id")
f = send("TEST_ui_failed", {})
s = send("TEST_ui_scheduled", {"scheduledAt": "2027-01-01T10:00:00Z"})
for _ in range(20):
    c = requests.get(f"{BASE}/api/campaigns/{f}/lite", headers=h).json()
    if c["status"] not in ("processing","pending"): break
    time.sleep(2)
print("FAILED", f, c["status"], c.get("failedCount"))
print("SCHED", s, requests.get(f"{BASE}/api/campaigns/{s}/lite", headers=h).json()["status"])
print("TOKEN", t)
