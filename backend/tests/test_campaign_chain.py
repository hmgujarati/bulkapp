"""Chained campaign test: parts run one after another (no BizChat calls).

Run: python tests/test_campaign_chain.py
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import db  # noqa: E402
from routes import messages as msg_mod  # noqa: E402

CHAIN = f"testchain-{uuid.uuid4()}"


async def _mk_user():
    user_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user_id, "email": f"{user_id}@t.com", "firstName": "T", "lastName": "T",
        "role": "user", "dailyLimit": 100000, "dailyUsage": 0,
        "lastResetDateTime": datetime.now(timezone.utc).isoformat(),
        "bizChatToken": "tok", "bizChatVendorUID": "vend",
    })
    return user_id


async def _mk_part(user_id, seq, total, status):
    cid = str(uuid.uuid4())
    await db.campaigns.insert_one({
        "id": cid, "userId": user_id, "name": f"TEST_Chain (Part {seq}/{total})",
        "templateName": "t",
        "recipients": [
            {"phone": f"9190009{seq}{i:03d}", "name": "", "status": "pending"} for i in range(3)
        ],
        "totalCount": 3, "sentCount": 0, "failedCount": 0, "pendingCount": 3,
        "status": status, "chainId": CHAIN, "chainSequence": seq, "chainTotal": total,
        "chainLabel": "part", "createdAt": datetime.now(timezone.utc).isoformat(),
    })
    return cid


async def main():
    user_id = await _mk_user()
    p1 = await _mk_part(user_id, 1, 3, "processing")
    p2 = await _mk_part(user_id, 2, 3, "queued")
    p3 = await _mk_part(user_id, 3, 3, "queued")

    async def fake_send(*a, **k):
        return {"success": True, "data": {"data": {"wamid": "wamid." + str(uuid.uuid4())}}}

    original = msg_mod.send_whatsapp_message
    msg_mod.send_whatsapp_message = fake_send
    try:
        await msg_mod.process_campaign(p1, "tok", "vend")
        # part 2 is spawned as a task by the chain hook; give it time to finish
        for _ in range(30):
            s2 = await db.campaigns.find_one({"id": p2}, {"status": 1, "sentCount": 1})
            if s2["status"] == "completed":
                break
            await asyncio.sleep(1)

        s1 = await db.campaigns.find_one({"id": p1}, {"status": 1, "sentCount": 1})
        s2 = await db.campaigns.find_one({"id": p2}, {"status": 1, "sentCount": 1})
        assert s1["status"] == "completed" and s1["sentCount"] == 3, s1
        print("PASS: part 1 completed")
        assert s2["status"] == "completed" and s2["sentCount"] == 3, s2
        print("PASS: part 2 auto-started and completed after part 1")

        for _ in range(30):
            s3 = await db.campaigns.find_one({"id": p3}, {"status": 1, "sentCount": 1})
            if s3["status"] == "completed":
                break
            await asyncio.sleep(1)
        s3 = await db.campaigns.find_one({"id": p3}, {"status": 1, "sentCount": 1})
        assert s3["status"] == "completed" and s3["sentCount"] == 3, s3
        print("PASS: part 3 auto-started and completed after part 2")
        print("\nCHAIN TEST PASSED")
    finally:
        msg_mod.send_whatsapp_message = original
        await db.campaigns.delete_many({"chainId": CHAIN})
        await db.users.delete_one({"id": user_id})


if __name__ == "__main__":
    asyncio.run(main())
