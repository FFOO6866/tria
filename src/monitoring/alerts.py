"""
Alerting System
===============

Production-grade alerting for monitoring thresholds and anomalies.

Features:
1. Configurable alert rules
2. Multiple notification channels (email, Slack, webhook)
3. Alert suppression (avoid notification spam)
4. Alert history tracking
5. Automatic recovery notifications

Alert Types:
- High error rate
- High response time
- Low cache hit rate
- High memory usage
- High rate limit block rate
- System unhealthy

Usage:
    from monitoring.alerts import AlertManager, AlertRule

    # Create alert manager
    manager = AlertManager()

    # Add alert rules
    manager.add_rule(AlertRule(
        name="high_error_rate",
        metric="error_rate",
        threshold=10.0,
        comparison="greater_than",
        severity="critical"
    ))

    # Check alerts
    manager.check_alerts()
"""

import os
import time
import smtplib
import requests
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .metrics import metrics_collector, cache_metrics, error_metrics, memory_metrics
from .logger import app_logger


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ComparisonOperator(Enum):
    """Comparison operators for alert conditions"""
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"


@dataclass
class AlertRule:
    """
    Alert rule definition

    Attributes:
        name: Unique alert name
        metric: Metric to monitor (or custom function)
        threshold: Threshold value for triggering alert
        comparison: Comparison operator
        severity: Alert severity level
        description: Human-readable description
        cooldown_minutes: Minimum time between alerts (default: 15)
        enabled: Whether rule is active
    """
    name: str
    metric: str  # Can be metric name or custom function
    threshold: float
    comparison: ComparisonOperator
    severity: AlertSeverity
    description: str = ""
    cooldown_minutes: int = 15
    enabled: bool = True
    custom_check: Optional[Callable[[], float]] = None


@dataclass
class Alert:
    """
    Triggered alert instance

    Attributes:
        rule_name: Name of the rule that triggered
        severity: Alert severity
        message: Alert message
        value: Current metric value
        threshold: Threshold that was exceeded
        timestamp: When alert was triggered
        metadata: Additional context
    """
    rule_name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """
    Manages alert rules and notifications

    Monitors metrics and sends notifications when thresholds are exceeded.
    Includes cooldown periods to avoid alert spam.
    """

    def __init__(
        self,
        email_enabled: bool = False,
        slack_enabled: bool = False,
        webhook_enabled: bool = False
    ):
        """
        Initialize alert manager

        Args:
            email_enabled: Enable email notifications
            slack_enabled: Enable Slack notifications
            webhook_enabled: Enable webhook notifications
        """
        self.rules: Dict[str, AlertRule] = {}
        self.alert_history: List[Alert] = []
        self.last_alert_time: Dict[str, datetime] = {}

        # Notification settings
        self.email_enabled = email_enabled
        self.slack_enabled = slack_enabled
        self.webhook_enabled = webhook_enabled

        # Load configuration from environment
        self.smtp_host = os.getenv("ALERT_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("ALERT_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("ALERT_SMTP_USER", "")
        self.smtp_password = os.getenv("ALERT_SMTP_PASSWORD", "")
        self.alert_email_to = os.getenv("ALERT_EMAIL_TO", "")

        self.slack_webhook_url = os.getenv("ALERT_SLACK_WEBHOOK", "")
        self.webhook_url = os.getenv("ALERT_WEBHOOK_URL", "")

        # Initialize default rules
        self._initialize_default_rules()

        app_logger.info(
            "AlertManager initialized",
            email_enabled=email_enabled,
            slack_enabled=slack_enabled,
            webhook_enabled=webhook_enabled
        )

    def _initialize_default_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                metric="error_rate_per_minute",
                threshold=5.0,
                comparison=ComparisonOperator.GREATER_THAN,
                severity=AlertSeverity.ERROR,
                description="Error rate exceeded 5 errors/minute",
                cooldown_minutes=15
            ),
            AlertRule(
                name="very_high_error_rate",
                metric="error_rate_per_minute",
                threshold=10.0,
                comparison=ComparisonOperator.GREATER_THAN,
                severity=AlertSeverity.CRITICAL,
                description="Error rate exceeded 10 errors/minute (CRITICAL)",
                cooldown_minutes=5
            ),
            AlertRule(
                name="high_response_time_p95",
                metric="response_time_p95",
                threshold=5000.0,  # 5 seconds
                comparison=ComparisonOperator.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                description="P95 response time exceeded 5 seconds",
                cooldown_minutes=15
            ),
            AlertRule(
                name="low_cache_hit_rate",
                metric="cache_hit_rate",
                threshold=30.0,  # 30%
                comparison=ComparisonOperator.LESS_THAN,
                severity=AlertSeverity.WARNING,
                description="Cache hit rate below 30%",
                cooldown_minutes=30
            ),
            AlertRule(
                name="high_memory_usage",
                metric="memory_mb",
                threshold=1500.0,  # 1.5GB
                comparison=ComparisonOperator.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                description="Memory usage exceeded 1.5GB",
                cooldown_minutes=15
            ),
            AlertRule(
                name="critical_memory_usage",
                metric="memory_mb",
                threshold=2000.0,  # 2GB
                comparison=ComparisonOperator.GREATER_THAN,
                severity=AlertSeverity.CRITICAL,
                description="Memory usage exceeded 2GB (CRITICAL)",
                cooldown_minutes=10
            ),
            AlertRule(
                name="high_rate_limit_block_rate",
                metric="rate_limit_block_rate",
                threshold=20.0,  # 20%
                comparison=ComparisonOperator.GREATER_THAN,
                severity=AlertSeverity.INFO,
                description="Rate limit block rate exceeded 20%",
                cooldown_minutes=30
            ),
            AlertRule(
                name="low_success_rate",
                metric="request_success_rate",
                threshold=95.0,  # 95%
                comparison=ComparisonOperator.LESS_THAN,
                severity=AlertSeverity.ERROR,
                description="Request success rate below 95%",
                cooldown_minutes=15
            )
        ]

        for rule in default_rules:
            self.add_rule(rule)

    def add_rule(self, rule: AlertRule):
        """
        Add alert rule

        Args:
            rule: AlertRule to add
        """
        self.rules[rule.name] = rule
        app_logger.info(
            "Alert rule added",
            rule_name=rule.name,
            severity=rule.severity.value,
            threshold=rule.threshold
        )

    def remove_rule(self, rule_name: str):
        """Remove alert rule by name"""
        if rule_name in self.rules:
            del self.rules[rule_name]
            app_logger.info("Alert rule removed", rule_name=rule_name)

    def enable_rule(self, rule_name: str):
        """Enable alert rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True

    def disable_rule(self, rule_name: str):
        """Disable alert rule"""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False

    def check_alerts(self) -> List[Alert]:
        """
        Check all alert rules and trigger notifications

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            # Check cooldown period
            if self._is_in_cooldown(rule_name, rule.cooldown_minutes):
                continue

            # Get metric value
            if rule.custom_check:
                current_value = rule.custom_check()
            else:
                current_value = self._get_metric_value(rule.metric)

            if current_value is None:
                continue

            # Check condition
            should_alert = self._check_condition(
                current_value,
                rule.threshold,
                rule.comparison
            )

            if should_alert:
                alert = Alert(
                    rule_name=rule_name,
                    severity=rule.severity,
                    message=rule.description or f"{rule_name} triggered",
                    value=current_value,
                    threshold=rule.threshold,
                    metadata={
                        "metric": rule.metric,
                        "comparison": rule.comparison.value
                    }
                )

                triggered_alerts.append(alert)
                self.alert_history.append(alert)
                self.last_alert_time[rule_name] = datetime.now()

                # Send notifications
                self._send_notifications(alert)

                # Log alert
                app_logger.warning(
                    f"Alert triggered: {rule_name}",
                    severity=alert.severity.value,
                    value=current_value,
                    threshold=rule.threshold,
                    rule_name=rule_name
                )

        return triggered_alerts

    def _get_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for a metric"""
        if metric_name == "error_rate_per_minute":
            return error_metrics.get_error_rate(60)
        elif metric_name == "response_time_p95":
            summary = metrics_collector.get_summary("response_time_ms")
            return summary.p95_value if summary else None
        elif metric_name == "response_time_mean":
            summary = metrics_collector.get_summary("response_time_ms")
            return summary.mean_value if summary else None
        elif metric_name == "cache_hit_rate":
            return cache_metrics.get_hit_rate()
        elif metric_name == "memory_mb":
            return memory_metrics.get_current_mb()
        elif metric_name == "rate_limit_block_rate":
            blocked = metrics_collector.get_counter("rate_limit_blocked")
            total = metrics_collector.get_counter("rate_limit_requests")
            return (blocked / total * 100) if total > 0 else 0.0
        elif metric_name == "request_success_rate":
            succeeded = metrics_collector.get_counter("requests_succeeded")
            total = metrics_collector.get_counter("requests_total")
            return (succeeded / total * 100) if total > 0 else 100.0
        else:
            return None

    def _check_condition(
        self,
        value: float,
        threshold: float,
        comparison: ComparisonOperator
    ) -> bool:
        """Check if condition is met"""
        if comparison == ComparisonOperator.GREATER_THAN:
            return value > threshold
        elif comparison == ComparisonOperator.LESS_THAN:
            return value < threshold
        elif comparison == ComparisonOperator.EQUALS:
            return value == threshold
        elif comparison == ComparisonOperator.NOT_EQUALS:
            return value != threshold
        return False

    def _is_in_cooldown(self, rule_name: str, cooldown_minutes: int) -> bool:
        """Check if alert is in cooldown period"""
        if rule_name not in self.last_alert_time:
            return False

        elapsed = datetime.now() - self.last_alert_time[rule_name]
        return elapsed < timedelta(minutes=cooldown_minutes)

    def _send_notifications(self, alert: Alert):
        """Send alert notifications to all enabled channels"""
        if self.email_enabled and self.alert_email_to:
            try:
                self._send_email_notification(alert)
            except Exception as e:
                app_logger.error("Failed to send email alert", error=e)

        if self.slack_enabled and self.slack_webhook_url:
            try:
                self._send_slack_notification(alert)
            except Exception as e:
                app_logger.error("Failed to send Slack alert", error=e)

        if self.webhook_enabled and self.webhook_url:
            try:
                self._send_webhook_notification(alert)
            except Exception as e:
                app_logger.error("Failed to send webhook alert", error=e)

    def _send_email_notification(self, alert: Alert):
        """Send email notification"""
        if not self.smtp_user or not self.alert_email_to:
            return

        subject = f"[{alert.severity.value.upper()}] TRIA Alert: {alert.rule_name}"

        body = f"""
