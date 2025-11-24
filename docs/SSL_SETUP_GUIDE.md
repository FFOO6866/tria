# SSL/HTTPS Setup Guide for Tria AIBPO

**Current Status:** HTTP only (13.214.14.130:8003)
**Target:** HTTPS with valid SSL certificate
**Estimated Time:** 15-30 minutes

---

## 🎯 **Choose Your SSL Setup Method**

### **Option A: With Domain Name** ✅ **RECOMMENDED**

**Requirements:**
- Domain name (e.g., aibpo.com, tria.yourdomain.com)
- Domain A record pointing to 13.214.14.130

**Advantages:**
- ✅ Professional URL (https://aibpo.com)
- ✅ FREE SSL from Let's Encrypt
- ✅ Automatic renewal
- ✅ No browser warnings
- ✅ Full production-ready

**Time:** 15 minutes

**→ Go to: [Option A Instructions](#option-a-with-domain-name)**

---

### **Option B: Without Domain (IP Only)** ⚠️

**Requirements:**
- Just your server IP (13.214.14.130)

**Advantages:**
- ✅ No domain purchase needed
- ✅ Works immediately

**Disadvantages:**
- ⚠️ Self-signed certificate (browser warnings)
- ⚠️ Users must click "Proceed anyway"
- ⚠️ Not recommended for production

**Time:** 10 minutes

**→ Go to: [Option B Instructions](#option-b-without-domain-ip-only)**

---

### **Option C: Cloudflare Tunnel** 🆓 **NO DOMAIN NEEDED**

**Requirements:**
- Nothing! Just run a script

**Advantages:**
- ✅ FREE HTTPS
- ✅ No domain required
- ✅ Cloudflare provides: https://random-words-123.trycloudflare.com
- ✅ No DNS configuration

**Disadvantages:**
- ⚠️ Random URL (changes on restart)
- ⚠️ Not professional for production

**Time:** 5 minutes

**→ Go to: [Option C Instructions](#option-c-cloudflare-tunnel)**

---

## 📋 **Quick Recommendation**

| Use Case | Recommendation |
|----------|----------------|
| **Production deployment** | Option A (with domain) |
| **Demo/testing only** | Option C (Cloudflare Tunnel) |
| **Internal use only** | Option B (self-signed) |

---

# Option A: With Domain Name

## Prerequisites

### 1. Get a Domain Name

**Where to buy:**
- [Namecheap](https://www.namecheap.com) - $8-12/year
- [GoDaddy](https://www.godaddy.com) - $10-15/year
- [Cloudflare Registrar](https://www.cloudflare.com/products/registrar/) - At-cost pricing

**Options:**
```
aibpo.com          # Short and professional
tria-demo.com      # For demo purposes
your-company.com   # Use your company domain
```

### 2. Point Domain to Server

In your domain registrar's DNS settings, add an **A record**:

```
Type: A
Name: @ (or your subdomain)
Value: 13.214.14.130
TTL: Auto or 300 seconds
```

**Examples:**

**For root domain (aibpo.com):**
```
A    @         13.214.14.130
```

**For subdomain (tria.aibpo.com):**
```
A    tria      13.214.14.130
```

**Wait for DNS propagation:**
```bash
# Test from your local machine:
nslookup aibpo.com
# Should return: 13.214.14.130
```

---

## Setup Steps

### Step 1: Upload SSL Setup Script

From your **local machine**:

```bash
# Navigate to project
cd C:\Users\fujif\OneDrive\Documents\GitHub\tria

# Copy script to server
scp -i "C:\Users\fujif\Downloads\Tria (1).pem" scripts/setup_ssl.sh ubuntu@13.214.14.130:/home/ubuntu/
```

### Step 2: SSH into Server

```bash
ssh -i "C:\Users\fujif\Downloads\Tria (1).pem" ubuntu@13.214.14.130
```

### Step 3: Run SSL Setup Script

```bash
# Make script executable
chmod +x setup_ssl.sh

# Run with your domain and email
sudo ./setup_ssl.sh aibpo.com your-email@example.com

# Example:
sudo ./setup_ssl.sh aibpo.com admin@aibpo.com
```

**The script will:**
1. ✅ Verify DNS points to server
2. ✅ Install nginx + certbot
3. ✅ Configure firewall (ports 80, 443)
4. ✅ Create nginx reverse proxy config
5. ✅ Obtain SSL certificate from Let's Encrypt
6. ✅ Set up auto-renewal
7. ✅ Update .env with HTTPS redirect URI

### Step 4: Update Xero App Settings

1. Go to: https://developer.xero.com/app/manage
2. Click on your "aibpo" app
3. Update **Redirect URI** to:
   ```
   https://aibpo.com/api/xero/callback
   ```
   (Replace `aibpo.com` with your domain)

### Step 5: Restart Services

```bash
# Restart Docker services
cd /path/to/tria
docker-compose restart

# Or restart backend manually
systemctl restart tria-backend  # If using systemd
```

### Step 6: Test HTTPS

```bash
# Test from server
curl https://aibpo.com/health

# Test from your browser
# Open: https://aibpo.com
# Should show lock icon 🔒
```

### Step 7: Get New Xero Tokens

```bash
# Get tokens with HTTPS redirect
python scripts/get_xero_tokens.py

# Follow prompts, authorize in browser
# Copy refresh token and tenant ID to .env
```

---

## Verification Checklist

After setup, verify:

- [ ] `https://your-domain.com` loads without warnings
- [ ] Lock icon 🔒 appears in browser
- [ ] Certificate is valid (click lock icon → view certificate)
- [ ] API responds: `curl https://your-domain.com/health`
- [ ] Xero redirect URI updated in Xero dashboard
- [ ] New refresh token obtained with HTTPS redirect
- [ ] Auto-renewal configured: `sudo certbot renew --dry-run`

---

## Troubleshooting

### ❌ "Domain doesn't resolve"

**Problem:** DNS not pointing to server

**Solution:**
```bash
# Check DNS
nslookup your-domain.com

# If it doesn't return 13.214.14.130:
# 1. Verify A record in domain registrar
# 2. Wait 5-30 minutes for propagation
# 3. Try again
```

---

### ❌ "Certificate request failed"

**Problem:** Port 80 not accessible

**Solution:**
```bash
# Check if port 80 is open
sudo ufw status

# Open port 80
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Check AWS/cloud firewall (Security Group)
# Ensure ports 80 and 443 are open
```

---

### ❌ "nginx: [emerg] bind() to 0.0.0.0:80 failed"

**Problem:** Another service using port 80

**Solution:**
```bash
# Find what's using port 80
sudo lsof -i :80

# Stop conflicting service
sudo systemctl stop apache2  # If Apache
# Or kill the process

# Restart nginx
sudo systemctl restart nginx
```

---

# Option B: Without Domain (IP Only)

## Self-Signed Certificate Setup

### Step 1: Generate Self-Signed Certificate

SSH into server:
```bash
ssh -i "C:\Users\fujif\Downloads\Tria (1).pem" ubuntu@13.214.14.130

# Create SSL directory
sudo mkdir -p /etc/ssl/tria

# Generate certificate (valid for 365 days)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/tria/selfsigned.key \
  -out /etc/ssl/tria/selfsigned.crt \
  -subj "/C=SG/ST=Singapore/L=Singapore/O=Tria/CN=13.214.14.130"
```

### Step 2: Configure Nginx

```bash
# Install nginx if not installed
sudo apt-get update
sudo apt-get install -y nginx

# Create nginx config
sudo tee /etc/nginx/sites-available/tria-ssl <<'EOF'
upstream backend {
    server 127.0.0.1:8003;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name 13.214.14.130;

    ssl_certificate /etc/ssl/tria/selfsigned.crt;
    ssl_certificate_key /etc/ssl/tria/selfsigned.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://backend;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name 13.214.14.130;
    return 301 https://$server_name$request_uri;
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/tria-ssl /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: Update .env

```bash
# Update redirect URI to HTTPS
nano .env

# Change:
XERO_REDIRECT_URI=https://13.214.14.130/api/xero/callback
```

### Step 4: Update Xero App

In Xero Developer Portal:
```
Redirect URI: https://13.214.14.130/api/xero/callback
```

### ⚠️ Browser Warning

Users will see:
```
⚠️ Your connection is not private
NET::ERR_CERT_AUTHORITY_INVALID
```

**They must click:** "Advanced" → "Proceed to 13.214.14.130 (unsafe)"

**This is expected with self-signed certificates.**

---

# Option C: Cloudflare Tunnel

## FREE HTTPS Without Domain

### Step 1: Upload Script

```bash
# From local machine
scp -i "C:\Users\fujif\Downloads\Tria (1).pem" \
  scripts/setup_ssl_cloudflare.sh \
  ubuntu@13.214.14.130:/home/ubuntu/
```

### Step 2: Run Script

```bash
# SSH into server
ssh -i "C:\Users\fujif\Downloads\Tria (1).pem" ubuntu@13.214.14.130

# Make executable
chmod +x setup_ssl_cloudflare.sh

# Run (as normal user, not root)
./setup_ssl_cloudflare.sh
```

### Step 3: Get Your HTTPS URL

Script output will show:
```
Your tunnel is now available at:
https://fancy-words-123.trycloudflare.com

⚠️ This URL will change if you restart the tunnel
```

### Step 4: Update Xero Redirect

In Xero Developer Portal:
```
Redirect URI: https://fancy-words-123.trycloudflare.com/api/xero/callback
```

### Step 5: Update .env

```bash
XERO_REDIRECT_URI=https://fancy-words-123.trycloudflare.com/api/xero/callback
```

### ⚠️ Limitations

- URL changes on restart (unless you create Cloudflare account)
- Not suitable for long-term production
- Good for demos and testing

---

## Certificate Renewal (Option A Only)

Let's Encrypt certificates expire after **90 days**.

### Auto-Renewal (Automatic)

Certbot automatically renews certificates via systemd timer:

```bash
# Check renewal timer status
sudo systemctl status certbot.timer

# Test renewal (dry-run)
sudo certbot renew --dry-run
```

### Manual Renewal (If needed)

```bash
# Renew all certificates
sudo certbot renew

# Renew specific domain
sudo certbot renew --cert-name your-domain.com

# Force renewal
sudo certbot renew --force-renewal
```

---

## SSL Verification Commands

```bash
# Test SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check certificate expiry
echo | openssl s_client -connect your-domain.com:443 2>/dev/null | openssl x509 -noout -dates

# Test HTTPS endpoint
curl -v https://your-domain.com/health

# Check SSL rating
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com
```

---

## Next Steps After SSL Setup

1. ✅ Test HTTPS works
2. ✅ Update Xero redirect URI
3. ✅ Get new Xero tokens with HTTPS redirect
4. ✅ Test end-to-end order flow
5. ✅ Update frontend API URL to HTTPS
6. ✅ Test on multiple browsers
7. ✅ Document SSL certificate expiry date

---

## Support

**Issues?** Check troubleshooting sections above or contact support.

**SSL Rating:** Test your SSL setup at https://www.ssllabs.com/ssltest/
