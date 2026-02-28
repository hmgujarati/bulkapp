# WhatsApp Meta Template Configuration Guide

This guide explains how to configure WhatsApp message templates for the Reminder Bot.

## Your Approved Template

Your template has been approved by Meta. Here are the details:

**Template Name:** `reminder_alert`  
**Language:** `en_US`  
**Category:** `UTILITY`  
**Header:** `Reminder Alert`

```
Hi There!

Reminder: {{1}}
Time: {{2}}
Date: {{3}}

- Your WhatsApp Assistant
```

**Variables:**
- `{{1}}` = Reminder message (e.g., "Call John")
- `{{2}}` = Time (e.g., "3:00 PM")
- `{{3}}` = Date (e.g., "25 Feb 2025")

---

## How to Configure in the App

1. Go to **Reminders** page
2. Click **API Settings** button
3. Enter `reminder_alert` in the **Default Meta Template ID** field
4. Click **Save Settings**

---

## How Templates Work

- **Within 24-hour window**: Messages are sent as free-form session messages
- **Outside 24-hour window**: Messages use your approved template

The Reminder Bot automatically fills in the template variables with:
- `{{1}}` = Your reminder message
- `{{2}}` = Scheduled time
- `{{3}}` = Scheduled date

---

## Need Help?

- [Meta Business Help Center](https://www.facebook.com/business/help)
- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp)
