# 📑 Templates with Media & Location Guide

## 🎯 Overview

The "My Templates" feature now supports **saving and reusing media URLs and location data**! Create complete campaign templates including images, videos, documents, and location information for instant reuse.

---

## ✨ What's New

### Previous Template Features:
- ✅ Template name
- ✅ BizChat template reference
- ✅ 5 text fields

### NEW Template Features:
- ✅ **Header Image URL**
- ✅ **Header Video URL**
- ✅ **Header Document URL**
- ✅ **Document Name**
- ✅ **Header Field 1** (with {name} support)
- ✅ **GPS Coordinates** (Latitude/Longitude)
- ✅ **Location Name**
- ✅ **Location Address**

---

## 🔄 Complete Workflow

### Method 1: Upload → Save → Reuse

**Step 1: Upload Media in Send Messages**
1. Go to **Send Messages** page
2. Scroll to "Media & Location" section
3. Upload your files:
   - Image: product.jpg
   - Video: tutorial.mp4
   - Document: catalog.pdf
4. **Copy the URLs** shown after upload

**Step 2: Fill Campaign Details**
1. Campaign Name: "Product Launch"
2. Template Name: "product_promo"
3. Template Fields: Fill field1-5
4. Media: Files already uploaded (URLs shown)
5. Location: Enter GPS and address

**Step 3: Save as Template**
1. Click **"Save as Template"** button
2. Enter template name: "My Product Promo"
3. Template is saved with ALL fields including media URLs

**Step 4: Reuse Later**
1. Go to Send Messages page
2. Click "Load Saved Template" dropdown
3. Select "My Product Promo"
4. ✅ Everything loads: fields, media URLs, location!
5. Just add recipients and send

---

### Method 2: Create Template from My Templates Page

**Step 1: Go to My Templates**
1. Click **"My Templates"** in navigation
2. Click **"+ New Template"** button

**Step 2: Fill Template Details**
```
Template Name: "Holiday Promotion"
BizChat Template: "holiday_sale"
Language: English

Fields:
- Field 1: "Hi {name}, special holiday offer!"
- Field 2: "Get 30% discount"
- Field 3-5: (optional)

Media URLs:
- Header Image: https://yourdomain.com/uploads/images/holiday.jpg
- Header Video: (optional)
- Header Document: (optional)

Location:
- Latitude: 40.7128
- Longitude: -74.0060
- Name: "Our NYC Store"
- Address: "123 Fifth Avenue, New York"
```

**Step 3: Save Template**
1. Click **"Save Template"**
2. Template saved in database

**Step 4: Use Template**
1. Go to Send Messages
2. Load template from dropdown
3. All fields populate automatically
4. Add recipients and send!

---

## 📝 Real-World Examples

### Example 1: E-commerce Product Launch

**Template Name:** "New Product Launch"

```
BizChat Template: product_announcement
Language: English

Text Fields:
- Field 1: Hi {name}, discover our new collection!
- Field 2: Limited time: 25% OFF
- Field 3: Use code: NEW25
- Field 4: Shop now
- Field 5: Free shipping on orders over $50

Media:
- Header Image: https://mystore.com/uploads/images/new-product.jpg
  (Product photo uploaded earlier)

Location:
- Name: Our Main Store
- Address: 456 Market Street, San Francisco
- Latitude: 37.7749
- Longitude: -122.4194
```

**Reuse Scenario:**
- Every week, just update the image URL
- Keep all other fields same
- Load template → Update image → Send

---

### Example 2: Event Invitation

**Template Name:** "Monthly Event Invite"

```
BizChat Template: event_invitation
Language: English

Text Fields:
- Field 1: Dear {name}, you're invited!
- Field 2: Join us for our monthly meetup
- Field 3: Date: First Saturday of every month
- Field 4: Time: 6:00 PM
- Field 5: RSVP by clicking the link

Media:
- Header Document: https://mysite.com/uploads/documents/event-details.pdf
  (Event brochure)
- Document Name: Event Details.pdf

Location:
- Name: Community Center Hall
- Address: 789 Park Avenue
- Latitude: 34.0522
- Longitude: -118.2437
```

**Reuse Scenario:**
- Monthly event with same details
- Just load template and send
- Maybe update date field only

---

### Example 3: Store Location Share

**Template Name:** "Visit Our Store"

```
BizChat Template: location_share
Language: English

Text Fields:
- Field 1: Hello {name}!
- Field 2: Visit our new store location
- Field 3: We're now closer to you
- Field 4: Special opening discount: 15%
- Field 5: Valid for first 100 customers

Media:
- Header Image: https://store.com/uploads/images/store-front.jpg
- Header Video: https://store.com/uploads/videos/store-tour.mp4

Location:
- Name: Our New Branch
- Address: 321 Downtown Street, Suite 100
- Latitude: 40.7589
- Longitude: -73.9851
```

