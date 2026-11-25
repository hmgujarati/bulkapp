"""Saved templates field6..field15 + send recipient field_12 passthrough (iteration 13)"""
import os
import sys
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
CREDS = {"email": "qatest@example.com", "password": "Test@12345"}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=CREDS)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    return s


@pytest.fixture(scope="module")
def created():
    data = {"templates": [], "campaigns": []}
    yield data
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=CREDS)
    s.headers.update({"Authorization": f"Bearer {r.json()['token']}"})
    for tid in data["templates"]:
        s.delete(f"{BASE_URL}/api/saved-templates/{tid}")
    for cid in data["campaigns"]:
        s.post(f"{BASE_URL}/api/campaigns/{cid}/cancel")
        s.delete(f"{BASE_URL}/api/campaigns/{cid}")


def _find(client, tid):
    r = client.get(f"{BASE_URL}/api/saved-templates")
    assert r.status_code == 200
    return next((t for t in r.json()["templates"] if t["id"] == tid), None)


# Saved template CRUD with extended fields
class TestSavedTemplateExtendedFields:
    def test_create_with_field6_and_12(self, client, created):
        name = f"TEST_15f_{uuid.uuid4().hex[:6]}"
        r = client.post(f"{BASE_URL}/api/saved-templates", json={
            "name": name, "templateName": "test_tpl", "templateLanguage": "en",
            "field1": "one", "field6": "six", "field12": "twelve"})
        assert r.status_code == 200, r.text
        tid = r.json()["templateId"]
        created["templates"].append(tid)
        t = _find(client, tid)
        assert t["field1"] == "one" and t["field6"] == "six" and t["field12"] == "twelve"
        assert t.get("field15") is None
        g = client.get(f"{BASE_URL}/api/saved-templates/{tid}").json()
        assert g["field12"] == "twelve" and "_id" not in g
        created["tid"] = tid
        created["name"] = name

    def test_update_field12_and_15(self, client, created):
        tid = created["tid"]
        r = client.put(f"{BASE_URL}/api/saved-templates/{tid}", json={
            "name": created["name"], "templateName": "test_tpl", "templateLanguage": "en",
            "field1": "one", "field6": "six", "field12": "twelve-upd", "field15": "fifteen"})
        assert r.status_code == 200, r.text
        t = _find(client, tid)
        assert t["field12"] == "twelve-upd" and t["field15"] == "fifteen" and t["field6"] == "six"

    def test_legacy_5_field_template(self, client, created):
        name = f"TEST_5f_{uuid.uuid4().hex[:6]}"
        r = client.post(f"{BASE_URL}/api/saved-templates", json={
            "name": name, "templateName": "t5", "field1": "a", "field5": "e"})
        assert r.status_code == 200
        tid = r.json()["templateId"]
        created["templates"].append(tid)
        r = client.put(f"{BASE_URL}/api/saved-templates/{tid}", json={
            "name": name, "templateName": "t5", "field1": "a2", "field5": "e"})
        assert r.status_code == 200
        t = _find(client, tid)
        assert t["field1"] == "a2" and t["field5"] == "e" and t.get("field6") is None


# /api/messages/send stores field_12 on recipient
class TestSendExtendedFields:
    def test_send_keeps_field_12(self, client, created):
        future = "2030-01-01T10:00:00Z"
        rec = {"phone": "+919000000001", "name": "TEST_r", "template_language": "en",
               "field_1": "a", "field_2": "", "field_3": "", "field_4": "", "field_5": "",
               "field_12": "twelve"}
        r = client.post(f"{BASE_URL}/api/messages/send", json={
            "campaignName": f"TEST_15f_{uuid.uuid4().hex[:6]}", "templateName": "test_tpl",
            "recipients": [rec], "scheduledAt": future, "countryCode": "91"})
        assert r.status_code == 200, r.text
        cid = r.json()["campaignId"]
        created["campaigns"].append(cid)
        c = client.get(f"{BASE_URL}/api/campaigns/{cid}").json()
        assert c["recipients"][0].get("field_12") == "twelve"
        assert c["recipients"][0].get("field_1") == "a"


# Unit: _build_payload forwards field_1..15 non-empty only
def test_build_payload_unit():
    sys.path.insert(0, "/app/backend")
    from routes.messages import _build_payload
    p = _build_payload("+91 9000000001", "t", {
        "name": "Bob", "field_1": "Hi {name}", "field_2": "", "field_12": "x",
        "field_15": "y", "field_16": "no", "status": "pending", "phone": "z"})
    assert p["field_1"] == "Hi Bob"
    assert "field_2" not in p
    assert p["field_12"] == "x" and p["field_15"] == "y"
    assert "field_16" not in p and "status" not in p
    assert p["phone_number"] == "919000000001"
