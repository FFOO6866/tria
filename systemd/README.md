# Tria AIBPO systemd Services

systemd service files for Ubuntu server deployment with automatic startup, restart, and backup functionality.

## Services Overview

### 1. tria-aibpo.service
Main application service that manages Docker Compose containers.

**Features:**
- Automatic startup on boot
- Restart on failure
- Graceful shutdown with 30s timeout
- Health check after startup
- Dependency management (requires Docker)

### 2. tria-aibpo-backup.service + tria-aibpo-backup.timer
Automated backup service for PostgreSQL database and application data.

**Features:**
- Daily backups at 2 AM
- Automatic cleanup (keeps last 7 days)
- Backs up PostgreSQL database (compressed SQL dump)
- Backs up application data (logs, ChromaDB, .env)
- Persistent timer (runs missed backups on boot)

## Installation

### Quick Install (Automated)

The deployment script automatically installs systemd services:

```bash
sudo ./scripts/deploy_ubuntu.sh
```

### Manual Installation

#### 1. Install Main Service

```bash
# Copy service file
sudo cp systemd/tria-aibpo.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable tria-aibpo

# Start service
sudo systemctl start tria-aibpo

# Check status
sudo systemctl status tria-aibpo
```

#### 2. Install Backup Service (Optional but Recommended)

```bash
# Copy service and timer files
sudo cp systemd/tria-aibpo-backup.service /etc/systemd/system/
sudo cp systemd/tria-aibpo-backup.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable timer (start on boot)
sudo systemctl enable tria-aibpo-backup.timer

# Start timer
sudo systemctl start tria-aibpo-backup.timer

# Check timer status
sudo systemctl status tria-aibpo-backup.timer

# List all timers
sudo systemctl list-timers tria-aibpo-backup.timer
```

## Management Commands

### Main Application Service

```bash
# Start application
sudo systemctl start tria-aibpo

# Stop application
sudo systemctl stop tria-aibpo

# Restart application
sudo systemctl restart tria-aibpo

# Reload application (recreate containers)
sudo systemctl reload tria-aibpo

# Check status
sudo systemctl status tria-aibpo

# View logs
sudo journalctl -u tria-aibpo -f

# View recent logs (last 100 lines)
sudo journalctl -u tria-aibpo -n 100

# Enable auto-start on boot
sudo systemctl enable tria-aibpo

# Disable auto-start on boot
sudo systemctl disable tria-aibpo
```

### Backup Service

```bash
# Check timer status
sudo systemctl status tria-aibpo-backup.timer

# Run backup manually (immediate)
sudo systemctl start tria-aibpo-backup.service

# View backup logs
sudo journalctl -u tria-aibpo-backup -f

# List scheduled timers
sudo systemctl list-timers

# Enable timer
sudo systemctl enable tria-aibpo-backup.timer

# Disable timer
sudo systemctl disable tria-aibpo-backup.timer
```

## Configuration

### Change Working Directory

If you deploy Tria AIBPO to a different location (not `/opt/tria-aibpo`), update the service file:

```bash
sudo nano /etc/systemd/system/tria-aibpo.service
```

Change:
```ini
WorkingDirectory=/opt/tria-aibpo
EnvironmentFile=/opt/tria-aibpo/.env
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart tria-aibpo
```

### Change Backup Schedule

To change backup schedule (default: daily at 2 AM):

```bash
sudo nano /etc/systemd/system/tria-aibpo-backup.timer
```

Modify `OnCalendar` line:
```ini
# Daily at 2 AM
OnCalendar=*-*-* 02:00:00

# Every 6 hours
OnCalendar=*-*-* 00,06,12,18:00:00

# Weekly on Sunday at 3 AM
OnCalendar=Sun *-*-* 03:00:00
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart tria-aibpo-backup.timer
```

### Change Backup Retention

To change backup retention period (default: 7 days):

```bash
sudo nano /etc/systemd/system/tria-aibpo-backup.service
```

Modify cleanup commands:
```bash
# Keep last 30 days
ExecStartPost=/bin/bash -c 'find ${BACKUP_DIR} -name "*.sql.gz" -mtime +30 -delete'
ExecStartPost=/bin/bash -c 'find ${BACKUP_DIR} -name "*.tar.gz" -mtime +30 -delete'
```

