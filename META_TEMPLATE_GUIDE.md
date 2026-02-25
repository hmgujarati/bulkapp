# WhatsApp Meta Template Configuration Guide

This guide explains how to configure WhatsApp message templates in Meta Business Manager for use with the Reminder Bot feature. **Templates are required for messages sent outside the 24-hour customer service window.**

## Why Do You Need Meta Templates?

WhatsApp Business API has two types of messages:
1. **Session Messages**: Free-form messages within 24 hours of customer's last message
2. **Template Messages**: Pre-approved messages for business-initiated conversations (outside 24-hour window)

For reminders to work reliably, you need **approved Meta templates** since reminders are often sent when the customer hasn't messaged recently.

---

## Step 1: Access Meta Business Manager

1. Go to [Meta Business Suite](https://business.facebook.com)
2. Log in with your Facebook account
3. Navigate to **WhatsApp Manager** > **Message Templates**

---

## Step 2: Create Templates for Approval

Below are **ready-to-use template designs** that follow Meta's guidelines and have high approval rates.

### Template 1: Simple Reminder (RECOMMENDED)

**Template Name:** `reminder_alert`  
**Category:** `UTILITY`  
**Language:** `English`

```
Header: None

Body:
Reminder: {{1}}

Footer: None

Buttons: None
```

**Variables:**
- `{{1}}` = The reminder message (e.g., "Call John at 3pm")

**Why it works:** Simple, utility-focused, no promotional language.

---

### Template 2: Detailed Reminder with Time

**Template Name:** `scheduled_reminder`  
**Category:** `UTILITY`  
**Language:** `English`

```
Header: TEXT - "Reminder"

Body:
Hi {{1}},

This is your scheduled reminder:
{{2}}

Time: {{3}}

Footer: Sent via WhatsApp Reminder Bot

Buttons: None
```

**Variables:**
- `{{1}}` = Contact name
- `{{2}}` = Reminder message
- `{{3}}` = Scheduled time (e.g., "4:30 PM, 22 Jan 2025")

---

### Template 3: Professional Reminder

**Template Name:** `reminder_notification`  
**Category:** `UTILITY`  
**Language:** `English`

```
Header: None

Body:
Hello {{1}},

You have a reminder: {{2}}

Scheduled for: {{3}}

Reply STOP to unsubscribe.

Footer: None

Buttons: None
```

**Variables:**
- `{{1}}` = Contact name
- `{{2}}` = Reminder text
- `{{3}}` = Date and time

**Note:** Including "Reply STOP to unsubscribe" increases approval chances.

---

### Template 4: Task Reminder

**Template Name:** `task_reminder`  
**Category:** `UTILITY`  
**Language:** `English`

```
Header: None

Body:
Task Reminder

{{1}}

Due: {{2}}

Footer: None

Buttons: None
```

**Variables:**
- `{{1}}` = Task description
- `{{2}}` = Due date/time

---

### Template 5: Appointment Reminder

**Template Name:** `appointment_reminder`  
**Category:** `UTILITY`  
**Language:** `English`

```
Header: TEXT - "Appointment Reminder"

Body:
Hi {{1}},

This is a reminder for your upcoming appointment:
{{2}}

Date: {{3}}
Time: {{4}}

Please reply YES to confirm or NO to reschedule.

Footer: None

Buttons:
- Quick Reply: "YES"
- Quick Reply: "NO"
```

**Variables:**
- `{{1}}` = Customer name
- `{{2}}` = Appointment details
- `{{3}}` = Date
- `{{4}}` = Time

---

## Step 3: Submit for Approval

1. Fill in the template details exactly as shown
2. Add **sample content** for each variable:
   - `{{1}}` → "John"
   - `{{2}}` → "Call the dentist"
   - `{{3}}` → "3:00 PM"
3. Click **Submit**
4. Wait for Meta approval (usually 24-48 hours)

---

## Step 4: Configure in Reminder Bot

Once your template is approved:

1. Go to **Reminders** page in the app
2. Click **API Settings** button
3. Enter your template name in **Default Meta Template ID**
   - Example: `reminder_alert` or `scheduled_reminder`
4. Click **Save Settings**

---

## Template Approval Best Practices

### DO:
- Use UTILITY category for reminders
- Keep messages clear and concise
- Include unsubscribe option for marketing
- Use professional, neutral language
- Provide accurate sample content

### DON'T:
- Use promotional or marketing language
- Include URLs in non-marketing templates
- Use all caps or excessive punctuation
- Make templates too long
- Use emojis excessively (1-2 max is fine)

---

## Template Status Reference

| Status | Meaning | Action |
|--------|---------|--------|
| **Approved** | Ready to use | Configure in app |
| **Pending** | Under review | Wait 24-48 hours |
| **Rejected** | Did not meet guidelines | Read feedback, modify, resubmit |
| **Paused** | Temporarily disabled | Check quality rating |

---

## Common Rejection Reasons & Fixes

| Rejection Reason | Fix |
|-----------------|-----|
| "Content not allowed" | Remove promotional language |
| "Variable format incorrect" | Use `{{1}}` format, not `{1}` or `[1]` |
| "Category mismatch" | Change from MARKETING to UTILITY |
| "Sample content missing" | Add realistic sample values |
| "Opt-out missing" | Add "Reply STOP to unsubscribe" |

---

## How Templates Work with Reminder Bot

When the Reminder Bot sends a message:

1. **Within 24-hour window**: Sends as session message (free-form text)
2. **Outside 24-hour window**: Uses your configured template

The bot automatically:
- Fills in the template variables with reminder details
- Handles the API call to BizChat
- Tracks delivery status

---

## Testing Your Template

After approval, test by:

1. Create a reminder for 1-2 minutes in the future
2. Wait for the reminder to be sent
3. Check if the message was delivered
4. Verify the format looks correct

If messages fail, check:
- Template name matches exactly (case-sensitive)
- BizChat API credentials are correct
- Template is still in "Approved" status

---

## Need Help?

- [Meta Business Help Center](https://www.facebook.com/business/help)
- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp)
- [Template Guidelines](https://developers.facebook.com/docs/whatsapp/message-templates/guidelines/)
- Contact your BizChat API provider for integration support
