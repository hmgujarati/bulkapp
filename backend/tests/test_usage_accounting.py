"""Daily-usage accounting: each RUN charges only what it sent, and a campaign that
runs out of quota resumes later instead of dying.

Run: python tests/test_usage_accounting.py
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import db  # noqa: E402
from routes import messages as msg_mod  # noqa: E402

failures = []


async def _mk_user(daily_limit, daily_usage=0, reset_hours_ago=1):
    user_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user_id, "email": f"{user_id}@t.com", "firstName": "T", "lastName": "T",
        "role": "user", "dailyLimit": daily_limit, "dailyUsage": daily_usage,
        "lastResetDateTime": (datetime.now(timezone.utc) - timedelta(hours=reset_hours_ago)).isoformat(),
        "bizChatToken": "tok", "bizChatVendorUID": "vend",
    })
    return user_id


async def _mk_campaign(user_id, count, **extra):
    cid = str(uuid.uuid4())
    doc = {
        "id": cid, "userId": user_id, "name": "TEST_usage_acct", "templateName": "t",
        "recipients": [{"phone": f"9190001{i:04d}", "name": "", "status": "pending"} for i in range(count)],
        "totalCount": count, "sentCount": 0, "failedCount": 0, "pendingCount": count,
        "status": "pending", "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    doc.update(extra)
    await db.campaigns.insert_one(doc)
    return cid


async def _usage(user_id):
    u = await db.users.find_one({"id": user_id})
    return u.get('dailyUsage', 0)


async def main():
    async def fake_send(*a, **k):
        return {"success": True, "data": {"data": {"wamid": "wamid." + str(uuid.uuid4())}}}

    original = msg_mod.send_whatsapp_message
    msg_mod.send_whatsapp_message = fake_send
    created_users = []
    try:
        # === Case 1: drip across two windows charges 5 then 5 (not 5 then 10) ===
        u1 = await _mk_user(100000)
        created_users.append(u1)
        anchor = datetime.now(timezone.utc) - timedelta(minutes=5)
        c1 = await _mk_campaign(u1, 12, dripEnabled=True, dripDailyLimit=5,
                                dripStartAt=anchor.isoformat())
        await msg_mod.process_campaign(c1, "tok", "vend")
        after_day1 = await _usage(u1)
        if after_day1 != 5:
            failures.append(f"Case1 day1: expected usage 5 got {after_day1}")

        # Move the anchor back a day -> next drip window
        await db.campaigns.update_one(
            {"id": c1}, {"$set": {"dripStartAt": (anchor - timedelta(days=1)).isoformat(),
                                  "status": "pending"}}
        )
        await msg_mod.process_campaign(c1, "tok", "vend")
        after_day2 = await _usage(u1)
        if after_day2 != 10:
            failures.append(f"Case1 day2: expected cumulative usage 10 got {after_day2} (double-charging?)")
        else:
            print(f"✓ Case1: drip charged per run (5 -> 10), campaign sentCount grew correctly")

        # === Case 2: non-drip campaign bigger than today's remaining quota ===
        u2 = await _mk_user(10, daily_usage=8)
        created_users.append(u2)
        c2 = await _mk_campaign(u2, 5)
        await msg_mod.process_campaign(c2, "tok", "vend")
        camp = await db.campaigns.find_one({"id": c2})
        usage2 = await _usage(u2)
        if camp['sentCount'] != 2 or usage2 != 10:
            failures.append(f"Case2: expected 2 sent / usage 10, got {camp['sentCount']} / {usage2}")
        elif camp['status'] != 'scheduled' or not camp.get('scheduledAt'):
            failures.append(f"Case2: expected status scheduled with scheduledAt, got {camp['status']}")
        else:
            print("✓ Case2: partial send inside quota, rest auto-scheduled for after the reset")

        # Simulate the daily reset and resume
        await db.users.update_one({"id": u2}, {"$set": {
            "dailyUsage": 0,
            "lastResetDateTime": datetime.now(timezone.utc).isoformat()
        }})
        await db.campaigns.update_one({"id": c2}, {"$set": {"status": "pending"}})
        await msg_mod.process_campaign(c2, "tok", "vend")
        camp = await db.campaigns.find_one({"id": c2})
        usage2b = await _usage(u2)
        if camp['sentCount'] != 5 or camp['status'] != 'completed':
            failures.append(f"Case2b: expected 5 sent/completed, got {camp['sentCount']}/{camp['status']}")
        elif usage2b != 3:
            failures.append(f"Case2b: expected usage 3 after reset, got {usage2b} (cumulative charge?)")
        else:
            print("✓ Case2b: after the reset the rest went out and only 3 were charged")

        # === Case 3: quota fully used -> campaign waits, nothing sent, nothing charged ===
        u3 = await _mk_user(10, daily_usage=10)
        created_users.append(u3)
        c3 = await _mk_campaign(u3, 4)
        await msg_mod.process_campaign(c3, "tok", "vend")
        camp = await db.campaigns.find_one({"id": c3})
        if camp['sentCount'] != 0 or camp['status'] != 'scheduled':
            failures.append(f"Case3: expected 0 sent/scheduled, got {camp['sentCount']}/{camp['status']}")
        elif await _usage(u3) != 10:
            failures.append("Case3: usage changed while nothing was sent")
        else:
            print("✓ Case3: no quota left -> campaign scheduled for after the reset, nothing charged")

        # === Case 4: cancelling a running campaign stops the worker ===
        u4 = await _mk_user(100000)
        created_users.append(u4)
        c4 = await _mk_campaign(u4, 40)

        async def cancel_soon():
            await asyncio.sleep(0.2)
            await db.campaigns.update_one({"id": c4}, {"$set": {"status": "cancelled"}})

        await asyncio.gather(msg_mod.process_campaign(c4, "tok", "vend"), cancel_soon())
        camp = await db.campaigns.find_one({"id": c4})
        if camp['status'] != 'cancelled':
            failures.append(f"Case4: expected cancelled, got {camp['status']}")
        elif camp['sentCount'] >= 40:
            failures.append(f"Case4: worker kept going after cancel ({camp['sentCount']}/40 sent)")
        elif await _usage(u4) != camp['sentCount']:
            failures.append(f"Case4: usage {await _usage(u4)} != sent {camp['sentCount']}")
        else:
            print(f"✓ Case4: cancel stopped the worker at {camp['sentCount']}/40 and charged exactly that")
    finally:
        msg_mod.send_whatsapp_message = original
        for uid in created_users:
            await db.users.delete_one({"id": uid})
            await db.campaigns.delete_many({"userId": uid})

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\nALL PASSED")


if __name__ == "__main__":
    asyncio.run(main())
