# Tria AIBPO - Ubuntu Quick Reference

Quick reference for common operations on Ubuntu server deployment.

## 🚀 Quick Start

```bash
# One-command deployment (development)
sudo ./scripts/deploy_ubuntu.sh --dev

# Production deployment with SSL
sudo ./scripts/deploy_ubuntu.sh --production --domain=yourdomain.com --email=you@example.com
```

## 📦 Service Management

```bash
# systemd service
sudo systemctl start tria-aibpo        # Start
sudo systemctl stop tria-aibpo         # Stop
sudo systemctl restart tria-aibpo      # Restart
sudo systemctl status tria-aibpo       # Status
sudo systemctl enable tria-aibpo       # Enable auto-start
sudo systemctl disable tria-aibpo      # Disable auto-start

# Docker Compose
cd /opt/tria-aibpo
sudo docker compose up -d              # Start all services
sudo docker compose down               # Stop all services
sudo docker compose restart            # Restart all services
sudo docker compose ps                 # List containers
sudo docker compose logs -f            # View logs (follow)
```

## 🔍 Monitoring

```bash
# Health check
curl http://localhost/health | jq .

# Container status
sudo docker compose ps

# Resource usage
sudo docker stats

# View logs
sudo journalctl -u tria-aibpo -f                    # systemd logs
sudo docker compose logs -f                         # All containers
sudo docker compose logs -f backend                 # Specific service
sudo docker compose exec nginx tail -f /var/log/nginx/access.log  # Nginx access
sudo docker compose exec nginx tail -f /var/log/nginx/error.log   # Nginx errors

# System resources
htop                                    # Interactive process viewer
df -h                                   # Disk usage
free -m                                 # Memory usage
sudo netstat -tlnp                      # Network connections
```

## 🗃️ Database Operations

```bash
# Connect to PostgreSQL
sudo docker compose exec postgres psql -U tria_admin -d tria_aibpo

# Database backup
sudo docker compose exec -T postgres pg_dump -U tria_admin tria_aibpo | gzip > backup.sql.gz

# Database restore
gunzip -c backup.sql.gz | sudo docker compose exec -T postgres psql -U tria_admin -d tria_aibpo

# Database size
sudo docker compose exec postgres psql -U tria_admin -d tria_aibpo -c "SELECT pg_size_pretty(pg_database_size('tria_aibpo'));"

# Redis CLI
sudo docker compose exec redis redis-cli -a "$REDIS_PASSWORD"

# Redis info
sudo docker compose exec redis redis-cli -a "$REDIS_PASSWORD" info
```

## 💾 Backup & Restore

```bash
# Manual backup
sudo systemctl start tria-aibpo-backup.service

# View backups
ls -lh /opt/tria-aibpo/backups/

# Backup status
sudo systemctl status tria-aibpo-backup.timer

# Backup logs
sudo journalctl -u tria-aibpo-backup -n 50

# Restore database
cd /opt/tria-aibpo
gunzip -c backups/postgres_YYYYMMDD_HHMMSS.sql.gz | \
  sudo docker compose exec -T postgres psql -U tria_admin -d tria_aibpo

# Restore application data
sudo tar -xzf backups/data_YYYYMMDD_HHMMSS.tar.gz -C /opt/tria-aibpo/
```

## 🔐 SSL Certificates

```bash
# List certificates
sudo certbot certificates

# Renew certificates (manual)
sudo certbot renew

# Renewal timer status
sudo systemctl status certbot.timer

# Test renewal (dry run)
sudo certbot renew --dry-run

# View certificate info
sudo openssl x509 -in /opt/tria-aibpo/nginx/ssl/tria.crt -text -noout

# Check certificate expiry
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

## 🔧 Configuration

```bash
# Edit environment variables
sudo nano /opt/tria-aibpo/.env

# Apply changes
cd /opt/tria-aibpo
sudo docker compose --env-file .env up -d --force-recreate

# Edit Nginx configuration
sudo nano /opt/tria-aibpo/nginx/conf.d/tria-aibpo.conf
sudo docker compose restart nginx

# Reload Nginx (without restart)
sudo docker compose exec nginx nginx -s reload
```

## 🔄 Updates & Maintenance

```bash
# Update application code
cd /opt/tria-aibpo
sudo git pull

# Rebuild and restart
sudo docker compose --env-file .env build
sudo docker compose --env-file .env up -d --force-recreate

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean Docker resources
sudo docker system prune -a              # Remove unused images/containers
sudo docker volume prune                 # Remove unused volumes
sudo docker image prune -a               # Remove unused images
```

## 🛡️ Firewall

```bash
# UFW status
sudo ufw status

# Allow port
sudo ufw allow 80/tcp

# Deny port
sudo ufw deny 8080/tcp

