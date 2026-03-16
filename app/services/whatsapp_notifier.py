"""WhatsApp notification service for sending lead alerts to sales officers."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import requests
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.sales_officer import SalesOfficer
from app.models.whatsapp_notification import WhatsAppNotification
from app.utils.config import settings

logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    """Service for sending WhatsApp notifications via Business API."""
    
    def __init__(self):
        """Initialize WhatsApp notifier with API configuration."""
        self.api_url = settings.whatsapp_api_url
        self.access_token = settings.whatsapp_access_token
        self.phone_number_id = settings.whatsapp_phone_number_id
        self.template_name = "lead_alert"  # Must be pre-approved in WhatsApp Business
        
    def send_lead_alert(
        self,
        db: Session,
        lead: Lead,
        officer: SalesOfficer
    ) -> bool:
        """
        Send WhatsApp alert for a high-priority lead.
        
        Args:
            db: Database session
            lead: Lead to notify about
            officer: Sales officer to notify
        
        Returns:
            True if notification sent successfully, False otherwise
        """
        # Check if WhatsApp is configured
        if not self._is_configured():
            logger.warning("WhatsApp API not configured, skipping notification")
            return False
        
        # Check opt-in permission
        if not self.check_opt_in(officer):
            logger.info(f"Officer {officer.name} has not opted in to WhatsApp notifications")
            return False
        
        # Check service window (24-hour rule)
        if not self.respect_service_window(db, officer):
            logger.info(f"Service window exceeded for officer {officer.name}")
            return False
        
        # Prepare message
        try:
            message_data = self._prepare_message(lead, officer)
            
            # Send via WhatsApp API
            response = self._send_message(message_data)
            
            # Log notification
            status = "sent" if response else "failed"
            self._log_notification(db, lead, officer, status)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp notification: {e}")
            self._log_notification(db, lead, officer, "failed")
            return False
    
    def check_opt_in(self, officer: SalesOfficer) -> bool:
        """
        Check if officer has opted in to WhatsApp notifications.
        
        Args:
            officer: Sales officer to check
        
        Returns:
            True if opted in and has phone number, False otherwise
        """
        return (
            officer.whatsapp_opt_in and 
            officer.phone_number is not None and 
            len(officer.phone_number) > 0
        )
    
    def respect_service_window(
        self,
        db: Session,
        officer: SalesOfficer,
        window_hours: int = 24
    ) -> bool:
        """
        Check if we can send a message within the 24-hour service window.
        
        WhatsApp Business API requires that business-initiated messages
        are sent within 24 hours of the last user message, or use
        approved templates.
        
        Args:
            db: Database session
            officer: Sales officer to check
            window_hours: Service window in hours (default: 24)
        
        Returns:
            True if within service window, False otherwise
        """
        # Get last notification sent to this officer
        last_notification = (
            db.query(WhatsAppNotification)
            .filter(WhatsAppNotification.officer_id == officer.id)
            .order_by(WhatsAppNotification.sent_at.desc())
            .first()
        )
        
        if not last_notification:
            return True  # No previous notification, OK to send
        
        # Check if enough time has passed
        time_since_last = datetime.utcnow() - last_notification.sent_at
        return time_since_last >= timedelta(hours=window_hours)
    
    def _is_configured(self) -> bool:
        """Check if WhatsApp API is properly configured."""
        return all([
            self.access_token,
            self.phone_number_id,
            self.api_url
        ])
    
    def _prepare_message(self, lead: Lead, officer: SalesOfficer) -> Dict[str, Any]:
        """
        Prepare WhatsApp message payload using approved template.
        
        Args:
            lead: Lead to notify about
            officer: Sales officer receiving notification
        
        Returns:
            Message payload for WhatsApp API
        """
        # Get lead details
        company_name = lead.company.name if lead.company else "Unknown Company"
        event_summary = lead.event.event_summary if lead.event else "New opportunity"
        location = lead.event.location if lead.event and lead.event.location else "Location TBD"
        
        # Get top 3 products
        products = []
        if lead.products:
            sorted_products = sorted(lead.products, key=lambda p: p.rank or 999)
            products = [p.product_name for p in sorted_products[:3]]
        product_list = ", ".join(products) if products else "Products TBD"
        
        # Generate dossier link
        dossier_link = f"{settings.frontend_url}/leads/{lead.id}"
        
        # Format phone number (ensure it has country code)
        phone_number = officer.phone_number
        if not phone_number.startswith("+"):
            phone_number = f"+{phone_number}"
        
        # Prepare template message
        # Note: Template must be pre-approved in WhatsApp Business Manager
        message_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": self.template_name,
                "language": {
                    "code": "en"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": company_name},
                            {"type": "text", "text": event_summary},
                            {"type": "text", "text": product_list},
                            {"type": "text", "text": location},
                            {"type": "text", "text": dossier_link}
                        ]
                    }
                ]
            }
        }
        
        return message_payload
    
    def _send_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Send message via WhatsApp Cloud API.
        
        Args:
            message_data: Message payload
        
        Returns:
            True if sent successfully, False otherwise
        """
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                url,
                json=message_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"WhatsApp message sent successfully: {response.json()}")
                return True
            else:
                logger.error(
                    f"WhatsApp API error: {response.status_code} - {response.text}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False
    
    def _log_notification(
        self,
        db: Session,
        lead: Lead,
        officer: SalesOfficer,
        status: str
    ) -> None:
        """
        Log WhatsApp notification attempt to database.
        
        Args:
            db: Database session
            lead: Lead that was notified about
            officer: Officer who was notified
            status: Notification status ('sent', 'delivered', 'failed')
        """
        try:
            notification = WhatsAppNotification(
                lead_id=lead.id,
                officer_id=officer.id,
                template_id=self.template_name,
                status=status
            )
            db.add(notification)
            db.commit()
            logger.info(f"Logged WhatsApp notification: {status}")
        except Exception as e:
            logger.error(f"Failed to log WhatsApp notification: {e}")
            db.rollback()
