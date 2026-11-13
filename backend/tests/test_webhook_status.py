"""Run: cd /app/backend && python tests/test_webhook_status.py
Webhook status handling against the LIVE backend (/api/webhook/*) + a MOCK BizChat send API."""
import asyncio, uuid, sys, logging
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

import httpx
import uvicorn
from fastapi import FastAPI, Request

logging.basicConfig(level=logging.WARNING)
BACKEND = "http://127.0.0.1:8001"
PORT = 8766
mock = FastAPI()


@mock.post("/api/{vendor}/contact/send-template-message")
async def send(vendor: str, request: Request):
    body = await request.json()
    return {"result": "success", "data": {"wamid": f"wamid.{body['phone_number']}"}}


def recip(phone, status="pending", wamid=None):
    return {"phone": phone, "name": "", "status": status, "sentAt": None, "messageId": wamid,
            "error": None, "retryCount": 0, "template_language": "en_US", "field_1": "hi"}


def bizchat_status(wamid, status, body=None, is_new=False):
    return {"contact": {"phone_number": "91000"}, "message": {
        "whatsapp_message_id": wamid, "status": status, "body": body, "is_new_message": is_new}}


async def main():
    import routes.messages as m
    from utils.database import db
    from services.message_status_service import extract_status_data
    m.BIZCHAT_API_BASE = f"http://127.0.0.1:{PORT}/api"
    server = uvicorn.Server(uvicorn.Config(mock, port=PORT, log_level="warning"))
    srv = asyncio.create_task(server.serve())
    await asyncio.sleep(1)

    ok = True
    def check(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + msg)

    user_id = f"test-user-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({"id": user_id, "email": f"{user_id}@t.local", "dailyUsage": 0, "dailyLimit": -1, "lastResetDateTime": now})
    cids, wamids_b = [], []
    try:
        # --- TEST 1: 20 simultaneous delivered webhooks, then 20 simultaneous read + 20 duplicate delivered
        cid = str(uuid.uuid4()); cids.append(cid)
        wamids = [f"wamid.T1-{uuid.uuid4().hex[:8]}" for _ in range(20)]
        await db.campaigns.insert_one({"id": cid, "userId": user_id, "status": "completed", "templateName": "t",
            "recipients": [recip(f"+9190000{i:05d}", "sent", w) for i, w in enumerate(wamids)],
            "totalCount": 20, "sentCount": 20, "failedCount": 0, "pendingCount": 0, "deliveredCount": 0, "readCount": 0,
            "createdAt": now, "lastHeartbeatAt": now})
        async with httpx.AsyncClient(timeout=30) as c:
            url = f"{BACKEND}/api/webhook/{user_id}"
            await asyncio.gather(*[c.post(url, json={"statuses": [{"id": w, "status": "delivered"}]}) for w in wamids])
            d = await db.campaigns.find_one({"id": cid})
            print(f"   after 20 delivered: deliveredCount={d['deliveredCount']} readCount={d['readCount']}")
            check(d['deliveredCount'] == 20 and all(r['status'] == 'delivered' for r in d['recipients']),
                  "TEST 1: 20 simultaneous delivered webhooks -> deliveredCount == 20")
            await asyncio.gather(*[c.post(url, json={"statuses": [{"id": w, "status": s}]})
                                   for w in wamids for s in ("read", "delivered", "read")])
            d = await db.campaigns.find_one({"id": cid})
            print(f"   after 40 read + 20 stale delivered: deliveredCount={d['deliveredCount']} readCount={d['readCount']}")
            check((d['deliveredCount'], d['readCount']) == (20, 20), "TEST 1b: duplicate read/stale delivered don't double count")
            await c.post(url, json=bizchat_status(wamids[0], "failed", "Message undeliverable"))
            d = await db.campaigns.find_one({"id": cid})
            check((d['sentCount'], d['failedCount'], d['deliveredCount'], d['readCount']) == (19, 1, 19, 19),
                  f"TEST 1c: read -> failed decrements delivered/read/sent (got {d['sentCount']},{d['failedCount']},{d['deliveredCount']},{d['readCount']})")

            # --- TEST 3: failed webhook with error text in body is a status, not an incoming message
            s3 = extract_status_data(bizchat_status("wamid.X", "failed", "Message undeliverable: 131026", is_new=None))
            check(s3 and s3[0]['status'] == 'failed' and '131026' in s3[0]['error'], "TEST 3: failed + body text -> status update with error reason")
            incoming = extract_status_data(bizchat_status("wamid.Y", "received", "Hi, price please?", is_new=True))
            check(incoming == [], "TEST 3b: real incoming message with body is NOT treated as status")

            # --- TEST 2: failed webhook BEFORE the worker saves messageId (legacy /bizchat path, no user id)
            cid2 = str(uuid.uuid4()); cids.append(cid2)
            phones = ["+919111100001", "+919111100002", "+919111100003"]
            wamids_b = [f"wamid.{p.lstrip('+')}" for p in phones]
            r = await c.post(f"{BACKEND}/api/webhook/bizchat",
                             json=bizchat_status(wamids_b[0], "failed", "Message undeliverable: user not on WhatsApp"))
            print(f"   early failed webhook response: {r.json()}")
            r2 = await c.post(f"{BACKEND}/api/webhook/{user_id}", json={"statuses": [{"id": wamids_b[1], "status": "delivered"}]})
            queued = await db.pending_statuses.count_documents({"wamid": {"$in": wamids_b}})
            check(r.json().get('type') == 'status_update' and queued == 2, f"TEST 2: early statuses queued in pending_statuses ({queued})")
        await db.campaigns.insert_one({"id": cid2, "userId": user_id, "status": "processing", "templateName": "t",
            "recipients": [recip(p) for p in phones], "totalCount": 3, "sentCount": 0, "failedCount": 0,
            "pendingCount": 3, "deliveredCount": 0, "readCount": 0, "createdAt": now, "lastHeartbeatAt": now})
        await m.process_campaign(cid2, "tok", "vendor")
        d = await db.campaigns.find_one({"id": cid2})
        by = {r['phone']: r for r in d['recipients']}
        for p in phones:
            print(f"   {p}: status={by[p]['status']} error={by[p].get('error')} messageId={by[p].get('messageId')}")
        print(f"   counts: sent={d['sentCount']} failed={d['failedCount']} pending={d['pendingCount']} delivered={d['deliveredCount']}")
        check(by[phones[0]]['status'] == 'failed' and 'not on WhatsApp' in (by[phones[0]]['error'] or ''),
              "TEST 2: recipient ends FAILED with BizChat's error reason")
        check(by[phones[1]]['status'] == 'delivered', "TEST 2: early delivered status applied too")
        check((d['sentCount'], d['failedCount'], d['pendingCount'], d['deliveredCount']) == (2, 1, 0, 1), "TEST 2: counts correct")
        check(await db.pending_statuses.count_documents({"wamid": {"$in": wamids_b}}) == 0, "TEST 2: applied pending_statuses removed")
        print("\nALL PASSED" if ok else "\nSOME CHECKS FAILED")
    finally:
        await db.campaigns.delete_many({"id": {"$in": cids}})
        await db.users.delete_one({"id": user_id})
        await db.pending_statuses.delete_many({"wamid": {"$in": wamids_b}})
        await m.close_http_client()
        server.should_exit = True
        await srv


if __name__ == "__main__":
    asyncio.run(main())