# Delete rule
sudo ufw delete allow 80/tcp

# Enable/disable firewall
sudo ufw enable
sudo ufw disable

# Reload firewall
sudo ufw reload
```

## 🐛 Troubleshooting

```bash
# Check service status
sudo systemctl status tria-aibpo
sudo systemctl status docker

# View error logs
sudo journalctl -u tria-aibpo -p err -n 50
sudo docker compose logs --tail=100

# Restart specific container
sudo docker compose restart backend
sudo docker compose restart nginx

# Remove and recreate containers
sudo docker compose down
sudo docker compose up -d

# Check port conflicts
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
sudo netstat -tlnp | grep :8003

# Test health endpoint
curl -v http://localhost/health
curl -v https://localhost/health -k

# Check DNS resolution
nslookup yourdomain.com
dig yourdomain.com

# Test database connection
sudo docker compose exec postgres pg_isready -U tria_admin

# Container resource usage
sudo docker stats --no-stream

# View container details
sudo docker compose inspect backend
```

## 📊 Performance Testing

```bash
# Test API response time
curl -w "@-" -o /dev/null -s http://localhost/health <<'EOF'
    time_namelookup:  %{time_namelookup}\n
       time_connect:  %{time_connect}\n
    time_appconnect:  %{time_appconnect}\n
      time_redirect:  %{time_redirect}\n
 time_starttransfer:  %{time_starttransfer}\n
                    ----------\n
         time_total:  %{time_total}\n
EOF

# Load testing (requires apache2-utils)
sudo apt install -y apache2-utils
ab -n 1000 -c 10 http://localhost/health

# Monitor during load test
watch -n 1 'sudo docker stats --no-stream'
```

## 🔑 Common File Locations

```bash
# Application
/opt/tria-aibpo/                        # Application root
/opt/tria-aibpo/.env                    # Environment variables
/opt/tria-aibpo/docker-compose.yml      # Docker Compose config

# Configuration
/opt/tria-aibpo/nginx/                  # Nginx configs
/opt/tria-aibpo/systemd/                # systemd service files

# Data
/opt/tria-aibpo/data/                   # Application data
/opt/tria-aibpo/logs/                   # Application logs
/opt/tria-aibpo/backups/                # Database backups

# SSL
/opt/tria-aibpo/nginx/ssl/              # SSL certificates
/etc/letsencrypt/                       # Let's Encrypt certificates

# systemd
/etc/systemd/system/tria-aibpo.service              # Main service
/etc/systemd/system/tria-aibpo-backup.service       # Backup service
/etc/systemd/system/tria-aibpo-backup.timer         # Backup timer
```

## 🆘 Emergency Procedures

### Complete Restart
```bash
cd /opt/tria-aibpo
sudo docker compose down
sudo docker compose up -d
```

### Emergency Stop
```bash
sudo systemctl stop tria-aibpo
# or
cd /opt/tria-aibpo && sudo docker compose down
```

### Rollback Update
```bash
cd /opt/tria-aibpo
sudo git log --oneline -n 10           # Find previous commit
sudo git checkout <commit-hash>        # Rollback to commit
sudo docker compose build
sudo docker compose up -d --force-recreate
```

### Clean Slate Restart
```bash
cd /opt/tria-aibpo
sudo docker compose down -v            # Remove volumes
sudo docker system prune -af           # Clean all Docker resources
sudo docker compose up -d              # Fresh start
```

## 📞 Getting Help

```bash
# View full documentation
cat /opt/tria-aibpo/docs/UBUNTU_DEPLOYMENT_GUIDE.md

# systemd service help
cat /opt/tria-aibpo/systemd/README.md

# Check application version
cd /opt/tria-aibpo && git log -1 --oneline

# Generate diagnostic report
cd /opt/tria-aibpo
echo "=== System Info ===" > diagnostic.txt
uname -a >> diagnostic.txt
echo "=== Docker Version ===" >> diagnostic.txt
docker --version >> diagnostic.txt
echo "=== Container Status ===" >> diagnostic.txt
docker compose ps >> diagnostic.txt
echo "=== Recent Logs ===" >> diagnostic.txt
docker compose logs --tail=50 >> diagnostic.txt
echo "=== Disk Usage ===" >> diagnostic.txt
df -h >> diagnostic.txt
echo "=== Memory Usage ===" >> diagnostic.txt
free -m >> diagnostic.txt
cat diagnostic.txt
```

---

**Pro Tips:**
- Use `sudo docker compose` (not `docker-compose`) on Ubuntu 22.04+
- Always check logs first: `sudo journalctl -u tria-aibpo -f`
- Test in development before production: `--dev` flag
- Backups run daily at 2 AM automatically
- SSL certificates renew automatically via certbot.timer