**Reuse Scenario:**
- Opening new branches
- Update only location coordinates
- Keep message and media same

---

## 🎨 UI Screenshots Flow

### In My Templates Page:

```
┌────────────────────────────────────────┐
│ My Templates                    [+ New]│
├────────────────────────────────────────┤
│                                        │
│ [Template Card: Product Launch]        │
│ • Template: product_promo              │
│ • Has: Image ✓, Location ✓            │
│ [Edit] [Delete]                        │
│                                        │
│ [Template Card: Holiday Sale]          │
│ • Template: holiday_offer              │
│ • Has: Video ✓, Document ✓            │
│ [Edit] [Delete]                        │
└────────────────────────────────────────┘
```

### Creating/Editing Template:

```
┌────────────────────────────────────────┐
│ New Template                     [X]   │
├────────────────────────────────────────┤
│ Template Name: [_________________]     │
│ BizChat Template: [_____________]      │
│ Language: [English ▼]                  │
│                                        │
│ Field 1: [____________________]        │
│ Field 2: [____________________]        │
│ ...                                    │
│                                        │
│ ─── Media & Location (Optional) ───    │
│                                        │
│ Header Image URL:                      │
│ [https://domain.com/uploads/...]       │
│                                        │
│ Header Video URL:                      │
│ [https://domain.com/uploads/...]       │
│                                        │
│ Header Document URL:                   │
│ [https://domain.com/uploads/...]       │
│                                        │
│ Latitude: [40.7128]  Longitude: [-74]  │
│ Location Name: [Our Store_______]      │
│ Address: [123 Main St___________]      │
│                                        │
│ 💡 Tip: Upload files in Send Messages,│
│    then copy URLs here                 │
│                                        │
│ [Save Template] [Cancel]               │
└────────────────────────────────────────┘
```

### In Send Messages (Load Template):

```
┌────────────────────────────────────────┐
│ Campaign Details                       │
│                                        │
│ Load Saved Template: [Select... ▼]    │
│   → Product Launch ✓                  │
│   → Holiday Sale                       │
│   → Visit Our Store                    │
│                                        │
│ (All fields auto-populate when selected)│
└────────────────────────────────────────┘
```

---

## 💾 How Media URLs Are Stored

### Database Structure:

```javascript
{
  "id": "uuid-123",
  "userId": "user-uuid",
  "name": "Product Launch Template",
  "templateName": "product_promo",
  "templateLanguage": "en",
  "field1": "Hi {name}, check this out!",
  "field2": "Special offer",
  "field3": "",
  "field4": "",
  "field5": "",
  // NEW: Media fields
  "header_image": "https://domain.com/uploads/images/uuid-456.jpg",
  "header_video": "https://domain.com/uploads/videos/uuid-789.mp4",
  "header_document": "https://domain.com/uploads/documents/uuid-012.pdf",
  "header_document_name": "catalog.pdf",
  "header_field_1": "Special for {name}",
  // NEW: Location fields
  "location_latitude": "40.7128",
  "location_longitude": "-74.0060",
  "location_name": "NYC Store",
  "location_address": "123 Fifth Ave, New York",
  "createdAt": "2024-12-03T10:00:00Z",
  "updatedAt": "2024-12-03T10:00:00Z"
}
```

---

## 🔧 Technical Implementation

### Backend Changes:

**Model Updates:**
```python
class SavedTemplate(BaseModel):
    # ... existing fields ...
    
    # NEW: Media fields
    header_image: Optional[str] = None
    header_video: Optional[str] = None
    header_document: Optional[str] = None
    header_document_name: Optional[str] = None
    header_field_1: Optional[str] = None
    
    # NEW: Location fields
    location_latitude: Optional[str] = None
    location_longitude: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
```

**API Endpoints:**
- `POST /api/saved-templates` - Create (now includes media/location)
- `GET /api/saved-templates` - List all
- `PUT /api/saved-templates/{id}` - Update (now includes media/location)
- `DELETE /api/saved-templates/{id}` - Delete

### Frontend Changes:

**My Templates Page:**
- ✅ Form expanded with media/location fields
- ✅ Text inputs for URLs (not file upload)
- ✅ All fields optional
- ✅ Validation for URLs

**Send Messages Page:**
- ✅ "Save as Template" button added
- ✅ Load template populates all fields including media
- ✅ Shows confirmation toast

---

