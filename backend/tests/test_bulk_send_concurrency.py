"""Run: cd /app/backend && python tests/test_bulk_send_concurrency.py
Spins up a MOCK BizChat server and runs 2 campaigns concurrently through the real process_campaign."""
import asyncio, uuid, sys, os, logging
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

import uvicorn
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
PORT = 8765
mock = FastAPI()
state = {"inflight": 0, "peak": 0, "calls": {}, "user_id": None, "webhooks": {}}
WEBHOOK_PHONES = ("919876500001", "919876500012", "919876533333")
BACKEND = "http://127.0.0.1:8001"


async def delivered_webhook_later(wamid):
    """Simulate BizChat calling our real webhook 1s after the send."""
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{BACKEND}/api/webhook/{state['user_id']}",
                         json={"statuses": [{"id": wamid, "status": "delivered"}]})
    state["webhooks"][wamid] = r.json()


@mock.post("/api/{vendor}/contact/send-template-message")
async def send(vendor: str, request: Request):
    body = await request.json()
    phone, tpl = body["phone_number"], body["template_name"]
    state["calls"][phone] = state["calls"].get(phone, 0) + 1
    state["inflight"] += 1
    state["peak"] = max(state["peak"], state["inflight"])
    try:
        await asyncio.sleep(0.3)
        leaked = {"status", "sentAt", "messageId", "error", "retryCount", "phone", "name"} & set(body)
        if leaked:
            return JSONResponse({"result": "failed", "message": f"leaked {leaked}"}, 422)
        if tpl == "bad_template":
            return {"result": "failed", "message": "Template for the selected language not found"}
        if phone.endswith("99990"):
            return JSONResponse({"result": "failed", "message": "Invalid phone number"}, 400)
        if phone.endswith("1111") and state["calls"][phone] == 1:
            return JSONResponse({"error": "SQLSTATE[HY000] [2002] Connection refused"}, 500)
        if phone.endswith("33333") and state["calls"][phone] == 1:
            return JSONResponse({"error": "Forbidden"}, 403)
        if phone in WEBHOOK_PHONES:
            asyncio.create_task(delivered_webhook_later(f"wamid.{phone}"))
        return {"result": "success", "data": {"wamid": f"wamid.{phone}", "log_uid": str(uuid.uuid4())}}
    finally:
        state["inflight"] -= 1


def recipients(prefix, n, specials=None):
    rs = [{"phone": f"+91{prefix}{i:05d}", "name": f"R{i}", "status": "pending", "sentAt": None,
           "messageId": None, "error": None, "retryCount": 0, "template_language": "en_US",
           "field_1": "Hi {name}", "field_2": "", "field_3": "", "field_4": "", "field_5": ""} for i in range(n)]
    for i, suffix in (specials or {}).items():
        rs[i]["phone"] = f"+91{prefix}{suffix}"
    return rs


