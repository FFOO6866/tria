# Monitoring Setup Guide
**Tria AI-BPO Production Monitoring**

This directory contains configuration files for setting up production monitoring with Prometheus, Grafana, and Alertmanager.

---

## Quick Start

### 1. Install Prometheus

```bash
# Download Prometheus
cd /opt
wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
tar xvf prometheus-2.48.0.linux-amd64.tar.gz
cd prometheus-2.48.0.linux-amd64

# Copy configuration
cp /path/to/tria/monitoring/prometheus.yml ./
cp /path/to/tria/monitoring/alerts.yml ./

# Start Prometheus
./prometheus --config.file=prometheus.yml
```

Access Prometheus UI: http://YOUR_SERVER:9090

### 2. Install Grafana

```bash
# Add Grafana repository (Ubuntu/Debian)
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -

# Install
sudo apt-get update
sudo apt-get install grafana

# Start Grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

Access Grafana UI: http://YOUR_SERVER:3000 (admin/admin)

### 3. Install Alertmanager

```bash
# Download Alertmanager
cd /opt
wget https://github.com/prometheus/alertmanager/releases/download/v0.26.0/alertmanager-0.26.0.linux-amd64.tar.gz
tar xvf alertmanager-0.26.0.linux-amd64.tar.gz
cd alertmanager-0.26.0.linux-amd64

# Copy configuration (create alertmanager.yml from template below)
cp /path/to/tria/monitoring/alertmanager.yml ./

# Start Alertmanager
./alertmanager --config.file=alertmanager.yml
```

Access Alertmanager UI: http://YOUR_SERVER:9093

---

## Component Setup

### A. Backend Metrics Exporter

Add Prometheus metrics to your FastAPI backend:

```bash
# Install prometheus client
pip install prometheus-fastapi-instrumentator

# Add to requirements.txt
echo "prometheus-fastapi-instrumentator==6.1.0" >> requirements.txt
```

Edit `src/enhanced_api.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Add Prometheus instrumentation
Instrumentator().instrument(app).expose(app)
# This creates /metrics endpoint automatically
```

Restart backend:
```bash
docker-compose restart backend
```

Verify: http://localhost:8003/metrics

### B. PostgreSQL Exporter

```bash
# Install postgres_exporter
docker run -d \
  --name postgres_exporter \
  --network tria_aibpo_network \
  -e DATA_SOURCE_NAME="postgresql://tria_admin:PASSWORD@postgres:5432/tria_aibpo?sslmode=disable" \
  -p 9187:9187 \
  prometheuscommunity/postgres-exporter
```

### C. Redis Exporter

```bash
# Install redis_exporter
docker run -d \
  --name redis_exporter \
  --network tria_aibpo_network \
  -e REDIS_ADDR=redis:6379 \
  -e REDIS_PASSWORD=YOUR_REDIS_PASSWORD \
  -p 9121:9121 \
  oliver006/redis_exporter
```

### D. Node Exporter (System Metrics)

```bash
# Install node_exporter
cd /opt
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvf node_exporter-1.7.0.linux-amd64.tar.gz
cd node_exporter-1.7.0.linux-amd64

# Run as systemd service
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/opt/node_exporter-1.7.0.linux-amd64/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter
```

---

## Grafana Dashboard Setup

### 1. Add Prometheus Data Source

1. Open Grafana: http://YOUR_SERVER:3000
2. Login (admin/admin, change password)
3. Go to Configuration → Data Sources
4. Click "Add data source"
5. Select "Prometheus"
6. URL: `http://localhost:9090`
7. Click "Save & Test"

### 2. Import Pre-Built Dashboards

**Node Exporter Dashboard** (System Metrics):
- Dashboard ID: `1860`
- Go to Dashboards → Import
- Enter ID: 1860
- Select Prometheus data source
- Click "Import"

**PostgreSQL Dashboard**:
- Dashboard ID: `9628`
- Follow same import process

**Redis Dashboard**:
- Dashboard ID: `11835`
- Follow same import process

### 3. Create Custom Tria Dashboard

Create a new dashboard with these panels:

**Panel 1: Request Rate**
```promql
rate(http_requests_total[5m])
```

