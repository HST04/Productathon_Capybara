"""Unit tests for WhatsApp notification service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid

from app.services.whatsapp_notifier import WhatsAppNotifier
from app.models.lead import Lead
from app.models.sales_officer import SalesOfficer
from app.models.company import Company
from app.models.event import Event
from app.models.lead_product import LeadProduct
from app.models.whatsapp_notification import WhatsAppNotification


class TestWhatsAppNotifier:
    """Test suite for WhatsApp notification service."""
    
    @pytest.fixture
    def notifier(self):
        """Create WhatsApp notifier instance."""
        with patch('app.services.whatsapp_notifier.settings') as mock_settings:
            mock_settings.whatsapp_api_url = "https://graph.facebook.com/v18.0"
            mock_settings.whatsapp_access_token = "test_token"
            mock_settings.whatsapp_phone_number_id = "123456789"
            mock_settings.frontend_url = "http://localhost:3000"
            return WhatsAppNotifier()
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = Mock()
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        return db
    
    @pytest.fixture
    def mock_officer(self):
        """Create mock sales officer."""
        officer = Mock(spec=SalesOfficer)
        officer.id = uuid.uuid4()
        officer.name = "John Doe"
        officer.phone_number = "+919876543210"
        officer.whatsapp_opt_in = True
        return officer
    
    @pytest.fixture
    def mock_lead(self):
        """Create mock lead with all required relationships."""
        # Create mock company
        company = Mock(spec=Company)
        company.name = "ABC Industries Ltd"
        
        # Create mock event
        event = Mock(spec=Event)
        event.event_summary = "New manufacturing plant expansion"
        event.location = "Mumbai"
        
        # Create mock lead
        lead = Mock(spec=Lead)
        lead.id = uuid.uuid4()
        lead.company = company
        lead.event = event
        lead.priority = "high"
        
        # Create mock products
        product1 = Mock(spec=LeadProduct)
        product1.product_name = "Furnace Oil"
        product1.rank = 1
        
        product2 = Mock(spec=LeadProduct)
        product2.product_name = "HSD"
        product2.rank = 2
        
        lead.products = [product1, product2]
        
        return lead
    
    def test_check_opt_in_success(self, notifier, mock_officer):
        """Test opt-in check with valid officer."""
        assert notifier.check_opt_in(mock_officer) is True
    
    def test_check_opt_in_not_opted_in(self, notifier, mock_officer):
        """Test opt-in check when officer hasn't opted in."""
        mock_officer.whatsapp_opt_in = False
        assert notifier.check_opt_in(mock_officer) is False
    
    def test_check_opt_in_no_phone(self, notifier, mock_officer):
        """Test opt-in check when officer has no phone number."""
        mock_officer.phone_number = None
        assert notifier.check_opt_in(mock_officer) is False
    
    def test_check_opt_in_empty_phone(self, notifier, mock_officer):
        """Test opt-in check when officer has empty phone number."""
        mock_officer.phone_number = ""
        assert notifier.check_opt_in(mock_officer) is False
    
    def test_respect_service_window_no_previous_notification(self, notifier, mock_db, mock_officer):
        """Test service window when no previous notification exists."""
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        assert notifier.respect_service_window(mock_db, mock_officer) is True
    
    def test_respect_service_window_within_window(self, notifier, mock_db, mock_officer):
        """Test service window when last notification was recent."""
        # Create mock notification from 1 hour ago
        mock_notification = Mock(spec=WhatsAppNotification)
        mock_notification.sent_at = datetime.utcnow() - timedelta(hours=1)
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_notification
        
        assert notifier.respect_service_window(mock_db, mock_officer) is False
    
    def test_respect_service_window_outside_window(self, notifier, mock_db, mock_officer):
        """Test service window when last notification was long ago."""
        # Create mock notification from 25 hours ago
        mock_notification = Mock(spec=WhatsAppNotification)
        mock_notification.sent_at = datetime.utcnow() - timedelta(hours=25)
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_notification
        
        assert notifier.respect_service_window(mock_db, mock_officer) is True
    
    def test_prepare_message_structure(self, notifier, mock_lead, mock_officer):
        """Test message preparation creates correct structure."""
        message = notifier._prepare_message(mock_lead, mock_officer)
        
        assert message["messaging_product"] == "whatsapp"
        assert message["recipient_type"] == "individual"
        assert message["to"] == "+919876543210"
        assert message["type"] == "template"
        assert "template" in message
        assert message["template"]["name"] == "lead_alert"
        assert message["template"]["language"]["code"] == "en"
    
    def test_prepare_message_parameters(self, notifier, mock_lead, mock_officer):
        """Test message parameters contain lead details."""
        message = notifier._prepare_message(mock_lead, mock_officer)
        
        params = message["template"]["components"][0]["parameters"]
        
        # Check company name
        assert params[0]["text"] == "ABC Industries Ltd"
        
        # Check event summary
        assert params[1]["text"] == "New manufacturing plant expansion"
        
        # Check products
        assert "Furnace Oil" in params[2]["text"]
        assert "HSD" in params[2]["text"]
        
        # Check location
        assert params[3]["text"] == "Mumbai"
        
        # Check dossier link
        assert "localhost:3000/leads/" in params[4]["text"]
    
    def test_prepare_message_phone_formatting(self, notifier, mock_lead, mock_officer):
        """Test phone number formatting adds country code if missing."""
        mock_officer.phone_number = "9876543210"  # No country code
        message = notifier._prepare_message(mock_lead, mock_officer)
        
        assert message["to"] == "+9876543210"
    
    @patch('app.services.whatsapp_notifier.requests.post')
    def test_send_message_success(self, mock_post, notifier):
        """Test successful message sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_post.return_value = mock_response
        
        message_data = {"test": "data"}
        result = notifier._send_message(message_data)
        
        assert result is True
        mock_post.assert_called_once()
    
    @patch('app.services.whatsapp_notifier.requests.post')
    def test_send_message_api_error(self, mock_post, notifier):
        """Test message sending with API error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        message_data = {"test": "data"}
        result = notifier._send_message(message_data)
        
        assert result is False
    
    @patch('app.services.whatsapp_notifier.requests.post')
    def test_send_message_network_error(self, mock_post, notifier):
        """Test message sending with network error."""
        mock_post.side_effect = Exception("Network error")
        
        message_data = {"test": "data"}
        result = notifier._send_message(message_data)
        
        assert result is False
    
    def test_log_notification_success(self, notifier, mock_db, mock_lead, mock_officer):
        """Test notification logging."""
        notifier._log_notification(mock_db, mock_lead, mock_officer, "sent")
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_log_notification_error_handling(self, notifier, mock_db, mock_lead, mock_officer):
        """Test notification logging handles errors gracefully."""
        mock_db.commit.side_effect = Exception("Database error")
        
        # Should not raise exception
        notifier._log_notification(mock_db, mock_lead, mock_officer, "sent")
        
        mock_db.rollback.assert_called_once()
    
    @patch('app.services.whatsapp_notifier.requests.post')
    def test_send_lead_alert_full_flow(self, mock_post, notifier, mock_db, mock_lead, mock_officer):
        """Test complete lead alert flow."""
        # Setup successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.123"}]}
        mock_post.return_value = mock_response
        
        # Mock no previous notifications
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        
        result = notifier.send_lead_alert(mock_db, mock_lead, mock_officer)
        
        assert result is True
        mock_post.assert_called_once()
        mock_db.add.assert_called()
        mock_db.commit.assert_called()
    
    def test_send_lead_alert_not_configured(self, mock_db, mock_lead, mock_officer):
        """Test lead alert when WhatsApp is not configured."""
        with patch('app.services.whatsapp_notifier.settings') as mock_settings:
            mock_settings.whatsapp_access_token = None
            notifier = WhatsAppNotifier()
            
            result = notifier.send_lead_alert(mock_db, mock_lead, mock_officer)
            
            assert result is False
    
    def test_send_lead_alert_no_opt_in(self, notifier, mock_db, mock_lead, mock_officer):
        """Test lead alert when officer hasn't opted in."""
        mock_officer.whatsapp_opt_in = False
        
        result = notifier.send_lead_alert(mock_db, mock_lead, mock_officer)
        
        assert result is False
    
    def test_send_lead_alert_service_window_exceeded(self, notifier, mock_db, mock_lead, mock_officer):
        """Test lead alert when service window is exceeded."""
        # Mock recent notification
        mock_notification = Mock(spec=WhatsAppNotification)
        mock_notification.sent_at = datetime.utcnow() - timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_notification
        
        result = notifier.send_lead_alert(mock_db, mock_lead, mock_officer)
        
        assert result is False
    
    def test_is_configured_all_settings_present(self, notifier):
        """Test configuration check with all settings."""
        assert notifier._is_configured() is True
    
    def test_is_configured_missing_token(self):
        """Test configuration check with missing token."""
        with patch('app.services.whatsapp_notifier.settings') as mock_settings:
            mock_settings.whatsapp_access_token = None
            mock_settings.whatsapp_phone_number_id = "123"
            mock_settings.whatsapp_api_url = "https://api.example.com"
            notifier = WhatsAppNotifier()
            
            assert notifier._is_configured() is False
    
    def test_prepare_message_handles_missing_products(self, notifier, mock_lead, mock_officer):
        """Test message preparation when lead has no products."""
        mock_lead.products = []
        
        message = notifier._prepare_message(mock_lead, mock_officer)
        params = message["template"]["components"][0]["parameters"]
        
        assert params[2]["text"] == "Products TBD"
    
    def test_prepare_message_handles_missing_location(self, notifier, mock_lead, mock_officer):
        """Test message preparation when event has no location."""
        mock_lead.event.location = None
        
        message = notifier._prepare_message(mock_lead, mock_officer)
        params = message["template"]["components"][0]["parameters"]
        
        assert params[3]["text"] == "Location TBD"