async def main():
    import routes.messages as m
    from utils.database import db
    m.BIZCHAT_API_BASE = f"http://127.0.0.1:{PORT}/api"

    server = uvicorn.Server(uvicorn.Config(mock, port=PORT, log_level="warning"))
    srv_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1)

    user_id = f"test-user-{uuid.uuid4()}"
    state["user_id"] = user_id

    # Race simulation for +919876544444: a delivered webhook lands between the
    # messageId write and the SENT status write — status must stay delivered.
    from motor.motor_asyncio import AsyncIOMotorCollection
    orig_update = AsyncIOMotorCollection.update_one
    race = {"done": False, "skipped": False}

    async def racing_update(self, flt, update, *a, **kw):
        if not race["done"] and flt.get("recipients.18.status") == "pending":
            race["done"] = True
            await orig_update(self, {"id": flt["id"]}, {"$set": {"recipients.18.status": "delivered"}})
            res = await orig_update(self, flt, update, *a, **kw)
            race["skipped"] = res.matched_count == 0
            return res
        return await orig_update(self, flt, update, *a, **kw)
    AsyncIOMotorCollection.update_one = racing_update
    now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({"id": user_id, "email": f"{user_id}@test.local", "dailyUsage": 0,
                               "dailyLimit": -1, "lastResetDateTime": now})
    camps = {
        "good": recipients("98765", 20, {3: "99990", 7: "11111", 15: "33333", 18: "44444"}),
        "badtpl": recipients("91234", 20),
    }
    ids = {}
    for key, rs in camps.items():
        cid = str(uuid.uuid4())
        ids[key] = cid
        await db.campaigns.insert_one({"id": cid, "userId": user_id, "name": f"TEST {key}", "status": "processing",
                                       "templateName": "bad_template" if key == "badtpl" else "welcome",
                                       "recipients": rs, "totalCount": 20, "sentCount": 0, "failedCount": 0,
                                       "pendingCount": 20, "createdAt": now, "lastHeartbeatAt": now})
    try:
        await asyncio.gather(*[m.process_campaign(cid, "tok", "vendor") for cid in ids.values()])
        await asyncio.sleep(2)  # let the last 1s-delayed webhooks land

        ok = True
        def check(cond, msg):
            nonlocal ok
            ok &= bool(cond)
            print(("PASS " if cond else "FAIL ") + msg)

        g = await db.campaigns.find_one({"id": ids["good"]})
        b = await db.campaigns.find_one({"id": ids["badtpl"]})
        u = await db.users.find_one({"id": user_id})
        print(f"\ngood:   status={g['status']} sent={g['sentCount']} failed={g['failedCount']} pending={g['pendingCount']}")
        print(f"badtpl: status={b['status']} sent={b['sentCount']} failed={b['failedCount']} pending={b['pendingCount']}")
        print(f"mock peak in-flight={state['peak']}  module peak={m._inflight_peak}  dailyUsage={u['dailyUsage']}\n")

        check(state["peak"] <= 5 and m._inflight_peak <= 5, "never more than 5 requests in flight across both campaigns")
        check((b['sentCount'], b['failedCount'], b['pendingCount']) == (0, 20, 0), "invalid template: 20 FAILED, counts correct")
        check(all(state["calls"][r['phone'].lstrip('+')] == 1 for r in b['recipients']), "invalid template: each sent exactly once (no retry)")
        check(all("Template for the selected language not found" in r['error'] for r in b['recipients']), "BizChat message saved as error")
        check((g['sentCount'], g['failedCount'], g['pendingCount']) == (19, 1, 0), "good campaign: 19 sent, 1 failed (invalid number)")
        check(state["calls"]["919876599990"] == 1, "HTTP 400 invalid number not retried")
        check(state["calls"]["919876511111"] == 2, "HTTP 500 retried once and then sent")
        check(state["calls"]["919876533333"] == 2, "HTTP 403 treated as retryable, retried and sent")
        by_phone = {r['phone'].lstrip('+'): r for r in g['recipients']}
        for ph in WEBHOOK_PHONES:
            print(f"   webhook {ph}: response={state['webhooks'].get('wamid.' + ph)} final status={by_phone[ph]['status']}")
            check(by_phone[ph]['status'] == 'delivered', f"{ph}: delivered webhook 1s after send -> status stays delivered")
        check(race["done"] and race["skipped"] and by_phone["919876544444"]['status'] == 'delivered',
              "race: webhook before SENT write -> SENT write skipped, stays delivered")
        check(g.get('deliveredCount') == 4, f"deliveredCount == 4 (got {g.get('deliveredCount')})")
        sent = [r for r in g['recipients'] if r['status'] in ('sent', 'delivered')]
        check(all(r['messageId'] == f"wamid.{r['phone'].lstrip('+')}" for r in sent), "wamid saved for every sent message")
        check(u['dailyUsage'] == 19, "dailyUsage increased only by newly sent messages")
        print("\nALL PASSED" if ok else "\nSOME CHECKS FAILED")
    finally:
        await db.campaigns.delete_many({"id": {"$in": list(ids.values())}})
        await db.users.delete_one({"id": user_id})
        AsyncIOMotorCollection.update_one = orig_update
        await m.close_http_client()
        server.should_exit = True
        await srv_task


if __name__ == "__main__":
    asyncio.run(main())
