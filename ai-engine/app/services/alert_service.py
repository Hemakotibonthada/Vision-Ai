"""
Vision-AI Alert Service
Features: Rule engine, notifications, webhooks, email alerts
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger

import aiohttp

from app.config import settings


class AlertService:
    """Alert rule engine with multi-channel notifications."""

    def __init__(self):
        self.rules = []
        self.alert_history = []
        self.alert_count = 0
        self.cooldowns = {}

    def add_rule(self, rule: Dict):
        """Add an alert rule."""
        self.rules.append({
            "id": len(self.rules) + 1,
            "name": rule.get("name", "Unnamed Rule"),
            "event_type": rule.get("event_type", "detection"),
            "condition": rule.get("condition", {}),
            "actions": rule.get("actions", []),
            "is_active": rule.get("is_active", True),
            "cooldown": rule.get("cooldown", 60),
            "created_at": datetime.utcnow().isoformat()
        })
        logger.info(f"Alert rule added: {rule.get('name')}")

    async def evaluate(self, event: Dict) -> List[Dict]:
        """Evaluate all rules against an event."""
        triggered = []

        for rule in self.rules:
            if not rule.get("is_active"):
                continue

            if rule["event_type"] != event.get("type"):
                continue

            # Check cooldown
            rule_id = rule["id"]
            if rule_id in self.cooldowns:
                if datetime.utcnow() < self.cooldowns[rule_id]:
                    continue

            # Evaluate condition
            if self._check_condition(rule["condition"], event):
                # Set cooldown
                self.cooldowns[rule_id] = datetime.utcnow() + timedelta(seconds=rule["cooldown"])

                # Execute actions
                for action in rule["actions"]:
                    await self._execute_action(action, event, rule)

                alert_record = {
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "event": event,
                    "triggered_at": datetime.utcnow().isoformat()
                }
                triggered.append(alert_record)
                self.alert_history.append(alert_record)
                self.alert_count += 1

        # Keep last 500 alerts
        if len(self.alert_history) > 500:
            self.alert_history = self.alert_history[-500:]

        return triggered

    def _check_condition(self, condition: Dict, event: Dict) -> bool:
        """Evaluate condition against event data."""
        if not condition:
            return True

        field = condition.get("field", "")
        op = condition.get("op", "==")
        value = condition.get("value")

        # Get nested field value
        event_value = event
        for key in field.split("."):
            if isinstance(event_value, dict):
                event_value = event_value.get(key)
            else:
                return False

        if event_value is None:
            return False

        try:
            if op == "==": return event_value == value
            elif op == "!=": return event_value != value
            elif op == ">": return float(event_value) > float(value)
            elif op == "<": return float(event_value) < float(value)
            elif op == ">=": return float(event_value) >= float(value)
            elif op == "<=": return float(event_value) <= float(value)
            elif op == "contains": return value in str(event_value)
            elif op == "in": return event_value in value
            else: return False
        except (ValueError, TypeError):
            return False

    async def _execute_action(self, action: Dict, event: Dict, rule: Dict):
        """Execute notification action."""
        action_type = action.get("type", "")

        try:
            if action_type == "webhook":
                await self._send_webhook(action.get("url", settings.WEBHOOK_URL), event, rule)
            elif action_type == "email":
                await self._send_email(action.get("target", settings.ALERT_EMAIL), event, rule)
            elif action_type == "slack":
                await self._send_slack(action.get("webhook", settings.SLACK_WEBHOOK), event, rule)
            elif action_type == "mqtt":
                await self._send_mqtt(action.get("topic", ""), event)
            elif action_type == "log":
                logger.warning(f"ALERT [{rule['name']}]: {json.dumps(event)}")
        except Exception as e:
            logger.error(f"Action failed ({action_type}): {e}")

    # Feature 200: Webhook notifications
    async def _send_webhook(self, url: str, event: Dict, rule: Dict):
        if not url:
            return
        payload = {
            "alert": rule["name"],
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "Vision-AI"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                logger.info(f"Webhook sent: {resp.status}")

    # Feature 201: Email alerts
    async def _send_email(self, target: str, event: Dict, rule: Dict):
        if not target or not settings.SMTP_USER:
            return
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USER
            msg["To"] = target
            msg["Subject"] = f"Vision-AI Alert: {rule['name']}"

            body = f"""
            <h2>Vision-AI Alert</h2>
            <p><strong>Rule:</strong> {rule['name']}</p>
            <p><strong>Event Type:</strong> {event.get('type', 'N/A')}</p>
            <p><strong>Time:</strong> {datetime.utcnow().isoformat()}</p>
            <pre>{json.dumps(event, indent=2)}</pre>
            """
            msg.attach(MIMEText(body, "html"))

            await aiosmtplib.send(
                msg, hostname=settings.SMTP_HOST, port=settings.SMTP_PORT,
                username=settings.SMTP_USER, password=settings.SMTP_PASSWORD,
                use_tls=True
            )
            logger.info(f"Email sent to {target}")
        except Exception as e:
            logger.error(f"Email failed: {e}")

    # Feature 203: Slack notifications
    async def _send_slack(self, webhook_url: str, event: Dict, rule: Dict):
        if not webhook_url:
            return
        payload = {
            "text": f"🚨 *Vision-AI Alert*\n*Rule:* {rule['name']}\n*Event:* {event.get('type')}\n*Time:* {datetime.utcnow().isoformat()}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                logger.info(f"Slack notification sent: {resp.status}")

    async def _send_mqtt(self, topic: str, event: Dict):
        # MQTT publish handled by MQTT service
        pass

    def get_rules(self) -> List[Dict]:
        return self.rules

    def get_history(self, limit: int = 50) -> List[Dict]:
        return self.alert_history[-limit:]

    def get_stats(self) -> Dict:
        return {
            "total_rules": len(self.rules),
            "active_rules": sum(1 for r in self.rules if r.get("is_active")),
            "total_alerts": self.alert_count,
            "recent_alerts": len(self.alert_history)
        }


# Singleton
alert_service = AlertService()
