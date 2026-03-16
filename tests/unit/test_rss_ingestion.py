"""Unit tests for RSS feed ingestion."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
from pathlib import Path

# Mock the database modules before importing
sys.modules['app.db.session'] = MagicMock()
sys.modules['app.models.signal'] = MagicMock()
sys.modules['app.models.source'] = MagicMock()

import feedparser
from app.services.ingestion import IngestionService


class TestRSSIngestion:
    """Test RSS feed parsing and signal creation."""
    
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
    
    def test_parse_valid_rss_feed(self, ingestion_service, mock_db):
        """Test parsing a valid RSS feed with entries."""
        # Mock feedparser response
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                'link': 'https://example.com/article1',
                'title': 'Company XYZ Expands Operations',
                'summary': 'Company XYZ announced expansion of manufacturing facility',
                'published_parsed': None
            },
            {
                'link': 'https://example.com/article2',
                'title': 'New Tender for Road Construction',
                'description': 'Government announces tender for highway project',
                'published_parsed': None
            }
        ]
        
        with patch('feedparser.parse', return_value=mock_feed):
            signals = ingestion_service.fetch_rss_feeds(['https://example.com/feed.xml'])
        
        assert len(signals) == 2
        assert signals[0].url == 'https://example.com/article1'
        assert signals[0].title == 'Company XYZ Expands Operations'
        assert signals[1].url == 'https://example.com/article2'
        assert signals[1].title == 'New Tender for Road Construction'
    
    def test_handle_malformed_feed(self, ingestion_service, mock_db):
        """Test handling of malformed RSS feed."""
        # Mock feedparser response with bozo flag
        mock_feed = MagicMock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Feed parsing error")
        mock_feed.entries = [
            {
                'link': 'https://example.com/article1',
                'title': 'Valid Entry',
                'summary': 'This entry is still valid',
                'published_parsed': None
            }
        ]
        
        with patch('feedparser.parse', return_value=mock_feed):
            signals = ingestion_service.fetch_rss_feeds(['https://example.com/feed.xml'])
        
        # Should still extract valid entries despite bozo flag
        assert len(signals) == 1
        assert signals[0].url == 'https://example.com/article1'
    
    def test_skip_entry_without_url(self, ingestion_service, mock_db):
        """Test that entries without URLs are skipped."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                'title': 'Entry Without URL',
                'summary': 'This entry has no link field'
            },
            {
                'link': 'https://example.com/valid',
                'title': 'Valid Entry',
                'summary': 'This entry has a URL'
            }
        ]
        
        with patch('feedparser.parse', return_value=mock_feed):
            signals = ingestion_service.fetch_rss_feeds(['https://example.com/feed.xml'])
        
        # Should only get the valid entry
        assert len(signals) == 1
        assert signals[0].url == 'https://example.com/valid'
    
    def test_skip_entry_without_content(self, ingestion_service, mock_db):
        """Test that entries without content are skipped."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                'link': 'https://example.com/no-content',
                'title': 'Entry Without Content'
                # No summary, description, or content field
            },
            {
                'link': 'https://example.com/valid',
                'title': 'Valid Entry',
                'summary': 'This entry has content'
            }
        ]
        
        with patch('feedparser.parse', return_value=mock_feed):
            signals = ingestion_service.fetch_rss_feeds(['https://example.com/feed.xml'])
        
        # Should only get the entry with content
        assert len(signals) == 1
        assert signals[0].url == 'https://example.com/valid'
    
    def test_extract_content_from_multiple_fields(self, ingestion_service, mock_db):
        """Test content extraction from different feed formats."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                'link': 'https://example.com/atom',
                'title': 'Atom Feed Entry',
                'content': [{'value': 'Content from Atom feed'}]
            },
            {
                'link': 'https://example.com/rss',
                'title': 'RSS Feed Entry',
                'summary': 'Content from RSS summary'
            },
            {
                'link': 'https://example.com/desc',
                'title': 'Description Entry',
                'description': 'Content from description field'
            }
        ]
        
        with patch('feedparser.parse', return_value=mock_feed):
            signals = ingestion_service.fetch_rss_feeds(['https://example.com/feed.xml'])
        
        assert len(signals) == 3
        assert signals[0].content == 'Content from Atom feed'
        assert signals[1].content == 'Content from RSS summary'
        assert signals[2].content == 'Content from description field'
    
    def test_continue_on_feed_error(self, ingestion_service, mock_db):
        """Test that processing continues when one feed fails."""
        mock_feed_success = MagicMock()
        mock_feed_success.bozo = False
        mock_feed_success.entries = [
            {
                'link': 'https://example.com/article',
                'title': 'Valid Article',
                'summary': 'Content'
            }
        ]
        
        def mock_parse(url):
            if 'fail' in url:
                raise Exception("Network error")
            return mock_feed_success
        
        with patch('feedparser.parse', side_effect=mock_parse):
            signals = ingestion_service.fetch_rss_feeds([
                'https://example.com/fail.xml',
                'https://example.com/success.xml'
            ])
        
        # Should get signal from successful feed
        assert len(signals) == 1
        assert signals[0].url == 'https://example.com/article'
    
    def test_provenance_metadata(self, ingestion_service, mock_db):
        """Test that provenance metadata is correctly recorded."""
        mock_feed = MagicMock()
        mock_feed.bozo = False
        mock_feed.entries = [
            {
                'link': 'https://example.com/article',
                'title': 'Test Article',
                'summary': 'Test content',
                'id': 'unique-entry-id'
            }
        ]
        
        with patch('feedparser.parse', return_value=mock_feed):
            signals = ingestion_service.fetch_rss_feeds(['https://example.com/feed.xml'])
        
        assert len(signals) == 1
        signal = signals[0]
        
        # Check provenance metadata
        assert signal.provenance is not None
        assert signal.provenance['method'] == 'rss'
        assert signal.provenance['url'] == 'https://example.com/article'
        assert signal.provenance['success'] is True
        assert signal.provenance['feed_url'] == 'https://example.com/feed.xml'
        assert signal.provenance['entry_id'] == 'unique-entry-id'
