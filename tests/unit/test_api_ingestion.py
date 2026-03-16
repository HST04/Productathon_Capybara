"""Unit tests for API-based content ingestion."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import requests

# Mock the database modules before importing
sys.modules['app.db.session'] = MagicMock()
sys.modules['app.models.signal'] = MagicMock()
sys.modules['app.models.source'] = MagicMock()

from app.services.ingestion import IngestionService, APIConfig


class TestAPIIngestion:
    """Test API-based content fetching."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db
    
    @pytest.fixture
    def ingestion_service(self, mock_db):
        """Create an ingestion service with mocked dependencies."""
        return IngestionService(db=mock_db)
    
    @pytest.fixture
    def basic_api_config(self):
        """Create a basic API configuration."""
        return APIConfig(
            base_url='https://api.example.com',
            endpoint='data',
            method='GET'
        )
    
    def test_api_config_initialization(self):
        """Test APIConfig initialization."""
        config = APIConfig(
            base_url='https://api.example.com/',
            endpoint='/data',
            method='get',
            headers={'Custom-Header': 'value'},
            auth=('user', 'pass'),
            params={'limit': 10}
        )
        
        assert config.base_url == 'https://api.example.com'
        assert config.endpoint == 'data'
        assert config.method == 'GET'
        assert config.url == 'https://api.example.com/data'
        assert config.headers['Custom-Header'] == 'value'
        assert config.auth == ('user', 'pass')
        assert config.params['limit'] == 10
    
    def test_api_config_with_bearer_token(self):
        """Test APIConfig with bearer token authentication."""
        config = APIConfig(
            base_url='https://api.example.com',
            auth_token='my-secret-token'
        )
        
        assert 'Authorization' in config.headers
        assert config.headers['Authorization'] == 'Bearer my-secret-token'
    
    def test_fetch_from_api_list_response(self, ingestion_service, basic_api_config, mock_db):
        """Test fetching from API with list response."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                'id': '1',
                'title': 'Article 1',
                'content': 'Content of article 1',
                'url': 'https://example.com/article1'
            },
            {
                'id': '2',
                'title': 'Article 2',
                'content': 'Content of article 2',
                'url': 'https://example.com/article2'
            }
        ]
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', return_value=mock_response):
            signals = ingestion_service.fetch_from_api(basic_api_config)
        
        assert len(signals) == 2
    
    def test_fetch_from_api_dict_response_with_data_field(self, ingestion_service, basic_api_config, mock_db):
        """Test fetching from API with nested data field."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {
                    'title': 'Article 1',
                    'body': 'Content 1',
                    'link': 'https://example.com/1'
                }
            ],
            'meta': {'total': 1}
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', return_value=mock_response):
            signals = ingestion_service.fetch_from_api(basic_api_config)
        
        assert len(signals) == 1
    
    def test_fetch_from_api_single_item_response(self, ingestion_service, basic_api_config, mock_db):
        """Test fetching from API with single item response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'title': 'Single Article',
            'content': 'Article content',
            'url': 'https://example.com/article'
        }
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', return_value=mock_response):
            signals = ingestion_service.fetch_from_api(basic_api_config)
        
        assert len(signals) == 1
    
    def test_fetch_from_api_with_authentication(self, ingestion_service, mock_db):
        """Test API request with authentication."""
        config = APIConfig(
            base_url='https://api.example.com',
            endpoint='protected',
            auth=('user', 'password')
        )
        
        mock_response = Mock()
        mock_response.json.return_value = [{'id': '1', 'content': 'Protected data'}]
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', return_value=mock_response) as mock_request:
            signals = ingestion_service.fetch_from_api(config)
            
            # Verify auth was passed
            assert mock_request.call_args[1]['auth'] == ('user', 'password')
    
    def test_fetch_from_api_with_custom_headers(self, ingestion_service, mock_db):
        """Test API request with custom headers."""
        config = APIConfig(
            base_url='https://api.example.com',
            headers={'X-API-Key': 'secret-key'}
        )
        
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', return_value=mock_response) as mock_request:
            ingestion_service.fetch_from_api(config)
            
            # Verify headers were passed
            assert mock_request.call_args[1]['headers']['X-API-Key'] == 'secret-key'
    
    def test_fetch_paginated_api(self, ingestion_service, mock_db):
        """Test fetching from paginated API."""
        config = APIConfig(
            base_url='https://api.example.com',
            endpoint='items',
            pagination_param='page',
            max_pages=3
        )
        
        # Mock responses for 3 pages
        responses = [
            Mock(json=lambda: [{'id': '1', 'content': 'Page 1 item'}]),
            Mock(json=lambda: [{'id': '2', 'content': 'Page 2 item'}]),
            Mock(json=lambda: [])  # Empty page to stop pagination
        ]
        
        for r in responses:
            r.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', side_effect=responses):
            signals = ingestion_service.fetch_from_api(config)
        
        # Should get 2 signals (page 3 is empty)
        assert len(signals) == 2
    
    def test_api_request_retry_on_server_error(self, ingestion_service, basic_api_config, mock_db):
        """Test that API requests have retry configuration."""
        # Verify that the session has retry adapter configured
        adapter = ingestion_service.session.get_adapter('https://')
        
        # Check that max_retries is configured
        assert adapter.max_retries is not None
        assert adapter.max_retries.total == 3
        assert 500 in adapter.max_retries.status_forcelist
    
    def test_api_request_handles_connection_error(self, ingestion_service, basic_api_config, mock_db):
        """Test handling of connection errors."""
        with patch.object(
            ingestion_service.session,
            'request',
            side_effect=requests.ConnectionError("Connection failed")
        ):
            with pytest.raises(requests.ConnectionError):
                ingestion_service.fetch_from_api(basic_api_config)
    
    def test_api_request_handles_timeout(self, ingestion_service, basic_api_config, mock_db):
        """Test handling of request timeout."""
        with patch.object(
            ingestion_service.session,
            'request',
            side_effect=requests.Timeout("Request timed out")
        ):
            with pytest.raises(requests.Timeout):
                ingestion_service.fetch_from_api(basic_api_config)
    
    def test_parse_non_json_response(self, ingestion_service, basic_api_config, mock_db):
        """Test parsing non-JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "Plain text response"
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', return_value=mock_response):
            signals = ingestion_service.fetch_from_api(basic_api_config)
        
        # Should create signal with raw text
        assert len(signals) == 1
    
    def test_extract_content_from_various_fields(self, ingestion_service, basic_api_config, mock_db):
        """Test content extraction from different field names."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {'title': 'Item 1', 'body': 'Body content'},
            {'name': 'Item 2', 'text': 'Text content'},
            {'headline': 'Item 3', 'description': 'Description content'}
        ]
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', return_value=mock_response):
            signals = ingestion_service.fetch_from_api(basic_api_config)
        
        assert len(signals) == 3
    
    def test_pagination_stops_on_empty_response(self, ingestion_service, mock_db):
        """Test that pagination stops when receiving empty response."""
        config = APIConfig(
            base_url='https://api.example.com',
            pagination_param='page',
            max_pages=10  # Set high limit
        )
        
        # Return data for 2 pages, then empty
        responses = [
            Mock(json=lambda: [{'id': '1'}]),
            Mock(json=lambda: [{'id': '2'}]),
            Mock(json=lambda: [])  # Empty - should stop here
        ]
        
        for r in responses:
            r.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'request', side_effect=responses) as mock_request:
            signals = ingestion_service.fetch_from_api(config)
            
            # Should only make 3 requests (not 10)
            assert mock_request.call_count == 3
            assert len(signals) == 2
