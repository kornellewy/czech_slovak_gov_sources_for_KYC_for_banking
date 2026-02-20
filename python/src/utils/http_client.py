"""HTTP client with retry logic and rate limiting support."""

import time
import requests
from typing import Optional, Dict, Any
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from config.constants import USER_AGENT


class HTTPClient:
    """HTTP client with retry logic, connection pooling, and custom headers.

    Example:
        client = HTTPClient(rate_limit=60)
        response = client.get("https://example.com/api")
        data = client.post("https://example.com/search", json={"query": "test"})
    """

    def __init__(
        self,
        rate_limit: Optional[int] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30,
        user_agent: Optional[str] = None
    ):
        """Initialize HTTP client.

        Args:
            rate_limit: Maximum requests per minute (None = no limit)
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff multiplier for retries
            timeout: Request timeout in seconds
            user_agent: Custom User-Agent string
        """
        self.rate_limit = rate_limit
        self.min_request_interval = 60 / rate_limit if rate_limit else 0
        self.last_request_time = 0
        self.timeout = timeout

        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update({
            'User-Agent': user_agent or USER_AGENT,
            'Accept': 'application/json',
            'Accept-Language': 'cs-SK,cs;q=0.9,sk;q=0.8,en;q=0.7',
        })

    def _apply_rate_limit(self) -> None:
        """Apply rate limiting by sleeping if necessary."""
        if self.min_request_interval > 0:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                sleep_time = self.min_request_interval - elapsed
                time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """Send GET request.

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional requests arguments

        Returns:
            Response object
        """
        self._apply_rate_limit()

        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        response = self.session.get(
            url,
            params=params,
            headers=request_headers,
            timeout=self.timeout,
            **kwargs
        )
        response.raise_for_status()

        # Handle ORSR's windows-1250 encoding
        if "orsr.sk" in url.lower():
            response.encoding = "windows-1250"

        return response

    def get_html(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Send GET request and return text content with proper encoding.

        Args:
            url: Request URL
            params: Query parameters

        Returns:
            Response text content
        """
        response = self.get(url, params=params)
        return response.text

    def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """Send POST request.

        Args:
            url: Request URL
            data: Form data
            json: JSON data
            headers: Additional headers
            **kwargs: Additional requests arguments

        Returns:
            Response object
        """
        self._apply_rate_limit()

        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)

        response = self.session.post(
            url,
            data=data,
            json=json,
            headers=request_headers,
            timeout=self.timeout,
            **kwargs
        )
        response.raise_for_status()
        return response

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
