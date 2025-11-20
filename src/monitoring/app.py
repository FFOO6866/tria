"""
Monitoring Dashboard Flask Application
========================================

Standalone Flask app for serving monitoring dashboard and API endpoints.

Usage:
    python -m monitoring.app

Access:
    - Dashboard: http://localhost:5001/
    - Health: http://localhost:5001/monitoring/health
    - Metrics: http://localhost:5001/monitoring/metrics
    - Detailed: http://localhost:5001/monitoring/metrics/detailed
"""

import os
from flask import Flask, send_file
from pathlib import Path

# Import monitoring blueprint
from .api import monitoring_bp


# Create Flask app
app = Flask(__name__)

# Register monitoring blueprint
app.register_blueprint(monitoring_bp, url_prefix='/monitoring')


@app.route('/')
def dashboard():
    """Serve the monitoring dashboard HTML"""
    dashboard_path = Path(__file__).parent / 'dashboard.html'
    return send_file(dashboard_path)


@app.route('/health')
def root_health():
    """Health check at root level"""
    from .api import get_health_status
    from flask import jsonify
    health_status = get_health_status()
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code


if __name__ == '__main__':
    print("=" * 80)
    print("TRIA Monitoring Dashboard")
    print("=" * 80)
    print()
    print("Starting monitoring dashboard server...")
    print()
    print("Access the dashboard at:")
    print("  - Dashboard: http://localhost:5001/")
    print("  - Health: http://localhost:5001/monitoring/health")
    print("  - Metrics: http://localhost:5001/monitoring/metrics")
    print("  - Errors: http://localhost:5001/monitoring/metrics/errors")
    print("  - Cache: http://localhost:5001/monitoring/metrics/cache")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()

    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )
