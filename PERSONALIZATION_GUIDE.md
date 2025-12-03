# 📧 Message Personalization Guide

## 🎯 New Feature: Personalized Names in Messages

You can now send personalized WhatsApp messages using the recipient's name from your Excel file!

---

## 📝 How It Works

### Step 1: Prepare Your Excel File

Your Excel file should have at least two columns:

| Phone | Name |
|-------|------|
| 9876543210 | John Smith |
| 9123456789 | Sarah Johnson |
| 9988776655 | Raj Kumar |

**Column Requirements:**
- **Phone column**: Can be named "phone", "Phone", "PHONE", "mobile", etc.
- **Name column**: Can be named "name", "Name", "NAME", "customer name", etc.

**Supported Formats:**
- `.xlsx` (Excel)
- `.xls` (Excel)
- `.csv` (CSV)

---

### Step 2: Use {name} Placeholder in Template Fields

When creating your campaign, use the `{name}` placeholder in any of the 5 template fields:

**Example 1: Simple Greeting**
```
Field 1: Hi {name}, your order is ready for pickup!
```

**Result:**
- John Smith receives: "Hi John Smith, your order is ready for pickup!"
- Sarah Johnson receives: "Hi Sarah Johnson, your order is ready for pickup!"
- Raj Kumar receives: "Hi Raj Kumar, your order is ready for pickup!"

**Example 2: Multiple Fields with Personalization**
```
Field 1: Dear {name}
Field 2: Your appointment is confirmed
Field 3: Thank you for choosing our service, {name}!
```

**Result for John Smith:**
- Field 1: "Dear John Smith"
- Field 2: "Your appointment is confirmed"
- Field 3: "Thank you for choosing our service, John Smith!"

---

## 💡 Tips & Best Practices

### ✅ DO:
- ✅ Use `{name}` exactly as shown (lowercase, with curly braces)
- ✅ Include name column in your Excel file
- ✅ Test with a small batch first
- ✅ Verify names are spelled correctly in Excel
- ✅ Use personalization in multiple fields if needed

### ❌ DON'T:
- ❌ Use `{Name}` or `{NAME}` (case-sensitive, must be lowercase)
- ❌ Use without name column in Excel (will show blank)
- ❌ Forget the curly braces `{}` around name
- ❌ Use special characters in names that might break formatting

---

## 📊 Example Use Cases

### 1. Order Confirmation
```
Field 1: Hi {name}! Your order #12345 has been confirmed.
Field 2: Estimated delivery: Tomorrow
Field 3: Thanks for shopping with us, {name}!
```

### 2. Appointment Reminder
```
Field 1: Dear {name}
Field 2: This is a reminder of your appointment on Dec 5, 2024 at 3:00 PM
Field 3: See you soon, {name}!
```

### 3. Promotional Campaign
```
Field 1: Hey {name}, we have a special offer just for you!
Field 2: Get 50% off on your next purchase
Field 3: Don't miss out, {name}. Offer valid till Dec 31!
```

### 4. Payment Reminder
```
Field 1: Hello {name}
Field 2: Your payment of ₹5,000 is due on Dec 10
Field 3: Please pay before the due date. Thank you, {name}!
```

### 5. Event Invitation
```
Field 1: Dear {name}, you're invited!
Field 2: Join us for our Annual Celebration on Dec 15
Field 3: RSVP by Dec 10. Hope to see you there, {name}!
```

---

## 🔄 Alternative: Copy-Paste Method

If you don't have an Excel file, you can also copy-paste data:

### Format:
```
phone,name
9876543210,John Smith
9123456789,Sarah Johnson
9988776655,Raj Kumar
```

**Steps:**
1. Go to Send Messages page
2. Click on "Copy-Paste" tab
3. Paste your data (comma-separated: phone,name)
4. Click "Load Recipients"
5. Use `{name}` in your template fields

---

## 📸 Screenshot Guide

### Where to Find the Feature:

