"""Feature: rename document header to each contact's name (document_name_from_contact).

Covers: _build_payload unit tests, /send single-shot flow, chunked init->recipients->start flow,
saved-templates persistence (create/update/get).
"""
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests
from dotenv import dotenv_values

sys.path.insert(0, "/app/backend")

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")).rstrip("/")
QA_EMAIL = "qatest@example.com"
QA_PASSWORD = "Test@12345"
DOC_URL = "https://example.com/files/price-list.pdf"


def future_iso():
    return datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat()


# ---------- Unit tests: payload builder ----------
from routes.messages import _build_payload, _document_name_for_contact  # noqa: E402


def _rec(name, **kw):
    d = {"name": name, "header_document": DOC_URL, "header_document_name": "Price List.pdf",
         "document_name_from_contact": True}
    d.update(kw)
    return d


class TestPayloadUnit:
    def test_rename_to_contact_name(self):
        p = _build_payload("+919000000001", "tpl", _rec("Ravi Kumar"))
        assert p["header_document_name"] == "Ravi Kumar.pdf"
        assert "document_name_from_contact" not in p
        assert p["header_document"] == DOC_URL

    def test_empty_name_keeps_original(self):
        for n in ["", None, "   ", "///"]:
            p = _build_payload("919000000001", "tpl", _rec(n))
            assert p["header_document_name"] == "Price List.pdf", n
            assert "document_name_from_contact" not in p

    def test_illegal_chars_removed(self):
        p = _build_payload("919000000001", "tpl", _rec('Ra/vi\\ K:u*m?a"r<>|'))
        assert p["header_document_name"] == "Ravi Kumar.pdf"

    def test_flag_off_keeps_original(self):
        p = _build_payload("919000000001", "tpl", _rec("Ravi Kumar", document_name_from_contact=False))
        assert p["header_document_name"] == "Price List.pdf"
        assert "document_name_from_contact" not in p

    def test_ext_kept_docx_and_from_url(self):
        p = _build_payload("919000000001", "tpl", _rec("Ravi", header_document_name="Offer.DOCX"))
        assert p["header_document_name"] == "Ravi.docx"
        p2 = _build_payload("919000000001", "tpl",
                            _rec("Ravi", header_document="https://x.com/a/b.xlsx?sig=1", header_document_name=None))
        assert p2["header_document_name"] == "Ravi.xlsx"

    def test_no_document_no_effect(self):
        p = _build_payload("919000000001", "tpl",
                           {"name": "Ravi", "header_image": "https://x/i.jpg", "document_name_from_contact": True})
        assert "header_document_name" not in p
        assert "document_name_from_contact" not in p

    def test_helper_direct(self):
        assert _document_name_for_contact("  Ravi   Kumar. ", "a.pdf", DOC_URL) == "Ravi Kumar.pdf"
        assert _document_name_for_contact("", "a.pdf", DOC_URL) is None


# ---------- API fixtures ----------
@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    s.headers.update({"Authorization": f"Bearer {r.json().get('token') or r.json().get('access_token')}"})
    return s


@pytest.fixture(scope="module")
def created(client):
    data = {"campaigns": [], "templates": []}
    yield data
    for cid in data["campaigns"]:
        client.post(f"{BASE_URL}/api/campaigns/{cid}/cancel", timeout=30)
        client.delete(f"{BASE_URL}/api/campaigns/{cid}", timeout=30)
    for tid in data["templates"]:
        client.delete(f"{BASE_URL}/api/saved-templates/{tid}", timeout=30)


def send_body(name, flag, **extra):
    b = {
        "campaignName": name, "templateName": "test_template", "countryCode": "91",
        "recipients": [{"phone": "9000000001", "name": "Ravi Kumar"}, {"phone": "9000000002", "name": ""}],
        "scheduledAt": future_iso(),
        "header_document": DOC_URL, "header_document_name": "Price List.pdf",
        "document_name_from_contact": flag,
    }
    b.update(extra)
    return b


def get_recipients(client, cid):
    r = client.get(f"{BASE_URL}/api/campaigns/{cid}", timeout=30)
    assert r.status_code == 200, r.text[:300]
    return r.json()["recipients"]


