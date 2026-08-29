"""Drip campaign (daily sending limit) logic test.

Standalone async script (no pytest-asyncio in this env):
    python tests/test_drip_campaign.py

Runs process_campaign against local Mongo with the BizChat send call patched,
verifying only `dripDailyLimit` messages go out per 24h window and that the
campaign parks itself as SCHEDULED for the next window.
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import db  # noqa: E402
from routes import messages as msg_mod  # noqa: E402


def _campaign_doc(user_id, total, drip_limit, anchor_iso):
    return {
        "id": str(uuid.uuid4()),
        "userId": user_id,
        "name": "Drip Test",
        "templateName": "test_template",
        "templateReference": "My Ref",
        "recipients": [
            {"phone": f"91900000{i:04d}", "name": f"U{i}", "status": "pending"}
            for i in range(total)
        ],
        "totalCount": total,
        "sentCount": 0,
        "failedCount": 0,
        "pendingCount": total,
        "status": "processing",
        "dripEnabled": True,
        "dripDailyLimit": drip_limit,
        "dripStartAt": anchor_iso,
        "dripWindowIndex": -1,
        "dripSentInWindow": 0,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }


async def _make_user(daily_limit=100):
    user_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user_id, "email": f"{user_id}@t.com", "firstName": "T", "lastName": "T",
        "role": "user", "dailyLimit": daily_limit, "dailyUsage": 0,
        "lastResetDateTime": datetime.now(timezone.utc).isoformat(),
        "bizChatToken": "tok", "bizChatVendorUID": "vend",
    })
    return user_id


async def test_daily_quota_then_reschedule():
    user_id = await _make_user()
    anchor = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    campaign = _campaign_doc(user_id, total=5, drip_limit=2, anchor_iso=anchor)
    await db.campaigns.insert_one(dict(campaign))

    async def fake_send(*args, **kwargs):
        return {"success": True, "data": {"data": {"wamid": "wamid." + str(uuid.uuid4())}}}

    original = msg_mod.send_whatsapp_message
    msg_mod.send_whatsapp_message = fake_send
    try:
        await msg_mod.process_campaign(campaign["id"], "tok", "vend")
        s = await db.campaigns.find_one({"id": campaign["id"]})
        assert s["sentCount"] == 2, f"expected 2 sent, got {s['sentCount']}"
        assert s["dripSentInWindow"] == 2, s["dripSentInWindow"]
        assert s["status"] == "scheduled", s["status"]
        assert s["pendingCount"] == 3, s["pendingCount"]
        expected = datetime.fromisoformat(anchor) + timedelta(days=1)
        assert abs((datetime.fromisoformat(s["scheduledAt"]) - expected).total_seconds()) < 5
        print("PASS: first window sent exactly 2 and rescheduled to next day")

        # Same window again -> nothing more should go out
        await db.campaigns.update_one({"id": campaign["id"]}, {"$set": {"status": "processing"}})
        await msg_mod.process_campaign(campaign["id"], "tok", "vend")
        s2 = await db.campaigns.find_one({"id": campaign["id"]})
        assert s2["sentCount"] == 2, s2["sentCount"]
        assert s2["status"] == "scheduled"
        print("PASS: re-running inside the same window sends nothing")

        # Next window (shift anchor back a day)
        new_anchor = (datetime.fromisoformat(anchor) - timedelta(days=1)).isoformat()
        await db.campaigns.update_one(
            {"id": campaign["id"]},
            {"$set": {"status": "processing", "dripStartAt": new_anchor}}
        )
        await msg_mod.process_campaign(campaign["id"], "tok", "vend")
        s3 = await db.campaigns.find_one({"id": campaign["id"]})
        assert s3["sentCount"] == 4, s3["sentCount"]
        assert s3["dripSentInWindow"] == 2, s3["dripSentInWindow"]
        assert s3["status"] == "scheduled"
        print("PASS: next window sent the next 2")

        # Final window -> campaign completes
        final_anchor = (datetime.fromisoformat(anchor) - timedelta(days=2)).isoformat()
        await db.campaigns.update_one(
            {"id": campaign["id"]},
            {"$set": {"status": "processing", "dripStartAt": final_anchor}}
        )
        await msg_mod.process_campaign(campaign["id"], "tok", "vend")
        s4 = await db.campaigns.find_one({"id": campaign["id"]})
        assert s4["sentCount"] == 5, s4["sentCount"]
        assert s4["status"] == "completed", s4["status"]
        print("PASS: last window completes the campaign")
    finally:
        msg_mod.send_whatsapp_message = original
        await db.campaigns.delete_one({"id": campaign["id"]})
        await db.users.delete_one({"id": user_id})


async def test_future_start_parks_campaign():
    user_id = await _make_user()
    anchor = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    campaign = _campaign_doc(user_id, total=4, drip_limit=2, anchor_iso=anchor)
    await db.campaigns.insert_one(dict(campaign))

    calls = []

    async def fake_send(*args, **kwargs):
        calls.append(1)
        return {"success": True, "data": {}}

    original = msg_mod.send_whatsapp_message
    msg_mod.send_whatsapp_message = fake_send
    try:
        await msg_mod.process_campaign(campaign["id"], "tok", "vend")
        s = await db.campaigns.find_one({"id": campaign["id"]})
        assert calls == [], calls
        assert s["status"] == "scheduled", s["status"]
        assert s["sentCount"] == 0
        assert s["scheduledAt"] == anchor
        print("PASS: future start time parks the campaign without sending")
    finally:
        msg_mod.send_whatsapp_message = original
        await db.campaigns.delete_one({"id": campaign["id"]})
        await db.users.delete_one({"id": user_id})


async def main():
    await test_daily_quota_then_reschedule()
    await test_future_start_parks_campaign()
    print("\nALL DRIP TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
