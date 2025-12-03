# ⏰ Scheduled Campaigns Guide

## 🎯 Overview

The WhatsApp Bulk Messenger now supports **scheduled campaigns** - send messages at a future date and time automatically!

---

## ✅ New Feature Added: Automatic Scheduled Campaign Processing

### What Was Missing Before:
- ❌ Campaigns could be created with a schedule
- ❌ But they were never automatically sent
- ❌ No background job to check scheduled time

### What's Now Implemented:
- ✅ Background task runs every minute
- ✅ Automatically finds campaigns scheduled for current time
- ✅ Processes them automatically
- ✅ Runs 24/7 in the background

---

## 🔄 How It Works

### 1. **Background Scheduler**
```
Every 60 seconds:
  ├─ Check MongoDB for scheduled campaigns
  ├─ Find campaigns where scheduledAt <= now
  ├─ Update status from SCHEDULED → PROCESSING
  ├─ Start sending messages
  └─ Mark as COMPLETED when done
```

### 2. **Campaign Lifecycle**

```
User schedules campaign
       ↓
Status: SCHEDULED (stored in database)
       ↓
Wait for scheduled time...
       ↓
Background checker finds it (runs every minute)
       ↓
Status: PROCESSING (sending messages)
       ↓
Messages sent with rate limiting (29/sec)
       ↓
Status: COMPLETED
```

---

## 📅 How to Schedule a Campaign

### Step 1: Create Campaign as Normal
1. Go to **Send Messages** page
2. Fill in:
   - Campaign Name
   - Template Name
   - Template Fields (use `{name}` for personalization!)
   - Upload Recipients (Excel/CSV)

### Step 2: Choose Schedule Time
1. Look for the **Schedule** section
2. Select future date and time
3. Click **"Schedule Campaign"** button

### Step 3: Wait for Automatic Sending
- Your campaign will be saved with status: **SCHEDULED**
- Background task checks every minute
- When time arrives, it automatically starts sending
- No manual action needed!

---

## 🕐 Scheduling Examples

### Example 1: Send Tomorrow Morning
```
Current Time: Dec 3, 2024, 10:00 PM
Schedule For: Dec 4, 2024, 09:00 AM

Result: Campaign will automatically send at 9 AM tomorrow
```

### Example 2: Weekend Campaign
```
Current Time: Friday, 5:00 PM
Schedule For: Saturday, 10:00 AM

Result: Campaign sends on Saturday morning automatically
```

### Example 3: Holiday Greetings
```
Current Time: Dec 20, 2024
Schedule For: Dec 25, 2024, 08:00 AM

Result: Messages sent on Christmas morning
```

---

## ⚙️ Technical Details

### Background Task Specifications:

**Check Interval:** Every 60 seconds (1 minute)

**Process:**
1. Query: Find all campaigns with status = "SCHEDULED" and scheduledAt <= current time
2. For each campaign found:
   - Verify user has valid BizChat credentials
   - Update status to "PROCESSING"
   - Start message sending in background
   - Apply rate limiting (29 messages/second)
   - Update daily usage counter
   - Mark as "COMPLETED" when done

**Accuracy:** 
- ±1 minute from scheduled time
- If scheduled for 10:00 AM, will start between 10:00-10:01 AM

**Concurrency:**
- Multiple scheduled campaigns can run simultaneously
- Each campaign processes in its own background task

---

## 📊 Campaign Status Flow

```
┌─────────────┐
│  SCHEDULED  │ ← Campaign created with future time
└─────────────┘
       ↓
       ↓ (Background task finds it when time arrives)
       ↓
┌─────────────┐
│ PROCESSING  │ ← Currently sending messages
└─────────────┘
       ↓
       ↓ (All messages sent)
       ↓
┌─────────────┐
│  COMPLETED  │ ← Campaign finished
└─────────────┘
```

---

## 🔍 Monitoring Scheduled Campaigns

### View Scheduled Campaigns:
1. Go to **Campaign History** page
2. Look for campaigns with status: **SCHEDULED**
3. See scheduled date/time

### Check Progress:
1. When scheduled time arrives, status changes to **PROCESSING**
2. Click on campaign to see:
   - Sent count
   - Failed count
   - Pending count
3. Real-time updates

---

## ⚠️ Important Notes

### 1. **Server Must Be Running**
- The background task only works when the backend server is running
- If server is down during scheduled time, campaign won't send
- When server restarts, it will immediately check for overdue campaigns

### 2. **Daily Limits Still Apply**
- Scheduled campaigns respect daily sending limits
- If limit is exceeded at scheduled time, campaign will fail
- Make sure you have sufficient daily limit available

### 3. **User Credentials Required**
- User must have valid BizChat API token
- User must have valid Vendor UID
- If credentials are missing, campaign fails with error

