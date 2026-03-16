"""Unit tests for web scraping functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import requests

# Mock the database modules before importing
sys.modules['app.db.session'] = MagicMock()
sys.modules['app.models.signal'] = MagicMock()
sys.modules['app.models.source'] = MagicMock()

from app.services.ingestion import IngestionService


class TestWebScraping:
    """Test web scraping functionality."""
    
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
    def sample_html(self):
        """Sample HTML content for testing."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Article</title>
            <script>console.log('test');</script>
            <style>.test { color: red; }</style>
        </head>
        <body>
            <header>
                <nav>Navigation</nav>
            </header>
            <main>
                <article>
                    <h1>Company XYZ Announces Expansion</h1>
                    <p>Company XYZ announced today that they are expanding their manufacturing facility.</p>
                    <p>The expansion will include new production lines for industrial products.</p>
                </article>
            </main>
            <footer>Footer content</footer>
        </body>
        </html>
        """
    
    def test_scrape_web_page_success(self, ingestion_service, sample_html, mock_db):
        """Test successful web page scraping."""
        url = 'https://example.com/article'
        
        # Mock policy checker to allow access
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.content = sample_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        assert signal is not None
        assert 'Company XYZ' in signal.content
        assert 'expansion' in signal.content
        # Script and style content should be removed
        assert 'console.log' not in signal.content
        assert 'color: red' not in signal.content
        # Navigation and footer should be removed
        assert 'Navigation' not in signal.content
        assert 'Footer content' not in signal.content
    
    def test_scrape_web_page_extracts_title(self, ingestion_service, sample_html, mock_db):
        """Test that title is extracted from HTML."""
        url = 'https://example.com/article'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = sample_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        assert signal.title == 'Test Article'
    
    def test_scrape_web_page_respects_robots_txt(self, ingestion_service, mock_db):
        """Test that scraping respects robots.txt."""
        url = 'https://example.com/disallowed'
        
        # Mock policy checker to disallow access
        ingestion_service.policy_checker.can_access = Mock(
            return_value=(False, "robots.txt disallows access")
        )
        
        signal = ingestion_service.scrape_web_page(url)
        
        # Should return None when access is not allowed
        assert signal is None
    
    def test_scrape_web_page_respects_rate_limit(self, ingestion_service, sample_html, mock_db):
        """Test that scraping respects rate limits."""
        url = 'https://example.com/article'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=2.5)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = sample_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch('time.sleep') as mock_sleep:
            with patch.object(ingestion_service.session, 'get', return_value=mock_response):
                signal = ingestion_service.scrape_web_page(url)
            
            # Should have waited for rate limit
            mock_sleep.assert_called_once_with(2.5)
    
    def test_scrape_web_page_records_request(self, ingestion_service, sample_html, mock_db):
        """Test that scraping records the request for rate limiting."""
        url = 'https://example.com/article'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = sample_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        # Should have recorded the request
        ingestion_service.policy_checker.record_request.assert_called_once_with(url)
    
    def test_scrape_web_page_handles_http_error(self, ingestion_service, mock_db):
        """Test handling of HTTP errors during scraping."""
        url = 'https://example.com/notfound'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        # Should return None on error
        assert signal is None
    
    def test_scrape_web_page_extracts_article_content(self, ingestion_service, mock_db):
        """Test extraction of content from article tag."""
        html = """
        <html>
        <head><title>Article Title</title></head>
        <body>
            <div class="sidebar">Sidebar content</div>
            <article>
                <h1>Main Article</h1>
                <p>This is the main article content.</p>
            </article>
        </body>
        </html>
        """
        
        url = 'https://example.com/article'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        # Should extract article content
        assert 'Main Article' in signal.content
        assert 'main article content' in signal.content
        # Sidebar should not be included (article tag takes precedence)
        assert 'Sidebar content' not in signal.content
    
    def test_scrape_web_page_cleans_whitespace(self, ingestion_service, mock_db):
        """Test that excessive whitespace is cleaned up."""
        html = """
        <html>
        <body>
            <p>Text   with    multiple     spaces</p>
            <p>
                Text
                with
                newlines
            </p>
        </body>
        </html>
        """
        
        url = 'https://example.com/article'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        # Multiple spaces should be collapsed to single space
        assert 'multiple     spaces' not in signal.content
        assert 'multiple spaces' in signal.content
    
    def test_scrape_multiple_pages(self, ingestion_service, sample_html, mock_db):
        """Test scraping multiple pages."""
        urls = [
            'https://example.com/page1',
            'https://example.com/page2',
            'https://example.com/page3'
        ]
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = sample_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signals = ingestion_service.scrape_multiple_pages(urls)
        
        assert len(signals) == 3
    
    def test_scrape_multiple_pages_continues_on_error(self, ingestion_service, sample_html, mock_db):
        """Test that scraping multiple pages continues when one fails."""
        urls = [
            'https://example.com/page1',
            'https://example.com/page2',  # This will fail
            'https://example.com/page3'
        ]
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        # First and third succeed, second fails
        responses = [
            Mock(content=sample_html.encode('utf-8'), raise_for_status=Mock()),
            Mock(raise_for_status=Mock(side_effect=requests.HTTPError("500 Error"))),
            Mock(content=sample_html.encode('utf-8'), raise_for_status=Mock())
        ]
        
        with patch.object(ingestion_service.session, 'get', side_effect=responses):
            signals = ingestion_service.scrape_multiple_pages(urls)
        
        # Should get 2 signals (first and third)
        assert len(signals) == 2
    
    def test_scrape_web_page_handles_no_title(self, ingestion_service, mock_db):
        """Test scraping page without title tag."""
        html = """
        <html>
        <body>
            <p>Content without title</p>
        </body>
        </html>
        """
        
        url = 'https://example.com/notitle'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        # Should have a default title
        assert signal.title is not None
        assert 'example.com' in signal.title
    
    def test_scrape_web_page_provenance_metadata(self, ingestion_service, sample_html, mock_db):
        """Test that provenance metadata is recorded."""
        url = 'https://example.com/article'
        
        ingestion_service.policy_checker.can_access = Mock(return_value=(True, "Access allowed"))
        ingestion_service.policy_checker.wait_for_rate_limit = Mock(return_value=0)
        ingestion_service.policy_checker.record_request = Mock()
        
        mock_response = Mock()
        mock_response.content = sample_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        
        with patch.object(ingestion_service.session, 'get', return_value=mock_response):
            signal = ingestion_service.scrape_web_page(url)
        
        # Check provenance metadata
        assert signal.provenance is not None
        assert signal.provenance['method'] == 'scrape'
        assert signal.provenance['success'] is True
        assert 'content_length' in signal.provenance
        assert signal.provenance['parser'] == 'beautifulsoup4'
