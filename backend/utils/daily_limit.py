"""Daily usage utility functions"""
from datetime import datetime, timezone, timedelta
from utils.database import db


async def check_and_reset_daily_usage(user_id: str, user_data: dict = None) -> dict:
    """
    Check if 24 hours have passed since last reset and reset daily usage if needed.
    Returns updated user data with current daily usage info.
    
    Time-based reset: Resets exactly 24 hours after the last message was sent.
    """
    if user_data is None:
        user_data = await db.users.find_one({"id": user_id})
        if not user_data:
            return None
    
    now = datetime.now(timezone.utc)
    last_reset_str = user_data.get('lastResetDateTime')
    daily_limit = user_data.get('dailyLimit', 1000)
    
    should_reset = False
    
    if last_reset_str:
        try:
            # Parse the last reset datetime
            last_reset = datetime.fromisoformat(last_reset_str.replace('Z', '+00:00'))
            # Check if 24 hours have passed
            time_since_reset = now - last_reset
            if time_since_reset >= timedelta(hours=24):
                should_reset = True
        except (ValueError, TypeError):
            # If parsing fails, reset
            should_reset = True
    else:
        # No reset datetime recorded, this is first use or legacy data
        # Check legacy lastResetDate field
        legacy_date = user_data.get('lastResetDate')
        if legacy_date:
            # Convert legacy date to datetime (assume midnight)
            try:
                last_reset = datetime.strptime(legacy_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if now - last_reset >= timedelta(hours=24):
                    should_reset = True
            except (ValueError, TypeError):
                should_reset = True
        else:
            should_reset = True
    
    if should_reset:
        # Reset daily usage
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "dailyUsage": 0,
                    "lastResetDateTime": now.isoformat()
                }
            }
        )
        user_data['dailyUsage'] = 0
        user_data['lastResetDateTime'] = now.isoformat()
    
    # Calculate remaining and next reset time
    # dailyLimit = -1 means UNLIMITED
    if daily_limit == -1:
        remaining = -1  # Sentinel for "unlimited"
    else:
        remaining = daily_limit - user_data.get('dailyUsage', 0)
    
    # Calculate when the limit will reset
    next_reset = None
    if user_data.get('lastResetDateTime'):
        try:
            last_reset = datetime.fromisoformat(user_data['lastResetDateTime'].replace('Z', '+00:00'))
            next_reset = (last_reset + timedelta(hours=24)).isoformat()
        except (ValueError, TypeError):
            pass
    
    result = {k: v for k, v in user_data.items() if k != '_id'}
    result['remaining'] = remaining
    result['nextResetAt'] = next_reset
    return result


async def update_last_activity(user_id: str, messages_sent: int = 0):
    """
    Update user's last activity time and daily usage.

    NOTE: `lastResetDateTime` anchors the 24h window and is only seeded when
    missing — it must NOT slide forward on every send, otherwise the window
    never expires for users who send every day and their usage never resets.
    """
    now = datetime.now(timezone.utc)
    
    await db.users.update_one(
        {
            "id": user_id,
            "$or": [{"lastResetDateTime": {"$exists": False}}, {"lastResetDateTime": None}]
        },
        {"$set": {"lastResetDateTime": now.isoformat()}}
    )
    
    update_doc = {"$set": {"lastActivityAt": now.isoformat()}}
    if messages_sent > 0:
        update_doc["$inc"] = {"dailyUsage": messages_sent}
    await db.users.update_one({"id": user_id}, update_doc)


async def recalculate_daily_usage(user_id: str) -> dict:
    """
    Recompute a user's dailyUsage from the messages that were ACTUALLY sent
    inside the current 24h window, using each recipient's `sentAt`.

    This is what the old approach got wrong: it looked at `campaign.createdAt`,
    so a campaign created yesterday (retried / resumed / drip) that sent
    messages today was not counted at all. Failed messages have no `sentAt`,
    so they are automatically refunded.
    """
    user = await db.users.find_one({"id": user_id})
    if not user:
        return None
    
    # Expire the window first (may reset usage + re-anchor lastResetDateTime)
    user = await check_and_reset_daily_usage(user_id, user)
    previous_usage = user.get('dailyUsage', 0)
    
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=24)
    if user.get('lastResetDateTime'):
        try:
            parsed = datetime.fromisoformat(str(user['lastResetDateTime']).replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            window_start = parsed
        except (ValueError, TypeError):
            pass
    
    window_start_iso = window_start.isoformat()
    sent_at_date = {
        "$convert": {"input": "$$r.sentAt", "to": "date", "onError": None, "onNull": None}
    }
    pipeline = [
        {"$match": {
            "userId": user_id,
            "status": {"$ne": "draft"},
            "$or": [
                {"updatedAt": {"$gte": window_start_iso}},
                {"completedAt": {"$gte": window_start_iso}},
                {"createdAt": {"$gte": window_start_iso}},
            ]
        }},
        {"$project": {
            "sentInWindow": {"$size": {"$filter": {
                "input": {"$ifNull": ["$recipients", []]},
                "as": "r",
                "cond": {"$gte": [sent_at_date, window_start]}
            }}}
        }},
        {"$group": {"_id": None, "total": {"$sum": "$sentInWindow"}}},
    ]
    
    rows = await db.campaigns.aggregate(pipeline, allowDiskUse=True).to_list(1)
    actual_usage = rows[0]['total'] if rows else 0
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"dailyUsage": actual_usage, "dailyUsageRefreshedAt": now.isoformat()}}
    )
    
    return {
        "userId": user_id,
        "email": user.get('email'),
        "previousUsage": previous_usage,
        "dailyUsage": actual_usage,
        "dailyLimit": user.get('dailyLimit', 1000),
        "windowStart": window_start_iso,
    }