## 📊 Workflow Comparison

### Before (Without Template Media):
```
Day 1: Upload image → Fill fields → Send campaign
Day 2: Upload SAME image again → Fill SAME fields → Send
Day 3: Upload SAME image again → Fill SAME fields → Send
❌ Repetitive work!
```

### After (With Template Media):
```
Day 1: Upload image → Fill fields → Save as Template
Day 2: Load template → All fields filled! → Just add recipients → Send
Day 3: Load template → All fields filled! → Just add recipients → Send
✅ Save hours of work!
```

---

## 💡 Best Practices

### 1. **Naming Convention**
- Use descriptive names: "Holiday Sale 2024" not "Template 1"
- Include purpose: "Product Launch - Electronics"
- Include version if iterating: "Event Invite v2"

### 2. **Media Management**
```
Good Practice:
✅ Upload file once
✅ Copy URL
✅ Save in template
✅ Reuse URL across campaigns

Bad Practice:
❌ Upload same file multiple times
❌ Manually enter URLs each time
```

### 3. **Template Organization**
```
Create templates for:
✅ Weekly promotions
✅ Monthly events
✅ Seasonal campaigns
✅ Location shares
✅ Product categories
```

### 4. **URL Management**
```
Tip: Keep a spreadsheet
┌─────────────────┬──────────────────────┐
│ Media Type      │ URL                  │
├─────────────────┼──────────────────────┤
│ Logo            │ .../uploads/logo.png │
│ Product Photo   │ .../uploads/prod.jpg │
│ Store Video     │ .../uploads/tour.mp4 │
│ Catalog PDF     │ .../uploads/cat.pdf  │
└─────────────────┴──────────────────────┘
```

---

## ⚠️ Important Notes

### 1. **URLs vs File Upload**
- My Templates stores **URLs only** (not files)
- Files must be uploaded first in Send Messages page
- Then copy URL to template

### 2. **File Persistence**
- Files stay on server at `/uploads/`
- URLs remain valid permanently
- Delete old files manually if needed

### 3. **Template Editing**
- Can update media URLs anytime
- No need to re-upload files
- Just update URL in template

### 4. **Bulk Updates**
- If you need to change media for multiple templates
- Upload new file once
- Update URLs in all templates

---

## 🧪 Testing Guide

### Test 1: Create Template with Media

1. **Upload Media:**
   ```
   Go to Send Messages
   Upload image: test.jpg
   Copy URL: https://domain.com/uploads/images/uuid.jpg
   ```

2. **Save Template:**
   ```
   Fill all fields
   Paste image URL
   Click "Save as Template"
   Name: "Test Template"
   ```

3. **Verify:**
   ```
   Go to My Templates
   Find "Test Template"
   Click Edit
   Verify image URL is saved
   ```

### Test 2: Load Template

1. **Load:**
   ```
   Go to Send Messages
   Select "Test Template" from dropdown
   ```

2. **Verify:**
   ```
   ✓ Template name populated
   ✓ All fields populated
   ✓ Image URL populated
   ✓ Preview button works
   ```

### Test 3: Update Template

1. **Upload New Media:**
   ```
   Upload new image
   Copy new URL
   ```

2. **Update Template:**
   ```
   Go to My Templates
   Edit "Test Template"
   Replace image URL
   Save
   ```

3. **Verify:**
   ```
   Load template again
   New image URL shown
   Old URL replaced
   ```

---

## 🔄 Migration Notes

### For Existing Templates:
- Old templates still work perfectly
- Media/location fields are **optional**
- No need to update old templates
- Can add media to existing templates anytime

### Backward Compatibility:
- ✅ Old templates load without errors
- ✅ New fields show as empty
- ✅ Can save without media/location
- ✅ Full flexibility

---

## ✅ Summary

**What You Can Do Now:**

**Save in Templates:**
- ✅ Template configuration
- ✅ Text fields (1-5)
- ✅ Image URLs
- ✅ Video URLs
- ✅ Document URLs
- ✅ GPS coordinates
- ✅ Location name & address

**Reuse Instantly:**
- ✅ Load template → All fields fill automatically
- ✅ Media URLs already there
- ✅ Location data already there
- ✅ Just add recipients and send!

**Save Time:**
- ✅ No re-uploading same files
- ✅ No re-entering same data
- ✅ Consistent campaigns
- ✅ Quick turnaround

**Production Ready:**
- ✅ Backend model updated
- ✅ Frontend UI updated
- ✅ API endpoints working
- ✅ Full testing done

---

**Feature Status:** ✅ **ACTIVE**  
**Version:** 4.0  
**Last Updated:** December 2024
