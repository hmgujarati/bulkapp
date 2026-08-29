"""Daily usage recalculation: sends done TODAY by an OLD campaign must count.

Run: python tests/test_dailyusage_backfill.py
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import db  # noqa: E402
from utils.daily_limit import recalculate_daily_usage, update_last_activity  # noqa: E402

now = datetime.now(timezone.utc)


async def _mk_user(daily_usage, window_start):
    user_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": user_id, "email": f"{user_id}@t.com", "firstName": "T", "lastName": "T",
        "role": "user", "dailyLimit": 100000, "dailyUsage": daily_usage,
        "lastResetDateTime": window_start.isoformat(),
    })
    return user_id


async def _mk_campaign(user_id, created_at, sent_ats, failed=0):
    cid = str(uuid.uuid4())
    recipients = [
        {"phone": f"9190000{i:04d}", "name": "", "status": "sent", "sentAt": s.isoformat()}
        for i, s in enumerate(sent_ats)
    ]
    recipients += [
        {"phone": f"9199999{i:04d}", "name": "", "status": "failed", "error": "x"}
        for i in range(failed)
    ]
    await db.campaigns.insert_one({
        "id": cid, "userId": user_id, "name": "TEST_usage", "templateName": "t",
        "recipients": recipients, "totalCount": len(recipients),
        "sentCount": len(sent_ats), "failedCount": failed, "pendingCount": 0,
        "status": "completed",
        "createdAt": created_at.isoformat(),
        "updatedAt": now.isoformat(),
    })
    return cid


async def main():
    failures = []
    window_start = now - timedelta(hours=6)

    # --- Case 1: campaign created 3 days ago, resumed & sent 40 msgs inside window
    u1 = await _mk_user(0, window_start)
    await _mk_campaign(
        u1,
        created_at=now - timedelta(days=3),
        sent_ats=[now - timedelta(minutes=5 + i) for i in range(40)],
        failed=7,
    )
    r1 = await recalculate_daily_usage(u1)
    if r1['dailyUsage'] != 40:
        failures.append(f"Case1: expected 40 got {r1['dailyUsage']}")
    else:
        print(f"✓ Case1: old campaign resumed today counted correctly ({r1['dailyUsage']}) — 7 failed refunded")

    # --- Case 2: sends BEFORE the window must not count
    u2 = await _mk_user(500, window_start)
    await _mk_campaign(
        u2,
        created_at=now - timedelta(days=1),
        sent_ats=[now - timedelta(hours=12), now - timedelta(hours=10)],
    )
    await _mk_campaign(u2, created_at=now, sent_ats=[now - timedelta(minutes=2)])
    r2 = await recalculate_daily_usage(u2)
    if r2['dailyUsage'] != 1:
        failures.append(f"Case2: expected 1 got {r2['dailyUsage']}")
    else:
        print(f"✓ Case2: pre-window sends excluded, in-window counted ({r2['dailyUsage']})")

    # --- Case 3: over-counted usage gets corrected down (refund)
    u3 = await _mk_user(3000, window_start)
    await _mk_campaign(u3, created_at=now - timedelta(days=2), sent_ats=[], failed=3000)
    r3 = await recalculate_daily_usage(u3)
    if r3['dailyUsage'] != 0 or r3['previousUsage'] != 3000:
        failures.append(f"Case3: expected 3000->0 got {r3['previousUsage']}->{r3['dailyUsage']}")
    else:
        print("✓ Case3: all-failed campaign refunded quota (3000 -> 0)")

    # --- Case 4: update_last_activity must NOT slide the 24h window anchor
    u4 = await _mk_user(0, window_start)
    await update_last_activity(u4, 10)
    doc = await db.users.find_one({"id": u4})
    if doc['lastResetDateTime'] != window_start.isoformat():
        failures.append(f"Case4: window anchor moved to {doc['lastResetDateTime']}")
    elif doc['dailyUsage'] != 10:
        failures.append(f"Case4: expected dailyUsage 10 got {doc['dailyUsage']}")
    else:
        print("✓ Case4: window anchor stays fixed, usage incremented")

    # --- Case 5: expired window resets usage to 0 on refresh
    u5 = await _mk_user(900, now - timedelta(hours=30))
    await _mk_campaign(u5, created_at=now - timedelta(hours=29), sent_ats=[now - timedelta(hours=28)])
    r5 = await recalculate_daily_usage(u5)
    if r5['dailyUsage'] != 0:
        failures.append(f"Case5: expected 0 after window expiry got {r5['dailyUsage']}")
    else:
        print("✓ Case5: expired 24h window resets usage to 0")

    # cleanup
    for uid in (u1, u2, u3, u4, u5):
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
