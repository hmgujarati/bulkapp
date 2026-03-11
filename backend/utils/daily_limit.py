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
    remaining = daily_limit - user_data.get('dailyUsage', 0)
    
    # Calculate when the limit will reset
    next_reset = None
    if user_data.get('lastResetDateTime'):
        try:
            last_reset = datetime.fromisoformat(user_data['lastResetDateTime'].replace('Z', '+00:00'))
            next_reset = (last_reset + timedelta(hours=24)).isoformat()
        except (ValueError, TypeError):
            pass
    
    return {
        **user_data,
        'remaining': remaining,
        'nextResetAt': next_reset
    }


async def update_last_activity(user_id: str, messages_sent: int = 0):
    """
    Update user's last activity time and daily usage.
    Called after sending messages to set the 24-hour reset window.
    """
    now = datetime.now(timezone.utc)
    
    update_data = {
        "lastResetDateTime": now.isoformat()
    }
    
    if messages_sent > 0:
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": update_data,
                "$inc": {"dailyUsage": messages_sent}
            }
        )
    else:
        await db.users.update_one(
            {"id": user_id},
            {"$set": update_data}
        )