TRIA System Alert

Severity: {alert.severity.value.upper()}
Alert: {alert.rule_name}
Message: {alert.message}

Current Value: {alert.value:.2f}
Threshold: {alert.threshold:.2f}
Time: {alert.timestamp.isoformat()}

Metadata:
{self._format_dict(alert.metadata)}

---
This is an automated alert from TRIA monitoring system.
"""

        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = self.alert_email_to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            if self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

        app_logger.info("Email alert sent", rule_name=alert.rule_name)

    def _send_slack_notification(self, alert: Alert):
        """Send Slack notification"""
        # Color based on severity
        color = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.ERROR: "#f44336",
            AlertSeverity.CRITICAL: "#9c27b0"
        }.get(alert.severity, "#cccccc")

        payload = {
            "attachments": [{
                "color": color,
                "title": f"{alert.severity.value.upper()}: {alert.rule_name}",
                "text": alert.message,
                "fields": [
                    {
                        "title": "Current Value",
                        "value": f"{alert.value:.2f}",
                        "short": True
                    },
                    {
                        "title": "Threshold",
                        "value": f"{alert.threshold:.2f}",
                        "short": True
                    }
                ],
                "footer": "TRIA Monitoring",
                "ts": int(alert.timestamp.timestamp())
            }]
        }

        response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        app_logger.info("Slack alert sent", rule_name=alert.rule_name)

    def _send_webhook_notification(self, alert: Alert):
        """Send generic webhook notification"""
        payload = {
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "message": alert.message,
            "value": alert.value,
            "threshold": alert.threshold,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata
        }

        response = requests.post(self.webhook_url, json=payload, timeout=10)
        response.raise_for_status()

        app_logger.info("Webhook alert sent", rule_name=alert.rule_name)

    def _format_dict(self, d: Dict) -> str:
        """Format dictionary for email body"""
        return "\n".join(f"  {k}: {v}" for k, v in d.items())

    def get_alert_history(self, limit: int = 50) -> List[Alert]:
        """
        Get recent alert history

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts
        """
        return self.alert_history[-limit:]

    def get_alert_summary(self) -> Dict[str, Any]:
        """
        Get summary of alert status

        Returns:
            Dictionary with alert statistics
        """
        total_alerts = len(self.alert_history)

        # Count by severity
        by_severity = {}
        for alert in self.alert_history:
            severity = alert.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # Recent alerts (last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_alerts = [
            a for a in self.alert_history
            if a.timestamp > one_hour_ago
        ]

        return {
            "total_alerts": total_alerts,
            "recent_alerts_1h": len(recent_alerts),
            "by_severity": by_severity,
            "active_rules": len([r for r in self.rules.values() if r.enabled]),
            "disabled_rules": len([r for r in self.rules.values() if not r.enabled])
        }


# Global alert manager instance
alert_manager = AlertManager(
    email_enabled=bool(os.getenv("ALERT_EMAIL_ENABLED", "")),
    slack_enabled=bool(os.getenv("ALERT_SLACK_ENABLED", "")),
    webhook_enabled=bool(os.getenv("ALERT_WEBHOOK_ENABLED", ""))
)


def check_alerts_periodically(interval_seconds: int = 60):
    """
    Background function to check alerts periodically

    Args:
        interval_seconds: How often to check alerts (default: 60)

    Usage:
        import threading
        thread = threading.Thread(target=check_alerts_periodically, daemon=True)
        thread.start()
    """
    while True:
        try:
            triggered = alert_manager.check_alerts()
            if triggered:
                app_logger.info(
                    "Periodic alert check completed",
                    triggered_count=len(triggered)
                )
        except Exception as e:
            app_logger.error("Alert check failed", error=e)

        time.sleep(interval_seconds)
