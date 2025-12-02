# 🚀 CloudPanel VPS Deployment Guide

Complete guide to deploy the WhatsApp Bulk Messaging Application on CloudPanel VPS with subdomain from shared hosting.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [MongoDB Installation](#mongodb-installation)
4. [Application Deployment](#application-deployment)
5. [Subdomain Configuration](#subdomain-configuration)
6. [SSL/HTTPS Setup](#sslhttps-setup)
7. [Process Management with PM2](#process-management-with-pm2)
8. [Automated Backups](#automated-backups)
9. [Security Hardening](#security-hardening)
10. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

### What You'll Need:
- CloudPanel VPS (Ubuntu 20.04/22.04 recommended)
- Root or sudo access to the VPS
- Domain/Subdomain from shared hosting (e.g., `whatsapp.yourdomain.com`)
- Access to your domain's DNS settings
- Basic terminal/SSH knowledge

### Required Software Versions:
- Node.js: 18.x or higher
- Python: 3.9 or higher
- MongoDB: 5.0 or higher
- Nginx: (comes with CloudPanel)

---

## 🖥️ Server Setup

### Step 1: Initial Server Access

```bash
# SSH into your CloudPanel VPS
ssh root@your-vps-ip

# Update system packages
apt update && apt upgrade -y
```

### Step 2: Install Node.js 18.x

```bash
# Install Node.js 18.x LTS
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install -y nodejs

# Verify installation
node --version  # Should show v18.x.x
npm --version
```

### Step 3: Install Python 3.9+ and Dependencies

```bash
# Install Python (usually pre-installed on Ubuntu)
apt install -y python3 python3-pip python3-venv

# Verify installation
python3 --version  # Should show 3.9 or higher
pip3 --version
```

### Step 4: Install Build Tools

```bash
# Install essential build tools
apt install -y build-essential git curl wget unzip
```

---

## 🗄️ MongoDB Installation

### Step 1: Install MongoDB 5.0+

```bash
# Import MongoDB GPG key
curl -fsSL https://www.mongodb.org/static/pgp/server-5.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-5.0.gpg

# Add MongoDB repository
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-5.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/5.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-5.0.list

# Update package list
apt update

# Install MongoDB
apt install -y mongodb-org

# Start MongoDB service
systemctl start mongod
systemctl enable mongod

# Verify MongoDB is running
systemctl status mongod
```

### Step 2: Secure MongoDB

```bash
# Connect to MongoDB
mongosh

# Create admin user (run in mongosh)
use admin
db.createUser({
  user: "admin",
  pwd: "YOUR_STRONG_PASSWORD_HERE",
  roles: [ { role: "userAdminAnyDatabase", db: "admin" }, "readWriteAnyDatabase" ]
})

# Create database and user for the application
use whatsapp_db
db.createUser({
  user: "whatsapp_user",
  pwd: "YOUR_DB_PASSWORD_HERE",
  roles: [ { role: "readWrite", db: "whatsapp_db" } ]
})

# Exit mongosh
exit
```

### Step 3: Enable MongoDB Authentication

```bash
# Edit MongoDB config
nano /etc/mongod.conf

# Add/modify the security section:
# security:
#   authorization: enabled

# Restart MongoDB
systemctl restart mongod
```

### MongoDB Connection String Format:
```
mongodb://whatsapp_user:YOUR_DB_PASSWORD_HERE@localhost:27017/whatsapp_db
```

---

## 📦 Application Deployment

### Step 1: Create Application Directory

```bash
# Create app directory
mkdir -p /var/www/whatsapp-app
cd /var/www/whatsapp-app

# Clone or upload your application
# Option A: Using Git
git clone YOUR_REPOSITORY_URL .

# Option B: Upload via SFTP/SCP
# Use FileZilla or similar to upload files to /var/www/whatsapp-app
```

### Step 2: Backend Setup (FastAPI)

```bash
cd /var/www/whatsapp-app/backend

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
```

**Backend `.env` file content:**
```env
MONGO_URL=mongodb://whatsapp_user:YOUR_DB_PASSWORD_HERE@localhost:27017/whatsapp_db
DB_NAME=whatsapp_db
JWT_SECRET=your-super-secret-jwt-key-change-this-random-string
PORT=8001
```

**Generate a secure JWT secret:**
```bash
# Generate random JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy the output and use it as JWT_SECRET
```

### Step 3: Frontend Setup (React)

```bash
cd /var/www/whatsapp-app/frontend

# Install dependencies using yarn (recommended) or npm
npm install -g yarn
yarn install

# Create .env file
nano .env
```

**Frontend `.env` file content:**
```env
REACT_APP_BACKEND_URL=https://whatsapp.yourdomain.com
```

**Build the frontend:**
```bash
# Build for production
yarn build

# The build files will be in /var/www/whatsapp-app/frontend/build
```

### Step 4: Create Initial Admin User

```bash
# Activate backend virtual environment
cd /var/www/whatsapp-app/backend
source venv/bin/activate

# Create admin user script
cat > create_admin.py << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import uuid
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

async def create_admin():
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Check if admin exists
    existing_admin = await db.users.find_one({"email": "bizchatapi@gmail.com"})
    if existing_admin:
        print("Admin user already exists!")
        return
    
    # Create admin user
    hashed_password = bcrypt.hashpw("adminpassword".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": "bizchatapi@gmail.com",
        "password": hashed_password,
        "firstName": "Admin",
        "lastName": "User",
        "role": "admin",
        "isPaused": False,
        "dailyLimit": 100000,
        "dailyUsage": 0,
        "bizChatToken": None,
        "bizChatVendorUID": None,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(admin_user)
    print("Admin user created successfully!")
    print("Email: bizchatapi@gmail.com")
    print("Password: adminpassword")
    print("IMPORTANT: Change this password after first login!")

asyncio.run(create_admin())
EOF

# Run the script
python3 create_admin.py

# Remove the script for security
rm create_admin.py
```

---

## 🌐 Subdomain Configuration

### Step 1: Configure DNS (From Your Shared Hosting)

1. Log in to your **shared hosting control panel** (cPanel, Plesk, etc.)
2. Navigate to **DNS Zone Editor** or **DNS Management**
3. Add/Edit an **A Record**:
   - **Type:** A
   - **Name:** whatsapp (or your subdomain prefix)
   - **Value:** YOUR_VPS_IP_ADDRESS
   - **TTL:** 3600 (or default)

**Example:**
```
Type: A
Name: whatsapp
Points to: 123.45.67.89 (your VPS IP)
TTL: 3600
```

4. Save the record
5. **Wait 5-30 minutes** for DNS propagation

### Step 2: Verify DNS Propagation

```bash
# Check if subdomain points to your VPS
dig whatsapp.yourdomain.com
# OR
nslookup whatsapp.yourdomain.com

# Should return your VPS IP address
```

### Step 3: Create CloudPanel Site

1. Log in to **CloudPanel** (usually at `https://your-vps-ip:8443`)
2. Navigate to **Sites** → **Add Site**
3. Fill in the details:
   - **Domain Name:** whatsapp.yourdomain.com
   - **Site Type:** Static HTML (we'll configure manually)
   - **PHP Version:** Not needed (we use Python/Node.js)
4. Click **Create**

### Step 4: Configure Nginx for CloudPanel

```bash
# Find your site's Nginx config
cd /etc/nginx/sites-enabled/

# Edit the config for your subdomain
nano whatsapp.yourdomain.com.conf
```

**Replace the content with:**
```nginx
# Frontend (React build files)
server {
    listen 80;
    server_name whatsapp.yourdomain.com;
    
    root /var/www/whatsapp-app/frontend/build;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Test and reload Nginx:**
```bash
# Test configuration
nginx -t

# Reload Nginx
systemctl reload nginx
```

---

## 🔒 SSL/HTTPS Setup

### Step 1: Install Certbot

```bash
# Install Certbot for Nginx
apt install -y certbot python3-certbot-nginx
```

### Step 2: Obtain SSL Certificate

```bash
# Get SSL certificate from Let's Encrypt
certbot --nginx -d whatsapp.yourdomain.com

# Follow the prompts:
# - Enter your email address
# - Agree to terms
# - Choose whether to redirect HTTP to HTTPS (recommended: Yes)
```

### Step 3: Auto-Renewal Setup

```bash
# Test auto-renewal
certbot renew --dry-run

# Certbot automatically adds a cron job for renewal
# Verify it exists:
systemctl status certbot.timer
```

### Step 4: Update Frontend Environment

```bash
# Edit frontend .env to use HTTPS
nano /var/www/whatsapp-app/frontend/.env

# Change to:
REACT_APP_BACKEND_URL=https://whatsapp.yourdomain.com

# Rebuild frontend
cd /var/www/whatsapp-app/frontend
yarn build
```

---

## 🔄 Process Management with PM2

### Step 1: Install PM2 Globally

```bash
# Install PM2
npm install -g pm2

# Verify installation
pm2 --version
```

### Step 2: Create PM2 Ecosystem File

```bash
cd /var/www/whatsapp-app

# Create ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'whatsapp-backend',
      script: '/var/www/whatsapp-app/backend/venv/bin/uvicorn',
      args: 'server:app --host 0.0.0.0 --port 8001',
      cwd: '/var/www/whatsapp-app/backend',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        PYTHONPATH: '/var/www/whatsapp-app/backend'
      },
      error_file: '/var/log/pm2/whatsapp-backend-error.log',
      out_file: '/var/log/pm2/whatsapp-backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
EOF
```

### Step 3: Start Application with PM2

```bash
# Create log directory
mkdir -p /var/log/pm2

# Start the application
pm2 start ecosystem.config.js

# Save PM2 process list
pm2 save

# Setup PM2 to start on boot
pm2 startup systemd
# Run the command that PM2 outputs
```

### Step 4: PM2 Management Commands

```bash
# View running processes
pm2 list

# View logs
pm2 logs whatsapp-backend

# Restart application
pm2 restart whatsapp-backend

# Stop application
pm2 stop whatsapp-backend

# Monitor resources
pm2 monit

# View detailed info
pm2 info whatsapp-backend
```

---

## 💾 Automated Backups

### Step 1: Create Backup Script

```bash
# Create backup directory
mkdir -p /var/backups/whatsapp-app

# Create backup script
cat > /usr/local/bin/backup-whatsapp-db.sh << 'EOF'
#!/bin/bash

# Configuration
BACKUP_DIR="/var/backups/whatsapp-app"
MONGO_USER="whatsapp_user"
MONGO_PASS="YOUR_DB_PASSWORD_HERE"
MONGO_DB="whatsapp_db"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Create backup
mongodump --username="$MONGO_USER" --password="$MONGO_PASS" \
          --db="$MONGO_DB" --authenticationDatabase="$MONGO_DB" \
          --out="$BACKUP_DIR/backup_$DATE"

# Compress backup
cd "$BACKUP_DIR"
tar -czf "backup_$DATE.tar.gz" "backup_$DATE"
rm -rf "backup_$DATE"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: backup_$DATE.tar.gz"
EOF

# Make script executable
chmod +x /usr/local/bin/backup-whatsapp-db.sh

# Test the script
/usr/local/bin/backup-whatsapp-db.sh
```

### Step 2: Schedule Daily Backups

```bash
# Edit crontab
crontab -e

# Add this line (backup every day at 2 AM)
0 2 * * * /usr/local/bin/backup-whatsapp-db.sh >> /var/log/whatsapp-backup.log 2>&1
```

### Step 3: Restore from Backup

```bash
# List backups
ls -lh /var/backups/whatsapp-app/

# Extract backup
cd /var/backups/whatsapp-app
tar -xzf backup_20250101_020000.tar.gz

# Restore database
mongorestore --username="whatsapp_user" --password="YOUR_DB_PASSWORD_HERE" \
             --db="whatsapp_db" --authenticationDatabase="whatsapp_db" \
             --drop backup_20250101_020000/whatsapp_db/
```

---

## 🔐 Security Hardening

### Step 1: Configure Firewall (UFW)

```bash
# Install UFW (if not installed)
apt install -y ufw

# Allow SSH (IMPORTANT: Do this first!)
ufw allow 22/tcp

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow CloudPanel port (if using)
ufw allow 8443/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

### Step 2: Secure MongoDB

```bash
# MongoDB should only listen on localhost
nano /etc/mongod.conf

# Ensure these settings:
# net:
#   port: 27017
#   bindIp: 127.0.0.1

# Restart MongoDB
systemctl restart mongod
```

### Step 3: Set File Permissions

```bash
# Set proper ownership
chown -R www-data:www-data /var/www/whatsapp-app

# Secure environment files
chmod 600 /var/www/whatsapp-app/backend/.env
chmod 600 /var/www/whatsapp-app/frontend/.env

# Make sure backend code is readable
chmod -R 755 /var/www/whatsapp-app
```

### Step 4: Rate Limiting (Nginx)

```bash
# Edit your site's Nginx config
nano /etc/nginx/sites-enabled/whatsapp.yourdomain.com.conf

# Add rate limiting at the http level
# Add this BEFORE the server block:
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Inside the location /api block, add:
# limit_req zone=api_limit burst=20 nodelay;

# Reload Nginx
nginx -t && systemctl reload nginx
```

### Step 5: Fail2Ban Setup

```bash
# Install Fail2Ban
apt install -y fail2ban

# Create custom config
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
EOF

# Start Fail2Ban
systemctl start fail2ban
systemctl enable fail2ban

# Check status
fail2ban-client status
```

---

## 🔍 Troubleshooting

### Common Issues and Solutions

#### 1. Backend Not Starting

```bash
# Check PM2 logs
pm2 logs whatsapp-backend --lines 50

# Check if port 8001 is in use
netstat -tlnp | grep 8001

# Test backend directly
cd /var/www/whatsapp-app/backend
source venv/bin/activate
python3 -m uvicorn server:app --host 0.0.0.0 --port 8001
```

#### 2. MongoDB Connection Issues

```bash
# Test MongoDB connection
mongosh "mongodb://whatsapp_user:YOUR_DB_PASSWORD@localhost:27017/whatsapp_db"

# Check MongoDB logs
tail -f /var/log/mongodb/mongod.log

# Verify MongoDB is running
systemctl status mongod
```

#### 3. Frontend Not Loading

```bash
# Check if build exists
ls -la /var/www/whatsapp-app/frontend/build

# Rebuild frontend
cd /var/www/whatsapp-app/frontend
yarn build

# Check Nginx logs
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log
```

#### 4. SSL Certificate Issues

```bash
# Renew certificate manually
certbot renew --force-renewal -d whatsapp.yourdomain.com

# Check certificate expiry
certbot certificates

# Test SSL configuration
nginx -t
```

#### 5. DNS Not Resolving

```bash
# Check DNS propagation
dig whatsapp.yourdomain.com +short
nslookup whatsapp.yourdomain.com

# Flush DNS cache (on your local machine)
# Windows: ipconfig /flushdns
# Mac: sudo dscacheutil -flushcache
# Linux: sudo systemd-resolve --flush-caches
```

#### 6. High Memory Usage

```bash
# Check memory usage
free -h
pm2 monit

# Restart application
pm2 restart whatsapp-backend

# Consider increasing VPS resources if consistently high
```

### Logs Locations

```bash
# Backend logs (PM2)
/var/log/pm2/whatsapp-backend-error.log
/var/log/pm2/whatsapp-backend-out.log

# Nginx logs
/var/log/nginx/access.log
/var/log/nginx/error.log

# MongoDB logs
/var/log/mongodb/mongod.log

# System logs
journalctl -u mongod -f
```

### Health Check Commands

```bash
# Check all services
systemctl status mongod
systemctl status nginx
pm2 status

# Test backend API
curl http://localhost:8001/api/health
curl https://whatsapp.yourdomain.com/api/health

# Test frontend
curl -I https://whatsapp.yourdomain.com/

# Monitor system resources
htop
df -h
```

---

## 📊 Performance Optimization

### 1. Nginx Optimization

```bash
# Edit Nginx main config
nano /etc/nginx/nginx.conf

# Add/modify in http block:
# gzip on;
# gzip_vary on;
# gzip_proxied any;
# gzip_comp_level 6;
# gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

# Reload Nginx
nginx -t && systemctl reload nginx
```

### 2. PM2 Cluster Mode (Optional)

```bash
# For high-traffic scenarios, modify ecosystem.config.js
# Change instances: 1 to instances: 2 (or more)

pm2 reload ecosystem.config.js
```

### 3. MongoDB Optimization

```bash
# Create indexes for frequently queried fields
mongosh "mongodb://whatsapp_user:YOUR_DB_PASSWORD@localhost:27017/whatsapp_db"

# Run in mongosh:
db.users.createIndex({ email: 1 })
db.campaigns.createIndex({ created_by: 1, createdAt: -1 })
db.templates.createIndex({ created_by: 1 })
```

---

## ✅ Post-Deployment Checklist

- [ ] MongoDB installed and secured
- [ ] Backend running via PM2
- [ ] Frontend built and served by Nginx
- [ ] DNS A record pointing to VPS IP
- [ ] SSL certificate installed and auto-renewal working
- [ ] Firewall configured (UFW)
- [ ] Daily backups scheduled
- [ ] Admin user created
- [ ] Application accessible via HTTPS
- [ ] Logs are being written and rotated
- [ ] PM2 configured to start on boot
- [ ] Test login with admin credentials
- [ ] Change default admin password

---

## 🎯 Quick Reference

### Application URLs
- **Frontend:** https://whatsapp.yourdomain.com
- **Backend API:** https://whatsapp.yourdomain.com/api

### Default Admin Credentials
- **Email:** bizchatapi@gmail.com
- **Password:** adminpassword
- **⚠️ CHANGE THIS IMMEDIATELY AFTER FIRST LOGIN!**

### Important Commands
```bash
# Restart backend
pm2 restart whatsapp-backend

# View logs
pm2 logs whatsapp-backend

# Backup database
/usr/local/bin/backup-whatsapp-db.sh

# Reload Nginx
nginx -t && systemctl reload nginx

# Check all services
systemctl status mongod nginx
pm2 status
```

---

## 📞 Support

If you encounter issues:
1. Check the **Troubleshooting** section above
2. Review logs in `/var/log/` directories
3. Verify all environment variables are set correctly
4. Ensure DNS has fully propagated (can take up to 24 hours)

---

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Pull latest code (if using Git)
cd /var/www/whatsapp-app
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Update frontend
cd frontend
yarn install
yarn build
cd ..

# Restart backend
pm2 restart whatsapp-backend

# No need to restart Nginx (static files updated)
```

### System Updates

```bash
# Regular system updates (monthly recommended)
apt update && apt upgrade -y

# Restart services if needed
systemctl restart mongod
pm2 restart all
systemctl restart nginx
```

---

## 📝 Notes

- **Subdomain Setup:** The subdomain DNS record must be created in your shared hosting control panel, not CloudPanel
- **CloudPanel:** While CloudPanel is installed, we use it primarily for SSL management and basic site config
- **PM2 vs Systemd:** PM2 is preferred for Node.js/Python apps due to better logging and process management
- **Database Security:** MongoDB is configured to only accept local connections for security
- **Backups:** Store backups off-site (cloud storage) for disaster recovery
- **Monitoring:** Consider adding Uptime monitoring (UptimeRobot, etc.) for production

---

**Deployment Guide Version:** 1.0  
**Last Updated:** December 2024  
**Application:** WhatsApp Bulk Messaging System
