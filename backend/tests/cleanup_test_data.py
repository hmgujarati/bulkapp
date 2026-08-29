import requests
from dotenv import dotenv_values
BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
s = requests.Session()
r = s.post(f"{BASE}/auth/login", json={"email": "qatest@example.com", "password": "Test@12345"})
tok = r.json().get("token") or r.json().get("access_token")
s.headers.update({"Authorization": f"Bearer {tok}"})
data = s.get(f"{BASE}/campaigns").json()
items = data if isinstance(data, list) else data.get("campaigns", [])
for c in items:
    if str(c.get("name", "")).startswith("TEST_"):
        d = s.delete(f"{BASE}/campaigns/{c['id']}")
        print("del campaign", c["name"], d.status_code)
tpls = s.get(f"{BASE}/saved-templates").json()
tpls = tpls if isinstance(tpls, list) else tpls.get("templates", [])
for t in tpls:
    if str(t.get("name", "")).startswith("TEST_"):
        d = s.delete(f"{BASE}/saved-templates/{t['id']}")
        print("del template", t["name"], d.status_code)
