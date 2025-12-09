# 📸 Media & Location Feature Guide

## 🎯 Overview

WhatsApp Bulk Messenger now supports sending **rich media content** and **location data** with your campaigns! Send images, videos, documents, and location pins along with your text messages.

---

## ✨ New Features Added

### 1. **Media Attachments**
- 📷 **Header Image**: JPG, PNG, GIF, WebP
- 🎥 **Header Video**: MP4, MOV, AVI, MKV, WebM
- 📄 **Header Document**: PDF, DOC, DOCX, XLS, XLSX, TXT, CSV
- 📝 **Header Field 1**: Custom text field (supports `{name}` personalization)

### 2. **Location Data**
- 📍 **Latitude/Longitude**: GPS coordinates
- 🏪 **Location Name**: Name of the place
- 🗺️ **Location Address**: Full address

---

## 📤 How File Upload Works

### Backend Implementation:
1. **Upload Endpoint**: `/api/upload/media`
2. **Storage**: Files saved in `/app/backend/uploads/`
   - Images: `/uploads/images/`
   - Videos: `/uploads/videos/`
   - Documents: `/uploads/documents/`
3. **URL Generation**: Returns full URL for use in campaigns
4. **Static Serving**: Files accessible via `/uploads/` route

### File Organization:
```
/app/backend/uploads/
├── images/
│   ├── uuid-1.jpg
│   ├── uuid-2.png
│   └── ...
├── videos/
│   ├── uuid-1.mp4
│   ├── uuid-2.mov
│   └── ...
└── documents/
    ├── uuid-1.pdf
    ├── uuid-2.docx
    └── ...
```

---

## 🎨 User Interface

### Location in App:
1. Navigate to **Send Messages** page
2. Fill in Campaign Details and Template Fields
3. **NEW SECTION**: "Media & Location (Optional)"
4. Upload files or enter location data
5. Send campaign as normal

### UI Layout:
```
┌─────────────────────────────────────┐
│ Campaign Details                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Template Fields                      │
│ (with {name} personalization)        │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Media & Location (Optional) ←NEW!   │
│ ├─ Header Image [Upload]            │
│ ├─ Header Video [Upload]            │
│ ├─ Header Document [Upload]         │
│ ├─ Header Field 1 [Text]            │
│ ├─ Latitude                          │
│ ├─ Longitude                         │
│ ├─ Location Name                     │
│ └─ Location Address                  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ Add Recipients                       │
└─────────────────────────────────────┘
```

---

## 📝 Usage Examples

### Example 1: Product Promotion with Image
```
Campaign: New Product Launch
Template: product_announcement
Header Image: [Upload product.jpg]
Field 1: Hi {name}, check out our new product!
Field 2: Special discount for you: 20% OFF
Recipients: Upload customer list
```

### Example 2: Video Message
```
Campaign: Tutorial Video
Template: video_message
Header Video: [Upload tutorial.mp4]
Field 1: Dear {name}
Field 2: Watch this helpful tutorial
Recipients: Paste phone numbers
```

### Example 3: Document with Location
```
Campaign: Event Invitation
Template: event_invite
Header Document: [Upload invitation.pdf]
Location Name: Grand Hotel
Location Address: 123 Main Street, City
Latitude: 40.7128
Longitude: -74.0060
Field 1: Hello {name}, you're invited!
Recipients: Upload guest list
```

### Example 4: Store Location Share
```
Campaign: Store Opening
Template: location_share
Location Name: Our New Store
Location Address: 456 Market Street
Latitude: 37.7749
Longitude: -122.4194
Field 1: Visit us at our new location, {name}!
```

---

## 🔧 Technical Implementation

### API Payload Structure:

When you send a campaign with media/location, the payload includes:

```json
{
  "campaignName": "Product Launch",
  "templateName": "product_promo",
  "recipients": [
    {
      "phone": "+919876543210",
      "name": "John",
      "field_1": "Hi John, check this out!",
      "field_2": "20% discount"
    }
  ],
  "header_image": "https://yourdomain.com/uploads/images/uuid.jpg",
  "header_video": "https://yourdomain.com/uploads/videos/uuid.mp4",
  "header_document": "https://yourdomain.com/uploads/documents/uuid.pdf",
  "header_document_name": "product-catalog.pdf",
  "header_field_1": "Special for {name}",
  "location_latitude": "22.22",
  "location_longitude": "22.22",
  "location_name": "Our Store",
  "location_address": "123 Main St, City"
}
```

### BizChat API Integration:

These fields are automatically passed to BizChat API:
```json
{
  "vendor_uid": "your-vendor-uid",
  "access_token": "your-token",
  "phone": "+919876543210",
  "template_name": "product_promo",
  "template_language": "en",
  "header_image": "https://yourdomain.com/uploads/images/uuid.jpg",
  "header_video": "https://yourdomain.com/uploads/videos/uuid.mp4",
  "header_document": "https://yourdomain.com/uploads/documents/uuid.pdf",
  "header_document_name": "product-catalog.pdf",
  "header_field_1": "Special for John",
  "location_latitude": "22.22",
  "location_longitude": "22.22",
  "location_name": "Our Store",
  "location_address": "123 Main St, City",
  "field_1": "Hi John, check this out!",
  "field_2": "20% discount"
}
```

---

## 📊 Supported File Formats

### Images:
- `.jpg` / `.jpeg`
- `.png`
- `.gif`
- `.webp`

### Videos:
- `.mp4` (Recommended)
- `.mov`
- `.avi`
- `.mkv`
- `.webm`

### Documents:
- `.pdf` (Recommended)
- `.doc` / `.docx`
- `.xls` / `.xlsx`
- `.txt`
- `.csv`

