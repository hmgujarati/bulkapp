# WhatsApp Meta Template Configuration Guide

This guide explains how to configure WhatsApp message templates in Meta Business Manager for use with the Reminder Bot feature.

## What are Meta Templates?

WhatsApp Business API requires pre-approved message templates for business-initiated conversations (messages sent outside the 24-hour customer service window). These templates must be approved by Meta before they can be used.

## Step 1: Access Meta Business Manager

1. Go to [Meta Business Suite](https://business.facebook.com)
2. Log in with your Facebook account
3. Navigate to your WhatsApp Business Account

## Step 2: Create a New Template

1. In the left menu, click **WhatsApp Manager**
2. Click **Message Templates** (or go to **Account Tools > Message Templates**)
3. Click **Create Template**

## Step 3: Configure Template Settings

### Basic Information:
- **Category**: Select `UTILITY` for reminder messages
- **Name**: Use a simple name like `reminder_notification` (lowercase, underscores only)
- **Language**: Select your target language (e.g., English)

### Template Content:
For a reminder template, you can use:

```
Header (Optional): 🔔 Reminder

Body: 
Hi {{1}},

This is a reminder: {{2}}

Scheduled for: {{3}}

Footer (Optional): Sent via WhatsApp Bulk Messenger
```

Where:
- `{{1}}` = Recipient name
- `{{2}}` = Reminder message
- `{{3}}` = Scheduled time

### Example Templates:

**Simple Reminder:**
```
Body: Reminder: {{1}}
```

**Detailed Reminder:**
```
Header: ⏰ Reminder Alert

Body: Hello {{1}},

You asked to be reminded about:
{{2}}

Best regards,
Your Reminder Bot
```

## Step 4: Submit for Approval

1. Review your template
2. Click **Submit**
3. Wait for Meta approval (usually 24-48 hours)

## Step 5: Configure in Reminder Bot

Once your template is approved:

1. Go to **Reminders** page in the app
2. Click **Settings** (gear icon)
3. Enter your template name in **Default Meta Template ID**
   - Example: `reminder_notification`
4. Click **Save Settings**

## Template Status

- **Approved**: Ready to use ✅
- **Pending**: Waiting for Meta review ⏳
- **Rejected**: Needs modification ❌

## Tips for Approval

1. **Keep it professional**: Avoid promotional language
2. **Be clear**: State the purpose clearly
3. **Use variables**: Include `{{1}}`, `{{2}}` etc. for dynamic content
4. **Follow guidelines**: Review [Meta's Template Guidelines](https://developers.facebook.com/docs/whatsapp/message-templates/guidelines/)

## 24-Hour Session Window

If a customer has messaged you within the last 24 hours, you can send messages without a template. The Reminder Bot automatically uses:
- **Template messages** for business-initiated conversations
- **Session messages** when within the 24-hour window (if configured)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Template rejected | Review rejection reason, modify and resubmit |
| Template not working | Verify exact template name matches |
| Messages failing | Check BizChat API credentials |

## Need Help?

- [Meta Business Help Center](https://www.facebook.com/business/help)
- [WhatsApp Business API Documentation](https://developers.facebook.com/docs/whatsapp)
- Contact your BizChat API provider for integration support