Then reload:
```bash
sudo systemctl daemon-reload
```

## Backup Location

Backups are stored in `/opt/tria-aibpo/backups/` by default:

```bash
# List backups
ls -lh /opt/tria-aibpo/backups/

# View backup size
du -sh /opt/tria-aibpo/backups/

# Restore PostgreSQL backup
gunzip -c /opt/tria-aibpo/backups/postgres_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose --env-file /opt/tria-aibpo/.env exec -T postgres psql -U tria_admin -d tria_aibpo

# Extract application data backup
tar -xzf /opt/tria-aibpo/backups/data_YYYYMMDD_HHMMSS.tar.gz -C /opt/tria-aibpo/
```

## Troubleshooting

### Service Won't Start

1. Check service status:
```bash
sudo systemctl status tria-aibpo
```

2. View full logs:
```bash
sudo journalctl -u tria-aibpo -n 100 --no-pager
```

3. Verify Docker is running:
```bash
sudo systemctl status docker
```

4. Check environment file:
```bash
sudo ls -l /opt/tria-aibpo/.env
```

5. Test Docker Compose manually:
```bash
cd /opt/tria-aibpo
sudo docker compose --env-file .env up
```

### Service Keeps Restarting

1. Check logs for errors:
```bash
sudo journalctl -u tria-aibpo -f
```

2. Check Docker container logs:
```bash
cd /opt/tria-aibpo
docker compose --env-file .env logs -f
```

3. Verify environment variables:
```bash
sudo cat /opt/tria-aibpo/.env
```

### Backup Fails

1. Check backup service logs:
```bash
sudo journalctl -u tria-aibpo-backup -n 50
```

2. Verify backup directory exists:
```bash
sudo ls -l /opt/tria-aibpo/backups/
```

3. Check disk space:
```bash
df -h /opt/tria-aibpo/
```

4. Test manual backup:
```bash
sudo systemctl start tria-aibpo-backup.service
sudo journalctl -u tria-aibpo-backup -f
```

### Timer Not Running

1. Check timer status:
```bash
sudo systemctl status tria-aibpo-backup.timer
```

2. List all timers:
```bash
systemctl list-timers --all
```

3. Enable timer if disabled:
```bash
sudo systemctl enable tria-aibpo-backup.timer
sudo systemctl start tria-aibpo-backup.timer
```

## Monitoring

### Check System Health

```bash
# Overall service status
sudo systemctl status tria-aibpo

# Application health endpoint
curl http://localhost/health

# Docker container status
cd /opt/tria-aibpo && docker compose ps

# Resource usage
docker stats

# Recent logs
sudo journalctl -u tria-aibpo --since "1 hour ago"
```

### Watch Logs in Real-Time

```bash
# Application logs
sudo journalctl -u tria-aibpo -f

# Backup logs
sudo journalctl -u tria-aibpo-backup -f

# Docker container logs
cd /opt/tria-aibpo && docker compose logs -f

# Nginx logs
docker compose exec nginx tail -f /var/log/nginx/access.log
```

## Resource Limits

To set resource limits for the application, edit the service file:

```bash
sudo nano /etc/systemd/system/tria-aibpo.service
```

Uncomment and adjust:
```ini
[Service]
# Limit memory to 4GB
MemoryLimit=4G

# Limit CPU to 200% (2 cores)
CPUQuota=200%
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart tria-aibpo
```

## Uninstallation

To remove systemd services:

```bash
# Stop services
sudo systemctl stop tria-aibpo
sudo systemctl stop tria-aibpo-backup.timer

# Disable services
sudo systemctl disable tria-aibpo
sudo systemctl disable tria-aibpo-backup.timer

# Remove service files
sudo rm /etc/systemd/system/tria-aibpo.service
sudo rm /etc/systemd/system/tria-aibpo-backup.service
sudo rm /etc/systemd/system/tria-aibpo-backup.timer

# Reload systemd
sudo systemctl daemon-reload
```

## Additional Resources

- [systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [systemd Timer Documentation](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