---

## ⚠️ Important Notes

### 1. **File Size Limits**
- Images: Recommended < 5MB
- Videos: Recommended < 16MB
- Documents: Recommended < 10MB
- **Note**: WhatsApp has its own limits; very large files may fail

### 2. **File Storage**
- Files are stored on your server at `/app/backend/uploads/`
- Each file gets a unique UUID name
- Original filename preserved for documents

### 3. **URL Format**
- Files uploaded in development: `http://localhost:8001/uploads/...`
- Files uploaded in production: `https://yourdomain.com/uploads/...`
- URLs are automatically converted to full URLs

### 4. **Media is Campaign-Wide**
- Same media sent to ALL recipients in the campaign
- Cannot send different images to different people
- Use personalization in text fields for customization

### 5. **Template Requirements**
- Your BizChat template must support media/location
- Template must be pre-approved with media placeholders
- Check BizChat dashboard for template configuration

---

## 🧪 Testing

### Test Media Upload:

1. **Upload Test Image:**
   - Go to Send Messages
   - Click on "Header Image" file input
   - Select an image file
   - Wait for upload confirmation
   - Should see: "✓ Image uploaded"

2. **Preview Uploaded File:**
   - Click "Preview" button next to file input
   - File opens in new tab
   - Verify it's the correct file

3. **Send Test Campaign:**
   - Upload media
   - Add test phone number
   - Fill template fields
   - Send campaign
   - Check if message received with media

### Test Location:

1. **Get GPS Coordinates:**
   - Google Maps → Right-click location → Copy coordinates
   - Format: `latitude, longitude`
   - Example: `40.7128, -74.0060`

2. **Enter Location Data:**
   - Latitude: `40.7128`
   - Longitude: `-74.0060`
   - Name: `New York City`
   - Address: `Manhattan, NY`

3. **Send and Verify:**
   - Send campaign
   - Recipient should see location pin
   - Tapping pin opens in maps

---

## 🔐 Security Considerations

### 1. **File Validation**
- ✅ File extension checked
- ✅ File type validated
- ✅ Only allowed formats accepted

### 2. **Access Control**
- ✅ Authentication required for upload
- ✅ Only logged-in users can upload
- ✅ Files accessible via public URL (for WhatsApp delivery)

### 3. **Storage**
- Files stored with random UUID names
- Original filename not exposed in URL
- Directory permissions set to 755

### 4. **Production Recommendations**
- Set up file size limits in Nginx
- Implement file scanning for viruses
- Regular cleanup of old unused files
- Consider cloud storage (S3, GCS) for large scale

---

## 🚀 Production Deployment

### Update Your Server:

1. **Ensure Upload Directory Exists:**
   ```bash
   mkdir -p /var/www/whatsapp-app/backend/uploads/{images,videos,documents}
   chmod -R 755 /var/www/whatsapp-app/backend/uploads
   ```

2. **Update Nginx (if needed):**
   ```nginx
   # In your site config
   location /uploads/ {
       alias /var/www/whatsapp-app/backend/uploads/;
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   ```

3. **Test File Upload:**
   ```bash
   curl -X POST https://yourdomain.com/api/upload/media \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@test.jpg" \
     -F "media_type=image"
   ```

4. **Monitor Storage:**
   ```bash
   # Check disk usage
   du -sh /var/www/whatsapp-app/backend/uploads/
   
   # Count files
   find /var/www/whatsapp-app/backend/uploads/ -type f | wc -l
   ```

---

## 🧹 Maintenance

### Cleanup Old Files:

Create a cleanup script for files older than 30 days:

```bash
#!/bin/bash
# /usr/local/bin/cleanup-uploads.sh

UPLOAD_DIR="/var/www/whatsapp-app/backend/uploads"
DAYS=30

find "$UPLOAD_DIR" -type f -mtime +$DAYS -delete

echo "Cleaned up files older than $DAYS days"
```

Schedule with cron:
```bash
# Daily at 3 AM
0 3 * * * /usr/local/bin/cleanup-uploads.sh >> /var/log/cleanup-uploads.log 2>&1
```

---

## 📞 Troubleshooting

### Problem: File upload fails

**Solutions:**
1. Check disk space: `df -h`
2. Verify directory permissions: `ls -la /app/backend/uploads`
3. Check file size (may be too large)
4. Verify file type is supported

### Problem: Uploaded file URL not working

**Solutions:**
1. Check file exists: `ls /app/backend/uploads/images/`
2. Verify static file mounting in server.py
3. Check Nginx configuration
4. Verify REACT_APP_BACKEND_URL is correct

### Problem: WhatsApp not displaying media

**Solutions:**
1. Verify template supports media
2. Check file URL is publicly accessible
3. Ensure file size within WhatsApp limits
4. Verify file format is supported by WhatsApp

---

## ✅ Summary

**New Capabilities:**
- ✅ Upload and send images
- ✅ Upload and send videos
- ✅ Upload and send documents
- ✅ Send location pins with lat/long
- ✅ Add location name and address
- ✅ Files stored on your server
- ✅ Full URL generation
- ✅ Preview uploaded files
- ✅ Support for {name} personalization in header fields

**Technical:**
- ✅ Backend upload endpoint: `/api/upload/media`
- ✅ Static file serving: `/uploads/`
- ✅ Automatic file validation
- ✅ UUID-based file naming
- ✅ Multi-format support

**Production Ready:**
- ✅ Secure upload with authentication
- ✅ File type validation
- ✅ Error handling
- ✅ Full integration with campaign system

---

**Feature Status:** ✅ **ACTIVE**  
**Version:** 3.0  
**Last Updated:** December 2024