1. **Login to the application**
2. **Navigate to "Send Messages"** from the top menu
3. **Look for the green alert box** that says:
   ```
   💡 Personalization: Use {name} to insert recipient's name from Excel.
   Example: "Hi {name}, your order is ready!" becomes "Hi John, your order is ready!"
   ```

### Visual Location:
```
┌──────────────────────────────────────────┐
│  Campaign Details                         │
│  ├─ Campaign Name                         │
│  ├─ Template Name                         │
│  └─ Template Language                     │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Template Fields                          │
│                                           │
│  ┌──────────────────────────────────────┐│
│  │ 💡 Personalization:                  ││
│  │ Use {name} to insert recipient's     ││
│  │ name from Excel                      ││
│  │                                      ││
│  │ Example: "Hi {name}, ..." becomes   ││
│  │ "Hi John, ..."                       ││
│  └──────────────────────────────────────┘│
│                                           │
│  Field 1: [Text area - use {name} here]  │
│  Field 2: [Text area - use {name} here]  │
│  ...                                      │
└──────────────────────────────────────────┘
```

---

## ⚙️ Technical Details

### How It Works Behind the Scenes:

1. **Excel Upload:** System reads the Excel file and extracts both phone and name columns
2. **Data Storage:** Each recipient is stored with their phone number and name
3. **Template Processing:** When sending, the system replaces `{name}` with the actual name
4. **API Call:** Personalized message is sent to BizChat API with unique values for each recipient

### Supported Placeholders:
- Currently: `{name}` ✅
- Future: More placeholders may be added (e.g., `{company}`, `{date}`, etc.)

---

## 🧪 Testing Your Personalization

### Test Checklist:

1. **Prepare Test Data:**
   ```
   Phone       | Name
   9999999999  | Test User 1
   8888888888  | Test User 2
   ```

2. **Create Test Campaign:**
   - Campaign Name: "Test Personalization"
   - Template: Your approved template
   - Field 1: "Hi {name}, this is a test message"

3. **Verify:**
   - Check if both recipients receive personalized messages
   - Confirm names appear correctly
   - Check for any formatting issues

4. **Production:**
   - Once tested, use with your actual recipient list
   - Monitor first few messages for accuracy

---

## ❓ Troubleshooting

### Problem: Name shows as blank or {name}

**Possible Causes:**
- Excel file doesn't have a "name" column
- Name column is empty for some recipients
- Typo in placeholder (e.g., `{Name}` instead of `{name}`)

**Solution:**
- Ensure Excel has a column with "name" in the header
- Fill in names for all recipients
- Use lowercase `{name}` exactly

---

### Problem: Special characters in names cause issues

**Example:** Name with apostrophe like "O'Brien"

**Solution:**
- System handles most special characters
- If issues persist, try removing special characters from names
- Report to support if specific characters cause problems

---

### Problem: Very long names get cut off

**Solution:**
- WhatsApp has message length limits
- Keep names reasonable length (< 50 characters)
- Test with longest name in your list first

---

## 📋 Branding Removal

As requested, all external branding has been removed:

✅ **Removed:**
- "Powered by BizChat API" from login page
- "Powered by BizChat API" from footer
- External branding references

✅ **Kept:**
- "© 2025 WhatsApp Bulk Messenger" (your app name)
- Functional elements and UI

---

## 🎯 Summary

**What You Get:**
- ✅ Personalized messages with recipient names
- ✅ Easy-to-use `{name}` placeholder
- ✅ Works with Excel/CSV files
- ✅ No external branding
- ✅ Same for all 5 template fields
- ✅ Automatic name substitution

**How to Use:**
1. Add name column to your Excel file
2. Upload Excel in Send Messages page
3. Use `{name}` in any template field
4. Send your campaign
5. Each recipient gets their name in the message!

---

**Last Updated:** December 2024  
**Feature Version:** 2.0  
**Status:** ✅ Active
