"""Notification system for sending alerts."""
import httpx
import asyncio
from typing import Dict, Any, Optional
import structlog
from src.config import settings

logger = structlog.get_logger()


class Notifier:
    """Sends notifications about scan findings."""
    
    def __init__(self):
        """Initialize notifier."""
        self.enabled = settings.enable_notifications
        self.webhook_url = settings.webhook_url
        self.slack_webhook = settings.slack_webhook
        logger.info("notifier_initialized", enabled=self.enabled)
    
    async def send_finding(
        self,
        bucket_name: str,
        provider: str,
        risk_level: str,
        details: Dict[str, Any]
    ) -> bool:
        """Send notification about a finding.
        
        Args:
            bucket_name: Name of the bucket
            provider: Cloud provider
            risk_level: Risk level (low, medium, high, critical)
            details: Additional finding details
            
        Returns:
            True if notification was sent successfully
        """
        if not self.enabled:
            return False
        
        # Only send notifications for medium+ risk
        if risk_level.lower() not in ['medium', 'high', 'critical']:
            return False
        
        message = self._format_message(bucket_name, provider, risk_level, details)
        
        success = True
        
        # Send to Slack if configured
        if self.slack_webhook:
            success = success and await self._send_slack(message)
        
        # Send to generic webhook if configured
        if self.webhook_url:
            success = success and await self._send_webhook(message)
        
        return success
    
    def _format_message(
        self,
        bucket_name: str,
        provider: str,
        risk_level: str,
        details: Dict[str, Any]
    ) -> str:
        """Format notification message.
        
        Args:
            bucket_name: Bucket name
            provider: Cloud provider
            risk_level: Risk level
            details: Finding details
            
        Returns:
            Formatted message string
        """
        emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }.get(risk_level.lower(), '⚪')
        
        message = f"{emoji} **{risk_level.upper()} Risk Finding**\n\n"
        message += f"**Bucket:** {bucket_name}\n"
        message += f"**Provider:** {provider}\n"
        message += f"**URL:** {details.get('url', 'N/A')}\n\n"
        
        if details.get('is_accessible'):
            message += "✅ Publicly accessible\n"
        
        if details.get('sensitive_files'):
            count = len(details['sensitive_files'])
            message += f"⚠️ {count} sensitive file(s) detected\n"
        
        if details.get('recommendations'):
            message += "\n**Recommendations:**\n"
            for rec in details['recommendations'][:3]:  # First 3
                message += f"• {rec}\n"
        
        return message
    
    async def _send_slack(self, message: str) -> bool:
        """Send notification to Slack.
        
        Args:
            message: Message to send
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.slack_webhook,
                    json={'text': message},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("slack_notification_sent")
                    return True
                else:
                    logger.error("slack_notification_failed", status=response.status_code)
                    return False
                    
        except Exception as e:
            logger.error("slack_notification_error", error=str(e))
            return False
    
    async def _send_webhook(self, message: str) -> bool:
        """Send notification to generic webhook.
        
        Args:
            message: Message to send
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json={
                        'message': message,
                        'timestamp': int(asyncio.get_event_loop().time())
                    },
                    timeout=10.0
                )
                
                if response.status_code < 400:
                    logger.info("webhook_notification_sent")
                    return True
                else:
                    logger.error("webhook_notification_failed", status=response.status_code)
                    return False
                    
        except Exception as e:
            logger.error("webhook_notification_error", error=str(e))
            return False
    
    async def send_summary(self, summary: Dict[str, Any]) -> bool:
        """Send scan summary notification.
        
        Args:
            summary: Scan summary statistics
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        message = "📊 **Scan Summary**\n\n"
        message += f"**Total Scans:** {summary.get('total_scans', 0)}\n"
        message += f"**Public Buckets:** {summary.get('public_count', 0)}\n"
        message += f"**Critical Findings:** {summary.get('critical_count', 0)}\n"
        message += f"**High Risk:** {summary.get('high_count', 0)}\n"
        message += f"**Medium Risk:** {summary.get('medium_count', 0)}\n"
        
        success = True
        
        if self.slack_webhook:
            success = success and await self._send_slack(message)
        
        if self.webhook_url:
            success = success and await self._send_webhook(message)
        
        return success
