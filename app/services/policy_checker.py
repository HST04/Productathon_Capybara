"""Policy Checker for compliant web access."""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import time
import logging

logger = logging.getLogger(__name__)


class PolicyChecker:
    """
    Ensures compliant web access by checking robots.txt and enforcing rate limits.
    Implements access method prioritization (API > RSS > scrape).
    """
    
    def __init__(self):
        # Cache for robots.txt parsers (domain -> (parser, timestamp))
        self._robots_cache: Dict[str, Tuple[RobotFileParser, datetime]] = {}
        self._robots_cache_ttl = timedelta(hours=24)  # Cache for 24 hours
        
        # Rate limiter: domain -> list of request timestamps
        self._rate_limits: Dict[str, list] = {}
        
        # Default rate limit: 1 request per second per domain
        self._default_rate_limit_seconds = 1.0
        
        # Custom rate limits per domain (domain -> seconds between requests)
        self._custom_rate_limits: Dict[str, float] = {}
        
        # User agent for robots.txt checks
        self._user_agent = "HPCLLeadBot/1.0"
    
    def set_custom_rate_limit(self, domain: str, seconds_between_requests: float) -> None:
        """
        Set a custom rate limit for a specific domain.
        
        Args:
            domain: Domain name (e.g., 'example.com')
            seconds_between_requests: Minimum seconds between requests
        """
        self._custom_rate_limits[domain] = seconds_between_requests
        logger.info(f"Set custom rate limit for {domain}: {seconds_between_requests}s")
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc
    
    def _get_robots_txt_url(self, url: str) -> str:
        """Get robots.txt URL for a given URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    def _fetch_robots_txt(self, domain: str, url: str) -> RobotFileParser:
        """
        Fetch and parse robots.txt for a domain.
        
        Args:
            domain: Domain name
            url: Base URL to construct robots.txt URL
        
        Returns:
            RobotFileParser instance
        """
        robots_url = self._get_robots_txt_url(url)
        parser = RobotFileParser()
        parser.set_url(robots_url)
        
        try:
            parser.read()
            logger.info(f"Fetched robots.txt for {domain}")
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}. Assuming allowed.")
            # If we can't fetch robots.txt, assume access is allowed
            # This is a conservative approach to avoid blocking legitimate access
        
        return parser
    
    def _get_robots_parser(self, url: str) -> RobotFileParser:
        """
        Get robots.txt parser for a URL, using cache if available.
        
        Args:
            url: URL to check
        
        Returns:
            RobotFileParser instance
        """
        domain = self._get_domain(url)
        now = datetime.utcnow()
        
        # Check cache
        if domain in self._robots_cache:
            parser, timestamp = self._robots_cache[domain]
            if now - timestamp < self._robots_cache_ttl:
                return parser
        
        # Fetch new robots.txt
        parser = self._fetch_robots_txt(domain, url)
        self._robots_cache[domain] = (parser, now)
        
        return parser
    
    def check_robots_txt(self, url: str) -> bool:
        """
        Check if robots.txt allows access to a URL.
        
        Args:
            url: URL to check
        
        Returns:
            True if allowed, False if disallowed
        """
        try:
            parser = self._get_robots_parser(url)
            allowed = parser.can_fetch(self._user_agent, url)
            
            if not allowed:
                logger.warning(f"robots.txt disallows access to {url}")
            
            return allowed
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            # On error, assume allowed to avoid blocking legitimate access
            return True
    
    def _clean_old_timestamps(self, domain: str, window_seconds: float) -> None:
        """Remove timestamps older than the rate limit window."""
        if domain not in self._rate_limits:
            return
        
        now = time.time()
        cutoff = now - window_seconds
        self._rate_limits[domain] = [
            ts for ts in self._rate_limits[domain] if ts > cutoff
        ]
    
    def check_rate_limit(self, url: str) -> bool:
        """
        Check if a request to a URL would violate rate limits.
        
        Args:
            url: URL to check
        
        Returns:
            True if request is allowed, False if rate limit would be exceeded
        """
        domain = self._get_domain(url)
        
        # Get rate limit for this domain
        rate_limit = self._custom_rate_limits.get(domain, self._default_rate_limit_seconds)
        
        # Clean old timestamps
        self._clean_old_timestamps(domain, rate_limit)
        
        # Check if we can make a request
        if domain not in self._rate_limits:
            self._rate_limits[domain] = []
        
        now = time.time()
        
        if len(self._rate_limits[domain]) == 0:
            # No recent requests, allow
            return True
        
        last_request = self._rate_limits[domain][-1]
        time_since_last = now - last_request
        
        if time_since_last >= rate_limit:
            return True
        else:
            logger.warning(
                f"Rate limit exceeded for {domain}. "
                f"Last request {time_since_last:.2f}s ago, limit is {rate_limit}s"
            )
            return False
    
    def record_request(self, url: str) -> None:
        """
        Record that a request was made to a URL.
        Updates rate limiting state.
        
        Args:
            url: URL that was accessed
        """
        domain = self._get_domain(url)
        
        if domain not in self._rate_limits:
            self._rate_limits[domain] = []
        
        self._rate_limits[domain].append(time.time())
        logger.debug(f"Recorded request to {domain}")
    
    def wait_for_rate_limit(self, url: str) -> float:
        """
        Calculate how long to wait before making a request to respect rate limits.
        
        Args:
            url: URL to check
        
        Returns:
            Seconds to wait (0 if can proceed immediately)
        """
        domain = self._get_domain(url)
        rate_limit = self._custom_rate_limits.get(domain, self._default_rate_limit_seconds)
        
        if domain not in self._rate_limits or len(self._rate_limits[domain]) == 0:
            return 0.0
        
        now = time.time()
        last_request = self._rate_limits[domain][-1]
        time_since_last = now - last_request
        
        if time_since_last >= rate_limit:
            return 0.0
        else:
            return rate_limit - time_since_last
    
    def prioritize_access_method(
        self,
        has_api: bool = False,
        has_rss: bool = False,
        can_scrape: bool = False
    ) -> Optional[str]:
        """
        Determine the best access method based on availability.
        Priority: API > RSS > Scrape
        
        Args:
            has_api: Whether API access is available
            has_rss: Whether RSS feed is available
            can_scrape: Whether web scraping is allowed
        
        Returns:
            'api', 'rss', 'scrape', or None if no method available
        """
        if has_api:
            logger.info("Selected access method: API (highest priority)")
            return 'api'
        elif has_rss:
            logger.info("Selected access method: RSS")
            return 'rss'
        elif can_scrape:
            logger.info("Selected access method: scrape (lowest priority)")
            return 'scrape'
        else:
            logger.warning("No access method available")
            return None
    
    def can_access(self, url: str, method: str = 'scrape') -> Tuple[bool, str]:
        """
        Check if access to a URL is allowed based on all policies.
        
        Args:
            url: URL to check
            method: Access method ('api', 'rss', 'scrape')
        
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # API and RSS don't need robots.txt or rate limit checks
        if method in ['api', 'rss']:
            return True, f"{method.upper()} access allowed"
        
        # For scraping, check robots.txt
        if not self.check_robots_txt(url):
            return False, "robots.txt disallows access"
        
        # Check rate limit
        if not self.check_rate_limit(url):
            wait_time = self.wait_for_rate_limit(url)
            return False, f"Rate limit exceeded, wait {wait_time:.2f}s"
        
        return True, "Access allowed"
    
    def log_provenance(
        self,
        url: str,
        method: str,
        success: bool,
        rate_limit_respected: bool = True
    ) -> Dict:
        """
        Create provenance metadata for a data access attempt.
        
        Args:
            url: URL accessed
            method: Access method used
            success: Whether access was successful
            rate_limit_respected: Whether rate limits were respected
        
        Returns:
            Dictionary with provenance metadata
        """
        domain = self._get_domain(url)
        
        provenance = {
            'url': url,
            'domain': domain,
            'method': method,
            'timestamp': datetime.utcnow().isoformat(),
            'success': success,
            'rate_limit_respected': rate_limit_respected,
            'user_agent': self._user_agent
        }
        
        # Add robots.txt status for scraping
        if method == 'scrape':
            provenance['robots_txt_allowed'] = self.check_robots_txt(url)
        
        logger.info(f"Logged provenance for {url}: {provenance}")
        
        return provenance