# ---------- Single-shot /send ----------
class TestSendFlow:
    def test_send_flag_on(self, client, created):
        r = client.post(f"{BASE_URL}/api/messages/send", json=send_body("TEST_docname_on", True), timeout=60)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created["campaigns"].append(cid)
        recs = get_recipients(client, cid)
        assert len(recs) == 2
        for rec in recs:
            assert rec.get("document_name_from_contact") is True
            assert rec["header_document"] == DOC_URL
            assert rec["header_document_name"] == "Price List.pdf"
        p = _build_payload(recs[0]["phone"], "test_template", recs[0])
        assert p["header_document_name"] == "Ravi Kumar.pdf"
        p2 = _build_payload(recs[1]["phone"], "test_template", recs[1])
        assert p2["header_document_name"] == "Price List.pdf"

    def test_send_flag_off(self, client, created):
        r = client.post(f"{BASE_URL}/api/messages/send", json=send_body("TEST_docname_off", False), timeout=60)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created["campaigns"].append(cid)
        for rec in get_recipients(client, cid):
            assert "document_name_from_contact" not in rec
            assert rec["header_document_name"] == "Price List.pdf"


# ---------- Chunked flow ----------
class TestChunkedFlow:
    def _run(self, client, created, flag):
        body = send_body(f"TEST_docname_chunk_{flag}", flag, recipients=[], totalCount=2)
        r = client.post(f"{BASE_URL}/api/messages/campaigns/init", json=body, timeout=60)
        assert r.status_code == 200, r.text[:300]
        cid = r.json()["campaignId"]
        created["campaigns"].append(cid)
        cr = client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/recipients",
                         json={"recipients": [{"phone": "9000000001", "name": "Ravi Kumar"},
                                              {"phone": "9000000002", "name": "Sita"}]}, timeout=60)
        assert cr.status_code == 200 and cr.json()["added"] == 2, cr.text[:300]
        sr = client.post(f"{BASE_URL}/api/messages/campaigns/{cid}/start", timeout=60)
        assert sr.status_code == 200, sr.text[:300]
        assert sr.json()["status"] == "scheduled"
        return get_recipients(client, cid)

    def test_chunked_flag_on(self, client, created):
        recs = self._run(client, created, True)
        assert all(r.get("document_name_from_contact") is True for r in recs)
        assert all(r.get("header_document_name") == "Price List.pdf" for r in recs)
        assert _build_payload(recs[1]["phone"], "t", recs[1])["header_document_name"] == "Sita.pdf"

    def test_chunked_flag_off(self, client, created):
        recs = self._run(client, created, False)
        assert all("document_name_from_contact" not in r for r in recs)


# ---------- Saved templates ----------
class TestSavedTemplates:
    def test_create_update_persist(self, client, created):
        name = f"TEST_docname_tpl_{uuid.uuid4().hex[:6]}"
        body = {"name": name, "templateName": "test_template", "header_document": DOC_URL,
                "header_document_name": "Price List.pdf", "document_name_from_contact": True}
        r = client.post(f"{BASE_URL}/api/saved-templates", json=body, timeout=30)
        assert r.status_code == 200, r.text[:300]
        tid = r.json()["templateId"]
        created["templates"].append(tid)
        g = client.get(f"{BASE_URL}/api/saved-templates/{tid}", timeout=30).json()
        assert g["document_name_from_contact"] is True
        lst = client.get(f"{BASE_URL}/api/saved-templates", timeout=30).json()["templates"]
        assert any(t["id"] == tid and t["document_name_from_contact"] is True for t in lst)
        body["document_name_from_contact"] = False
        u = client.put(f"{BASE_URL}/api/saved-templates/{tid}", json=body, timeout=30)
        assert u.status_code == 200
        g2 = client.get(f"{BASE_URL}/api/saved-templates/{tid}", timeout=30).json()
        assert g2["document_name_from_contact"] is False
        assert g2["header_document_name"] == "Price List.pdf"

    def test_default_false(self, client, created):
        name = f"TEST_docname_tpl_def_{uuid.uuid4().hex[:6]}"
        r = client.post(f"{BASE_URL}/api/saved-templates", json={"name": name, "templateName": "test_template"}, timeout=30)
        assert r.status_code == 200
        tid = r.json()["templateId"]
        created["templates"].append(tid)
        g = client.get(f"{BASE_URL}/api/saved-templates/{tid}", timeout=30).json()
        assert g["document_name_from_contact"] is False