**Panel 2: P95 Latency**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Panel 3: Error Rate**
```promql
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
```

**Panel 4: Cache Hit Rate**
```promql
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

**Panel 5: Active Database Connections**
```promql
pg_stat_activity_count
```

**Panel 6: Memory Usage**
```promql
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
```

---

## Alertmanager Configuration

Create `alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

# PagerDuty integration
route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'pagerduty'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .CommonAnnotations.summary }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'

  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
```

---

## PagerDuty Setup

### 1. Create Service

1. Go to PagerDuty → Services → New Service
2. Name: "Tria AI-BPO Production"
3. Escalation Policy: Create or select existing
4. Integration: "Use our API directly - Events API v2"
5. Copy "Integration Key"

### 2. Configure Alertmanager

Edit `alertmanager.yml`:
```yaml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_INTEGRATION_KEY_HERE'
```

Restart Alertmanager:
```bash
sudo systemctl restart alertmanager
```

### 3. Test Alert

Trigger a test alert:
```bash
curl -X POST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "critical"
    },
    "annotations": {
      "summary": "Test alert from Tria monitoring"
    }
  }]'
```

---

## Slack Integration (Optional)

### 1. Create Slack Webhook

1. Go to https://api.slack.com/apps
2. Create New App → "From scratch"
3. Name: "Tria Monitoring"
4. Select workspace
5. Go to "Incoming Webhooks"
6. Activate webhooks
7. Add New Webhook to Workspace
8. Select channel (#alerts)
9. Copy webhook URL

### 2. Configure Alertmanager

Edit `alertmanager.yml`:
```yaml
receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_WEBHOOK_URL_HERE'
        channel: '#alerts'
        title: '{{ .CommonAnnotations.summary }}'
        text: '{{ .CommonAnnotations.description }}'
```

---

## Verification Checklist

After setup, verify:

- [ ] Prometheus UI accessible (http://localhost:9090)
- [ ] Grafana UI accessible (http://localhost:3000)
- [ ] Alertmanager UI accessible (http://localhost:9093)
- [ ] Backend /metrics endpoint working (http://localhost:8003/metrics)
- [ ] All exporters running (postgres, redis, node)
- [ ] Prometheus scraping all targets (check Status → Targets)
- [ ] Grafana dashboards showing data
- [ ] Test alert delivered to PagerDuty/Slack
- [ ] Alert rules loaded (check Prometheus → Alerts)

---

## Troubleshooting

### Prometheus not scraping backend

```bash
# Check if /metrics endpoint exists
curl http://localhost:8003/metrics

# Check Prometheus targets
# Go to http://localhost:9090/targets
# All targets should show "UP"

# Check Prometheus logs
docker logs prometheus
```

### No data in Grafana

```bash
# Test Prometheus connection
curl http://localhost:9090/api/v1/query?query=up

# Check Grafana data source connection
# Grafana UI → Configuration → Data Sources → Prometheus → Test
```

### Alerts not firing

```bash
# Check alert rules are loaded
curl http://localhost:9090/api/v1/rules

# Check Alertmanager is receiving alerts
curl http://localhost:9093/api/v1/alerts

# Check Alertmanager logs
tail -f /opt/alertmanager/alertmanager.log
```

---

## Maintenance

### Update Prometheus

```bash
cd /opt
wget https://github.com/prometheus/prometheus/releases/download/vX.XX.X/prometheus-X.XX.X.linux-amd64.tar.gz
tar xvf prometheus-X.XX.X.linux-amd64.tar.gz
# Copy config files
cp prometheus-old/prometheus.yml prometheus-X.XX.X/
cp prometheus-old/alerts.yml prometheus-X.XX.X/
# Restart with new version
```

### Backup Configuration

```bash
# Backup all monitoring configs
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz \
  /opt/prometheus/prometheus.yml \
  /opt/prometheus/alerts.yml \
  /opt/alertmanager/alertmanager.yml \
  /var/lib/grafana/grafana.db
```

---

## Contact

- **On-Call**: See /docs/OPERATIONAL_RUNBOOK.md
- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/
- **PagerDuty Support**: https://support.pagerduty.com/

---

**Last Updated**: 2025-11-14
**Version**: 1.0
