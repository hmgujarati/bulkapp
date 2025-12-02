# 📊 Database Storage Information

## 🗄️ Where is the Database Stored?

### Primary Location:
```
📂 /var/lib/mongodb
```

This is the default MongoDB data directory where all your database files are physically stored on the server's disk.

---

## 📁 What's Inside?

### Database Name:
**whatsapp_bulk_messenger**

### Collections (Tables):
- **users** - User accounts (admin and regular users)
- **campaigns** - Message campaigns and their status
- **saved_templates** - User-saved message templates

### Current Data (as of now):
- Users: 2
- Campaigns: 0
- Templates: 0
- Total Database Size: ~0.2 MB

---

## 🔗 Connection Information

### Connection String:
```
mongodb://localhost:27017/whatsapp_bulk_messenger
```

### Configuration Files:
- **Backend Config:** `/app/backend/.env`
  ```
  MONGO_URL="mongodb://localhost:27017"
  DB_NAME="whatsapp_bulk_messenger"
  ```

- **MongoDB Config:** `/etc/mongod.conf`
  ```yaml
  storage:
    dbPath: /var/lib/mongodb
  ```

---

## 💾 Backup Information

### Recommended Backup Location:
```
📂 /var/backups/whatsapp-app/
```

### Backup File Format:
```
backup_YYYYMMDD_HHMMSS.tar.gz
```
Example: `backup_20240101_020000.tar.gz`

### How to Backup Manually:

```bash
# Create backup directory
mkdir -p /var/backups/whatsapp-app

# Backup database
mongodump --db=whatsapp_bulk_messenger --out=/var/backups/whatsapp-app/backup_$(date +%Y%m%d_%H%M%S)

# Compress backup
cd /var/backups/whatsapp-app
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz backup_$(date +%Y%m%d_%H%M%S)
```

### Automated Backups:
If you followed the deployment guide (`DEPLOYMENT.md`), automated daily backups are configured to run at 2 AM via cron job.

---

## 🛠️ Useful Commands

### View Database Size:
```bash
du -sh /var/lib/mongodb
```

### Connect to Database Shell:
```bash
mongosh "mongodb://localhost:27017/whatsapp_bulk_messenger"
```

### View All Collections:
```bash
mongosh "mongodb://localhost:27017/whatsapp_bulk_messenger" --eval "db.getCollectionNames()"
```

### Count Documents:
```bash
mongosh "mongodb://localhost:27017/whatsapp_bulk_messenger" --eval "
  print('Users: ' + db.users.countDocuments());
  print('Campaigns: ' + db.campaigns.countDocuments());
  print('Templates: ' + db.templates.countDocuments());
"
```

### Export Entire Database:
```bash
mongodump --db=whatsapp_bulk_messenger --out=/tmp/database_backup
```

### Restore Database:
```bash
mongorestore --db=whatsapp_bulk_messenger --drop /tmp/database_backup/whatsapp_bulk_messenger/
```

---

## 🔐 Security Notes

1. ✅ **Local Only**: MongoDB is configured to only accept connections from localhost (127.0.0.1)
2. ✅ **Not Exposed**: Database is not accessible from the internet
3. ✅ **Firewall**: Port 27017 should not be open to external traffic
4. ⚠️ **Backups**: Always keep regular backups in case of data loss
5. ⚠️ **Permissions**: Only root and MongoDB user have access to `/var/lib/mongodb`

---

## 📈 Database Growth Estimates

Based on typical usage:

| Data Type | Size per Record | 10,000 Records | 100,000 Records |
|-----------|----------------|----------------|-----------------|
| Users | ~1 KB | ~10 MB | ~100 MB |
| Campaigns | ~2 KB | ~20 MB | ~200 MB |
| Templates | ~500 B | ~5 MB | ~50 MB |

**Note:** Actual sizes may vary based on content and campaign details.

---

## 🚨 Important Warnings

### DO NOT:
- ❌ Delete files in `/var/lib/mongodb` manually
- ❌ Stop MongoDB while application is running
- ❌ Expose MongoDB port (27017) to the internet
- ❌ Modify database files directly

### DO:
- ✅ Use `mongodump` and `mongorestore` for backups
- ✅ Keep regular backups (daily recommended)
- ✅ Monitor disk space (ensure 20%+ free space)
- ✅ Use the application's API to modify data

---

## 🌐 Production Deployment

When you deploy to CloudPanel VPS (following `DEPLOYMENT.md`):

1. **Database Location**: Same (`/var/lib/mongodb`)
2. **Connection**: Remains localhost-only for security
3. **Backups**: Automated via cron job
4. **Monitoring**: Check disk space regularly

### Check Disk Space:
```bash
df -h /var/lib/mongodb
```

### MongoDB Service Status:
```bash
systemctl status mongod
```

---

## 📞 Need Help?

- Backup/Restore: See `DEPLOYMENT.md` - Section "Automated Backups"
- Connection Issues: Check that MongoDB is running with `systemctl status mongod`
- Performance: Consider adding indexes for large datasets

---

**Last Updated:** December 2024