### 4. **Timezone Considerations**
- All times are stored in UTC
- Frontend converts to local timezone for display
- Make sure to schedule in correct timezone

---

## 🧪 Testing Scheduled Campaigns

### Quick Test (2-minute schedule):

1. **Create Test Campaign:**
   - Go to Send Messages
   - Fill in all fields
   - Select time: **2 minutes from now**
   - Click "Schedule Campaign"

2. **Verify Scheduled:**
   - Go to Campaign History
   - See your campaign with status: SCHEDULED
   - Note the scheduled time

3. **Wait 2 Minutes:**
   - Watch Campaign History page
   - Status should change to PROCESSING
   - Then to COMPLETED

4. **Check Results:**
   - Click on campaign
   - Verify messages were sent
   - Check sent/failed counts

---

## 🛠️ Code Implementation

### Background Task Function:
```python
async def check_scheduled_campaigns():
    """Runs every 60 seconds to process scheduled campaigns"""
    while True:
        # Find campaigns ready to send
        now = datetime.now(timezone.utc)
        scheduled_campaigns = await db.campaigns.find({
            "status": "SCHEDULED",
            "scheduledAt": {"$lte": now.isoformat()}
        }).to_list(100)
        
        # Process each campaign
        for campaign in scheduled_campaigns:
            # Get user credentials
            # Update status to PROCESSING
            # Start sending in background
            asyncio.create_task(process_campaign(...))
        
        # Wait 60 seconds before next check
        await asyncio.sleep(60)
```

### Startup Hook:
```python
@app.on_event("startup")
async def startup_event():
    # ... other startup code ...
    
    # Start background task
    asyncio.create_task(check_scheduled_campaigns())
    logger.info("Scheduled campaigns checker started")
```

---

## 📋 Deployment Considerations

### For Production:

1. **Process Manager (PM2/Systemd):**
   - Ensure backend restarts automatically if it crashes
   - Background task will resume on restart

2. **Logging:**
   - Check logs at: `/var/log/pm2/whatsapp-backend-out.log`
   - Look for: "Processing scheduled campaign: {id}"

3. **Monitoring:**
   - Set up alerts for failed campaigns
   - Monitor backend uptime
   - Track scheduled campaign success rate

4. **Backup:**
   - Background task state is in database
   - No separate state to backup
   - Campaigns persist through restarts

---

## 🐛 Troubleshooting

### Problem: Campaign Not Sending at Scheduled Time

**Possible Causes:**
1. Backend server is down
2. User's BizChat credentials invalid
3. Daily limit exceeded
4. Database connection issue

**Solution:**
1. Check backend is running: `systemctl status backend` or `pm2 status`
2. Verify user credentials in Settings page
3. Check daily usage vs limit
4. Check backend logs for errors

---

### Problem: Campaign Sends Later Than Scheduled

**Cause:** 
- Background task checks every 60 seconds
- Up to 1 minute delay is normal

**Solution:**
- This is expected behavior
- For more precision, reduce sleep time in code (not recommended for production)

---

### Problem: Multiple Campaigns Processing at Same Time

**Cause:**
- Multiple campaigns scheduled for similar times

**Solution:**
- This is normal and expected
- Each campaign runs independently
- Rate limiting prevents API overload

---

## ✅ Summary

**What You Can Do Now:**
- ✅ Schedule campaigns for future date/time
- ✅ Automatic processing when time arrives
- ✅ No manual intervention needed
- ✅ Multiple scheduled campaigns supported
- ✅ Real-time status monitoring
- ✅ Respects daily limits
- ✅ Rate limiting applied (29 msg/sec)

**Background Task:**
- ✅ Runs every 60 seconds
- ✅ Starts automatically with backend
- ✅ Processes overdue campaigns
- ✅ Handles errors gracefully
- ✅ Logs all activities

**Production Ready:**
- ✅ Tested and working
- ✅ Handles server restarts
- ✅ Error handling implemented
- ✅ Rate limiting in place
- ✅ Daily usage tracking

---

## 📞 Support

If scheduled campaigns are not working:

1. **Check Logs:**
   ```bash
   tail -f /var/log/supervisor/backend.out.log
   # Look for: "Scheduled campaigns checker started"
   # Look for: "Processing scheduled campaign: {id}"
   ```

2. **Verify Backend Status:**
   ```bash
   sudo supervisorctl status backend
   # Should show: RUNNING
   ```

3. **Test Manually:**
   - Create campaign with 2-minute schedule
   - Monitor Campaign History page
   - Check status changes

---

**Feature Status:** ✅ **ACTIVE**  
**Version:** 2.1  
**Last Updated:** December 2024
