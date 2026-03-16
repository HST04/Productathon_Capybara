"""Signal Ingestion Service for collecting data from public sources."""

import feedparser
import requests
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout

from app.models.signal import Signal
from app.models.source import Source
from app.services.policy_checker import PolicyChecker

logger = logging.getLogger(__name__)


class APIConfig:
    """Configuration for API-based content fetching."""
    
    def __init__(
        self,
        base_url: str,
        endpoint: str = '',
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None,
        auth_token: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        pagination_param: Optional[str] = None,
        max_pages: int = 10,
        timeout: int = 30
    ):
        """
        Initialize API configuration.
        
        Args:
            base_url: Base URL of the API
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            headers: Custom headers
            auth: Basic auth tuple (username, password)
            auth_token: Bearer token for authentication
            params: Query parameters
            pagination_param: Parameter name for pagination (e.g., 'page', 'offset')
            max_pages: Maximum number of pages to fetch
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint.lstrip('/')
        self.method = method.upper()
        self.headers = headers or {}
        self.auth = auth
        self.auth_token = auth_token
        self.params = params or {}
        self.pagination_param = pagination_param
        self.max_pages = max_pages
        self.timeout = timeout
        
        # Add bearer token to headers if provided
        if self.auth_token:
            self.headers['Authorization'] = f'Bearer {self.auth_token}'
    
    @property
    def url(self) -> str:
        """Get full URL."""
        if self.endpoint:
            return f"{self.base_url}/{self.endpoint}"
        return self.base_url


class IngestionService:
    """
    Service for ingesting signals from various public sources.
    Handles RSS feeds, API-based content, and compliant web scraping.
    """
    
    def __init__(self, db: Session, policy_checker: Optional[PolicyChecker] = None):
        """
        Initialize the ingestion service.
        
        Args:
            db: Database session
            policy_checker: Policy checker instance (creates new if None)
        """
        self.db = db
        self.policy_checker = policy_checker or PolicyChecker()
        
        # Configure HTTP session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=['GET', 'POST', 'HEAD']
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def fetch_rss_feeds(self, feed_urls: List[str]) -> List[Signal]:
        """
        Fetch and parse RSS/Atom feeds from multiple URLs.
        
        Args:
            feed_urls: List of RSS/Atom feed URLs
        
        Returns:
            List of Signal objects created from feed entries
        """
        signals = []
        
        for feed_url in feed_urls:
            try:
                feed_signals = self._parse_single_feed(feed_url)
                signals.extend(feed_signals)
                logger.info(f"Successfully fetched {len(feed_signals)} signals from {feed_url}")
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_url}: {e}", exc_info=True)
                # Continue processing other feeds even if one fails
                continue
        
        return signals
    
    def _parse_single_feed(self, feed_url: str) -> List[Signal]:
        """
        Parse a single RSS/Atom feed and extract signals.
        
        Args:
            feed_url: URL of the RSS/Atom feed
        
        Returns:
            List of Signal objects from feed entries
        """
        signals = []
        
        try:
            # Parse the feed using feedparser
            feed = feedparser.parse(feed_url)
            
            # Check for parsing errors
            if feed.bozo:
                logger.warning(
                    f"Feed parsing warning for {feed_url}: {feed.bozo_exception}"
                )
                # Continue anyway - feedparser is forgiving and may still extract data
            
            # Get or create source for this feed
            source = self._get_or_create_source(feed_url, 'rss')
            
            # Process each entry in the feed
            for entry in feed.entries:
                try:
                    signal = self._create_signal_from_entry(entry, source, feed_url)
                    if signal:
                        signals.append(signal)
                except Exception as e:
                    logger.error(
                        f"Error processing feed entry from {feed_url}: {e}",
                        exc_info=True
                    )
                    # Continue processing other entries
                    continue
            
            logger.info(f"Parsed {len(signals)} entries from feed {feed_url}")
            
        except Exception as e:
            logger.error(f"Failed to parse feed {feed_url}: {e}", exc_info=True)
            raise
        
        return signals
    
    def _create_signal_from_entry(
        self,
        entry: feedparser.FeedParserDict,
        source: Source,
        feed_url: str
    ) -> Optional[Signal]:
        """
        Create a Signal object from a feed entry.
        
        Args:
            entry: Feed entry from feedparser
            source: Source object for this feed
            feed_url: Original feed URL
        
        Returns:
            Signal object or None if entry is invalid
        """
        # Extract URL (required field)
        url = entry.get('link')
        if not url:
            logger.warning(f"Feed entry missing URL, skipping: {entry.get('title', 'Unknown')}")
            return None
        
        # Extract title
        title = entry.get('title', '')
        
        # Extract content (try multiple fields)
        content = self._extract_content(entry)
        if not content:
            logger.warning(f"Feed entry missing content, skipping: {url}")
            return None
        
        # Extract timestamp
        published_date = self._extract_timestamp(entry)
        
        # Create provenance metadata
        provenance = self.policy_checker.log_provenance(
            url=url,
            method='rss',
            success=True,
            rate_limit_respected=True
        )
        provenance['feed_url'] = feed_url
        provenance['entry_id'] = entry.get('id', url)
        
        # Create Signal object
        signal = Signal(
            source_id=source.id,
            url=url,
            title=title,
            content=content,
            ingested_at=datetime.utcnow(),
            processed=False,
            provenance=provenance
        )
        
        return signal
    
    def _extract_content(self, entry: feedparser.FeedParserDict) -> str:
        """
        Extract content from feed entry, trying multiple fields.
        
        Args:
            entry: Feed entry from feedparser
        
        Returns:
            Content string or empty string if not found
        """
        # Try content field (Atom feeds)
        content = entry.get('content')
        if content and len(content) > 0:
            return content[0].get('value', '')
        
        # Try summary field (RSS feeds)
        summary = entry.get('summary')
        if summary:
            return summary
        
        # Try description field
        description = entry.get('description')
        if description:
            return description
        
        # Fall back to title if nothing else available
        title = entry.get('title')
        if title:
            return title
        
        # No content found
        return ''
    
    def _extract_timestamp(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """
        Extract publication timestamp from feed entry.
        
        Args:
            entry: Feed entry from feedparser
        
        Returns:
            datetime object or None if not found
        """
        # Try published_parsed (most common)
        published_parsed = entry.get('published_parsed')
        if published_parsed:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(published_parsed))
            except Exception as e:
                logger.warning(f"Error parsing published_parsed: {e}")
        
        # Try updated_parsed
        updated_parsed = entry.get('updated_parsed')
        if updated_parsed:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(updated_parsed))
            except Exception as e:
                logger.warning(f"Error parsing updated_parsed: {e}")
        
        # No timestamp found
        return None
    
    def _get_or_create_source(self, feed_url: str, access_method: str) -> Source:
        """
        Get existing source or create new one for a feed URL.
        
        Args:
            feed_url: URL of the feed
            access_method: Access method ('rss', 'api', 'scrape')
        
        Returns:
            Source object
        """
        # Extract domain from feed URL
        parsed = urlparse(feed_url)
        domain = parsed.netloc
        
        # Try to find existing source
        source = self.db.query(Source).filter(Source.domain == domain).first()
        
        if source:
            return source
        
        # Create new source with neutral trust tier
        source = Source(
            domain=domain,
            category='news',  # Default category, can be updated later
            access_method=access_method,
            crawl_frequency_minutes=60,  # Default 1 hour
            trust_score=50.0,  # Neutral starting score
            trust_tier='neutral',
            robots_txt_allowed=True  # RSS feeds don't need robots.txt check
        )
        
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        
        logger.info(f"Created new source for domain {domain}")
        
        return source

    
    def fetch_from_api(self, api_config: APIConfig) -> List[Signal]:
        """
        Fetch content from an API endpoint.
        
        Args:
            api_config: API configuration object
        
        Returns:
            List of Signal objects created from API response
        """
        signals = []
        
        try:
            # Fetch data from API with pagination support
            if api_config.pagination_param:
                signals = self._fetch_paginated_api(api_config)
            else:
                signals = self._fetch_single_api_request(api_config)
            
            logger.info(f"Successfully fetched {len(signals)} signals from API {api_config.url}")
            
        except Exception as e:
            logger.error(f"Error fetching from API {api_config.url}: {e}", exc_info=True)
            raise
        
        return signals
    
    def _fetch_single_api_request(self, api_config: APIConfig) -> List[Signal]:
        """
        Fetch data from a single API request.
        
        Args:
            api_config: API configuration object
        
        Returns:
            List of Signal objects
        """
        try:
            # Make API request
            response = self._make_api_request(api_config)
            
            # Parse response and create signals
            signals = self._parse_api_response(response, api_config)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error in single API request to {api_config.url}: {e}", exc_info=True)
            raise
    
    def _fetch_paginated_api(self, api_config: APIConfig) -> List[Signal]:
        """
        Fetch data from a paginated API.
        
        Args:
            api_config: API configuration object with pagination settings
        
        Returns:
            List of Signal objects from all pages
        """
        all_signals = []
        page = 1
        
        while page <= api_config.max_pages:
            try:
                # Update pagination parameter
                config_with_page = self._update_pagination_param(api_config, page)
                
                # Make request
                response = self._make_api_request(config_with_page)
                
                # Parse response
                signals = self._parse_api_response(response, config_with_page)
                
                if not signals:
                    # No more data, stop pagination
                    logger.info(f"No more data at page {page}, stopping pagination")
                    break
                
                all_signals.extend(signals)
                logger.info(f"Fetched {len(signals)} signals from page {page}")
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error fetching page {page} from {api_config.url}: {e}")
                # Continue to next page or stop based on error type
                if isinstance(e, (ConnectionError, Timeout)):
                    # Network errors - stop pagination
                    break
                # Other errors - try next page
                page += 1
                continue
        
        return all_signals
    
    def _make_api_request(self, api_config: APIConfig) -> requests.Response:
        """
        Make an HTTP request to the API.
        
        Args:
            api_config: API configuration object
        
        Returns:
            Response object
        
        Raises:
            RequestException: If request fails
        """
        try:
            # Prepare request parameters
            request_kwargs = {
                'headers': api_config.headers,
                'params': api_config.params,
                'timeout': api_config.timeout
            }
            
            # Add authentication if provided
            if api_config.auth:
                request_kwargs['auth'] = api_config.auth
            
            # Make request
            response = self.session.request(
                method=api_config.method,
                url=api_config.url,
                **request_kwargs
            )
            
            # Raise exception for 4xx/5xx status codes
            response.raise_for_status()
            
            logger.debug(f"API request successful: {api_config.method} {api_config.url}")
            
            return response
            
        except HTTPError as e:
            logger.error(f"HTTP error for {api_config.url}: {e}")
            raise
        except ConnectionError as e:
            logger.error(f"Connection error for {api_config.url}: {e}")
            raise
        except Timeout as e:
            logger.error(f"Timeout for {api_config.url}: {e}")
            raise
        except RequestException as e:
            logger.error(f"Request failed for {api_config.url}: {e}")
            raise
    
    def _parse_api_response(
        self,
        response: requests.Response,
        api_config: APIConfig
    ) -> List[Signal]:
        """
        Parse API response and create Signal objects.
        
        Args:
            response: HTTP response object
            api_config: API configuration object
        
        Returns:
            List of Signal objects
        """
        signals = []
        
        try:
            # Try to parse as JSON
            data = response.json()
            
            # Get or create source
            source = self._get_or_create_source(api_config.base_url, 'api')
            
            # Handle different response structures
            if isinstance(data, list):
                # Response is a list of items
                for item in data:
                    signal = self._create_signal_from_api_item(item, source, api_config)
                    if signal:
                        signals.append(signal)
            
            elif isinstance(data, dict):
                # Response is a dict - check for common pagination patterns
                items = None
                
                # Try common data field names
                for key in ['data', 'items', 'results', 'entries', 'records']:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                
                if items:
                    # Found items in nested structure
                    for item in items:
                        signal = self._create_signal_from_api_item(item, source, api_config)
                        if signal:
                            signals.append(signal)
                else:
                    # Single item response
                    signal = self._create_signal_from_api_item(data, source, api_config)
                    if signal:
                        signals.append(signal)
            
            logger.info(f"Parsed {len(signals)} signals from API response")
            
        except ValueError as e:
            # Not JSON - try to use raw text
            logger.warning(f"Response is not JSON, using raw text: {e}")
            source = self._get_or_create_source(api_config.base_url, 'api')
            
            signal = Signal(
                source_id=source.id,
                url=api_config.url,
                title=f"API Response from {api_config.base_url}",
                content=response.text,
                ingested_at=datetime.utcnow(),
                processed=False,
                provenance=self.policy_checker.log_provenance(
                    url=api_config.url,
                    method='api',
                    success=True
                )
            )
            signals.append(signal)
        
        return signals
    
    def _create_signal_from_api_item(
        self,
        item: Dict[str, Any],
        source: Source,
        api_config: APIConfig
    ) -> Optional[Signal]:
        """
        Create a Signal from an API response item.
        
        Args:
            item: API response item (dict)
            source: Source object
            api_config: API configuration
        
        Returns:
            Signal object or None if item is invalid
        """
        # Extract URL - try common field names
        url = None
        for key in ['url', 'link', 'href', 'uri', 'id']:
            if key in item:
                url = str(item[key])
                break
        
        if not url:
            # Use API URL as fallback
            url = api_config.url
        
        # Extract title - try common field names
        title = None
        for key in ['title', 'name', 'headline', 'subject']:
            if key in item:
                title = str(item[key])
                break
        
        # Extract content - try common field names
        content = None
        for key in ['content', 'body', 'text', 'description', 'summary', 'message']:
            if key in item:
                content = str(item[key])
                break
        
        if not content:
            # Use entire item as JSON string if no content field found
            import json
            content = json.dumps(item)
        
        # Create provenance metadata
        provenance = self.policy_checker.log_provenance(
            url=url,
            method='api',
            success=True
        )
        provenance['api_endpoint'] = api_config.url
        provenance['api_method'] = api_config.method
        
        # Create Signal
        signal = Signal(
            source_id=source.id,
            url=url,
            title=title or f"API Item from {api_config.base_url}",
            content=content,
            ingested_at=datetime.utcnow(),
            processed=False,
            provenance=provenance
        )
        
        return signal
    
    def _update_pagination_param(self, api_config: APIConfig, page: int) -> APIConfig:
        """
        Create a new APIConfig with updated pagination parameter.
        
        Args:
            api_config: Original API configuration
            page: Page number
        
        Returns:
            New APIConfig with updated pagination
        """
        # Create a copy of params
        new_params = api_config.params.copy()
        
        # Update pagination parameter
        if api_config.pagination_param:
            new_params[api_config.pagination_param] = page
        
        # Create new config with updated params
        new_config = APIConfig(
            base_url=api_config.base_url,
            endpoint=api_config.endpoint,
            method=api_config.method,
            headers=api_config.headers,
            auth=api_config.auth,
            auth_token=api_config.auth_token,
            params=new_params,
            pagination_param=api_config.pagination_param,
            max_pages=api_config.max_pages,
            timeout=api_config.timeout
        )
        
        return new_config

    
    def scrape_web_page(self, url: str) -> Optional[Signal]:
        """
        Scrape content from a web page in a compliant manner.
        
        Args:
            url: URL to scrape
        
        Returns:
            Signal object or None if scraping fails or is not allowed
        """
        try:
            # Check policy compliance before scraping
            allowed, reason = self.policy_checker.can_access(url, method='scrape')
            
            if not allowed:
                logger.warning(f"Scraping not allowed for {url}: {reason}")
                return None
            
            # Wait for rate limit if needed
            wait_time = self.policy_checker.wait_for_rate_limit(url)
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.2f}s for rate limit before scraping {url}")
                import time
                time.sleep(wait_time)
            
            # Make request
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Record request for rate limiting
            self.policy_checker.record_request(url)
            
            # Parse HTML and extract content
            signal = self._parse_html_content(response, url)
            
            logger.info(f"Successfully scraped content from {url}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}", exc_info=True)
            
            # Log failed attempt
            provenance = self.policy_checker.log_provenance(
                url=url,
                method='scrape',
                success=False
            )
            
            return None
    
    def _parse_html_content(self, response: requests.Response, url: str) -> Signal:
        """
        Parse HTML content and extract text.
        
        Args:
            response: HTTP response object
            url: URL of the page
        
        Returns:
            Signal object with extracted content
        """
        from bs4 import BeautifulSoup
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Try to find main content area
        # Look for common content containers
        content_area = None
        for selector in ['article', 'main', '[role="main"]', '.content', '#content', '.post', '.entry']:
            if selector.startswith('['):
                # Attribute selector
                content_area = soup.find(attrs={'role': 'main'})
            elif selector.startswith('.'):
                # Class selector
                content_area = soup.find(class_=selector[1:])
            elif selector.startswith('#'):
                # ID selector
                content_area = soup.find(id=selector[1:])
            else:
                # Tag selector
                content_area = soup.find(selector)
            
            if content_area:
                break
        
        # If no content area found, use body
        if not content_area:
            content_area = soup.find('body')
        
        if not content_area:
            content_area = soup
        
        # Remove script and style tags
        for tag in content_area.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.extract()
        
        # Extract text content
        content = content_area.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        import re
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Get or create source
        source = self._get_or_create_source(url, 'scrape')
        
        # Create provenance metadata
        provenance = self.policy_checker.log_provenance(
            url=url,
            method='scrape',
            success=True
        )
        provenance['content_length'] = len(content)
        provenance['parser'] = 'beautifulsoup4'
        
        # Create Signal
        signal = Signal(
            source_id=source.id,
            url=url,
            title=title or f"Scraped content from {urlparse(url).netloc}",
            content=content,
            ingested_at=datetime.utcnow(),
            processed=False,
            provenance=provenance
        )
        
        return signal
    
    def scrape_multiple_pages(self, urls: List[str]) -> List[Signal]:
        """
        Scrape multiple web pages.
        
        Args:
            urls: List of URLs to scrape
        
        Returns:
            List of Signal objects
        """
        signals = []
        
        for url in urls:
            try:
                signal = self.scrape_web_page(url)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")
                # Continue with other URLs
                continue
        
        logger.info(f"Successfully scraped {len(signals)} out of {len(urls)} pages")
        
        return signals
