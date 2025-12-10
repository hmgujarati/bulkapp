# 🔧 Template Media URL Fix Guide

## 🐛 Problem

If you're seeing **404 Not Found** errors when clicking image/video/document links in templates, it's because:

1. **Old URLs missing `/api/` prefix:** 
   - ❌ `https://domain.com/uploads/images/file.jpg`
   - ✅ `https://domain.com/api/uploads/images/file.jpg`

2. **Files were deleted** from server but URL still in template

3. **Browser cache** showing old content

---

## ✅ Solution

### Option 1: Re-upload Files (Recommended)

1. **Go to My Templates**
2. **Edit the template** with broken media
3. **Select media type** (image/video/document)
4. **Upload file again**
5. **Save template**
6. ✅ **New URL will have `/api/` prefix**

### Option 2: Fix URLs Manually

1. **Go to My Templates**
2. **Edit template**
3. **Find the URL field**
4. **Add `/api/` after domain:**
   ```
   Before: https://domain.com/uploads/images/file.jpg
   After:  https://domain.com/api/uploads/images/file.jpg
   ```
5. **Save template**

### Option 3: Database Migration (Already Done)

A migration script has been run to fix all existing templates. Any templates created AFTER this fix will have correct URLs automatically.

---

## 🧪 How to Test

### Test Template Media:

1. **Go to My Templates**
2. **Click Edit on any template with media**
3. **Look at the URL field:**
   - ✅ Should contain `/api/uploads/`
   - ❌ If only `/uploads/` → needs fixing

4. **For images, copy URL and open in browser:**
   - ✅ Image loads → Working!
   - ❌ 404 error → File deleted or URL wrong

### Test New Uploads:

1. **Create new template**
2. **Select media type**
3. **Upload a file**
4. **Check generated URL:**
   ```
   Should be: https://domain.com/api/uploads/type/uuid.ext
   ```
5. **Click to preview → should open file**

---

## 🔍 Common Issues

### Issue 1: "404 Not Found" for old templates

**Cause:** Template has old URL format without `/api/`

**Solution:** 
- Re-upload the file in the template
- OR manually add `/api/` to the URL
- OR delete and recreate template

### Issue 2: "404 Not Found" for newly uploaded files

**Cause:** File upload might have failed

**Solution:**
1. Check file size (should be < 16MB for videos)
2. Check file format is supported
3. Try uploading again
4. Check browser console for errors

### Issue 3: File was uploaded but shows 404

**Cause:** File might have been deleted from server

**Solution:**
- Re-upload the file
- Check server disk space: `df -h`
- Verify file exists: `ls /app/backend/uploads/images/`

### Issue 4: Image shows broken in Send Messages

**Cause:** Template URL is old format

**Solution:**
- Load template again (will auto-fix)
- Or upload new image directly in Send Messages

---

## 🛠️ For Administrators

### Check if migration needed:

```bash
# SSH into server
cd /app/backend

# Run this Python script:
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_urls():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["whatsapp_bulk_messenger"]
    
    templates = await db.saved_templates.find({}).to_list(1000)
    
    needs_fix = 0
    for template in templates:
        if (template.get('header_image') and '/uploads/' in template['header_image'] and '/api/uploads/' not in template['header_image']):
            needs_fix += 1
            print(f"❌ {template['name']}: image needs fix")
        if (template.get('header_video') and '/uploads/' in template['header_video'] and '/api/uploads/' not in template['header_video']):
            needs_fix += 1
            print(f"❌ {template['name']}: video needs fix")
        if (template.get('header_document') and '/uploads/' in template['header_document'] and '/api/uploads/' not in template['header_document']):
            needs_fix += 1
            print(f"❌ {template['name']}: document needs fix")
    
    print(f"\nTotal templates needing fix: {needs_fix}")
    client.close()

asyncio.run(check_urls())
EOF
```

### Run migration to fix all URLs:

```bash
cd /app/backend

python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_urls():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["whatsapp_bulk_messenger"]
    
    templates = await db.saved_templates.find({}).to_list(1000)
    
    fixed_count = 0
    for template in templates:
        needs_update = False
        update_data = {}
        
        # Fix image URL
        if template.get('header_image') and '/uploads/' in template['header_image']:
            if '/api/uploads/' not in template['header_image']:
                update_data['header_image'] = template['header_image'].replace('/uploads/', '/api/uploads/')
                needs_update = True
        
        # Fix video URL
        if template.get('header_video') and '/uploads/' in template['header_video']:
            if '/api/uploads/' not in template['header_video']:
                update_data['header_video'] = template['header_video'].replace('/uploads/', '/api/uploads/')
                needs_update = True
        
        # Fix document URL
        if template.get('header_document') and '/uploads/' in template['header_document']:
            if '/api/uploads/' not in template['header_document']:
                update_data['header_document'] = template['header_document'].replace('/uploads/', '/api/uploads/')
                needs_update = True
        
        if needs_update:
            await db.saved_templates.update_one(
                {"_id": template['_id']},
                {"$set": update_data}
            )
            fixed_count += 1
            print(f"Fixed: {template.get('name', 'Unnamed')}")
    
    print(f"\n✅ Fixed {fixed_count} templates")
    client.close()

asyncio.run(fix_urls())
EOF
```

---

## 📋 URL Format Reference

### Correct URL Format:

```
Development:
http://localhost:8001/api/uploads/images/uuid.jpg

Production:
https://your-domain.com/api/uploads/images/uuid.jpg
```

### URL Structure:

```
https://domain.com/api/uploads/{type}/{uuid}.{ext}
                    └──┬──┘ └───┬──┘ └─┬─┘ └┬┘
                      API    Type   UUID  Ext
                    prefix
```

**Types:** images, videos, documents  
**UUID:** Unique file identifier  
**Ext:** File extension (jpg, png, mp4, pdf, etc.)

---

## ✅ Prevention

### For Users:

1. **Always use the upload button** in templates
2. **Don't manually type URLs** unless you're sure
3. **Test preview** before saving template
4. **If preview doesn't work → re-upload**

### For Developers:

1. ✅ URLs automatically get `/api/` prefix (fixed in code)
2. ✅ Migration script available to fix old data
3. ✅ Both `/uploads/` and `/api/uploads/` paths work on backend
4. ✅ Frontend always generates URLs with `/api/` prefix

---

## 🎯 Quick Checklist

When uploading files:
- [ ] File uploads successfully
- [ ] Toast notification shows "uploaded"
- [ ] URL appears in field
- [ ] URL contains `/api/uploads/`
- [ ] Preview button works
- [ ] File opens in new tab
- [ ] Save template
- [ ] Load template → URL still works

---

**Status:** ✅ Migration completed  
**New uploads:** ✅ Automatically get correct URLs  
**Old templates:** ✅ Fixed by migration script  
**Last Updated:** December 2024
