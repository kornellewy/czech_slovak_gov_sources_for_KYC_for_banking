"""Playwright-based base scraper for dynamic websites.

This module provides PlaywrightBaseScraper, a base class for scrapers that need
to interact with dynamic websites using browser automation. It inherits from
BaseScraper and adds Playwright-specific functionality.

The class handles:
- Browser lifecycle (launch, close)
- Page navigation and waiting
- Screenshot capture for debugging
- JavaScript execution
- Error handling with graceful fallback

Example:
    class MyDynamicScraper(PlaywrightBaseScraper):
        def search_by_id(self, identifier: str) -> Optional[dict]:
            with self._get_page() as page:
                page.goto(f"https://example.com/search?id={identifier}")
                page.wait_for_selector(".result", timeout=10000)
                return self._parse_results(page.content())
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

from src.scrapers.base import BaseScraper
from config.constants import (
    BASE_DIR, PLAYWRIGHT_HEADLESS, PLAYWRIGHT_TIMEOUT,
    PLAYWRIGHT_SCREENSHOT_DIR
)


class PlaywrightError(Exception):
    """Exception raised when Playwright operations fail."""
    pass


class PlaywrightNotAvailableError(PlaywrightError):
    """Exception raised when Playwright is not installed or configured."""
    pass


class PlaywrightBaseScraper(BaseScraper):
    """Base scraper class using Playwright for browser automation.

    This class extends BaseScraper with Playwright browser capabilities.
    It provides common utilities for scraping dynamic websites that
    require JavaScript rendering.

    Features:
    - Automatic browser lifecycle management
    - Context manager for safe page handling
    - Screenshot capture for debugging
    - JavaScript execution
    - Configurable headless mode
    - Graceful fallback to static scraping

    Example:
        class JusticeCzechScraper(PlaywrightBaseScraper):
            def search_by_id(self, ico: str) -> Optional[dict]:
                try:
                    with self._get_page() as page:
                        page.goto(f"{self.SEARCH_URL}?ico={ico}")
                        page.wait_for_selector("table.result-details")
                        return self._extract_subjects(page.content())
                except PlaywrightError:
                    # Fallback to static scraping
                    return self._static_fallback(ico)

    Configuration:
        - PLAYWRIGHT_HEADLESS: Run browser in headless mode (default: true)
        - PLAYWRIGHT_TIMEOUT: Default timeout in ms (default: 30000)
        - PLAYWRIGHT_SCREENSHOT_DIR: Directory for screenshots
    """

    def __init__(self, enable_snapshots: bool = False, headless: Optional[bool] = None):
        """Initialize Playwright base scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
            headless: Override default headless mode (None uses env var)
        """
        super().__init__(enable_snapshots=enable_snapshots)

        # Use provided headless setting or fall back to config
        self.headless = headless if headless is not None else PLAYWRIGHT_HEADLESS
        self.playwright = None
        self.browser = None
        self._playwright_available = None
        self._browser_lock = asyncio.Lock()

        # Create screenshot directory if enabled
        self.screenshot_dir = PLAYWRIGHT_SCREENSHOT_DIR
        if self.enable_snapshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            f"Initialized PlaywrightBaseScraper (headless={self.headless})"
        )

    def _check_playwright_available(self) -> bool:
        """Check if Playwright is available and browsers are installed.

        Returns:
            True if Playwright can be used, False otherwise
        """
        if self._playwright_available is not None:
            return self._playwright_available

        try:
            from playwright.sync_api import sync_playwright
            # Try to import - will raise ImportError if not installed
            self._playwright_available = True
            return True
        except ImportError as e:
            self.logger.warning(f"Playwright not installed: {e}")
            self.logger.info("Install with: pip install playwright && playwright install chromium")
            self._playwright_available = False
            return False

    @contextmanager
    def _get_page(self):
        """Context manager for getting a Playwright page.

        This method handles browser initialization, page creation,
        and cleanup. It's thread-safe and handles errors gracefully.

        Yields:
            Playwright Page object

        Raises:
            PlaywrightNotAvailableError: If Playwright is not installed
            PlaywrightError: If browser automation fails

        Example:
            with self._get_page() as page:
                page.goto("https://example.com")
                title = page.title()
        """
        if not self._check_playwright_available():
            raise PlaywrightNotAvailableError(
                "Playwright is not available. Install with: pip install playwright"
            )

        from playwright.sync_api import sync_playwright

        playwright_ctx = None
        browser = None
        page = None

        try:
            # Create Playwright context
            playwright_ctx = sync_playwright().start()
            self.playwright = playwright_ctx

            # Launch browser
            browser = playwright_ctx.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            self.browser = browser

            # Create new context with realistic user agent
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='cs-CZ',
                timezone_id='Europe/Prague',
            )

            # Add extra headers to avoid bot detection
            context.set_extra_http_headers({
                'Accept-Language': 'cs-CZ,cs;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })

            # Create page
            page = context.new_page()

            # Set default timeout
            page.set_default_timeout(PLAYWRIGHT_TIMEOUT)

            self.logger.debug("Playwright page created successfully")

            yield page

        except Exception as e:
            self.logger.error(f"Playwright error: {e}")
            raise PlaywrightError(f"Browser automation failed: {e}") from e

        finally:
            # Cleanup
            if page:
                try:
                    page.close()
                except Exception:
                    pass
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            if playwright_ctx:
                try:
                    playwright_ctx.stop()
                except Exception:
                    pass

    def _wait_for_content(
        self,
        page,
        selector: str,
        timeout: Optional[int] = None
    ) -> bool:
        """Wait for content to appear on the page.

        Args:
            page: Playwright Page object
            selector: CSS selector to wait for
            timeout: Timeout in milliseconds (None uses default)

        Returns:
            True if content found, False if timeout

        Example:
            if not self._wait_for_content(page, "table.result-details"):
                return None
        """
        timeout = timeout or PLAYWRIGHT_TIMEOUT
        try:
            page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception as e:
            self.logger.debug(f"Timeout waiting for selector '{selector}': {e}")
            return False

    def _take_screenshot(
        self,
        page,
        filename: Optional[str] = None,
        full_page: bool = True
    ) -> Optional[str]:
        """Take a screenshot of the current page.

        Args:
            page: Playwright Page object
            filename: Output filename (None generates timestamp-based name)
            full_page: Whether to capture full scrollable page

        Returns:
            Screenshot file path or None if snapshots disabled
        """
        if not self.enable_snapshots:
            return None

        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"

            filepath = self.screenshot_dir / filename
            page.screenshot(path=str(filepath), full_page=full_page)

            self.logger.debug(f"Screenshot saved: {filepath}")
            return str(filepath)
        except Exception as e:
            self.logger.warning(f"Failed to take screenshot: {e}")
            return None

    def _execute_js(self, page, script: str) -> Any:
        """Execute JavaScript in the browser context.

        Args:
            page: Playwright Page object
            script: JavaScript code to execute

        Returns:
            Result of JavaScript execution

        Example:
            # Scroll to bottom of page
            self._execute_js(page, "window.scrollTo(0, document.body.scrollHeight)")
        """
        try:
            return page.evaluate(script)
        except Exception as e:
            self.logger.warning(f"JavaScript execution failed: {e}")
            return None

    def _scroll_and_wait(
        self,
        page,
        max_scrolls: int = 5,
        scroll_delay: int = 500
    ) -> None:
        """Handle infinite scroll pages by scrolling and waiting for content.

        Args:
            page: Playwright Page object
            max_scrolls: Maximum number of scroll attempts
            scroll_delay: Delay between scrolls in milliseconds
        """
        for i in range(max_scrolls):
            old_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(scroll_delay)

            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == old_height:
                # No more content loaded
                break

    def _navigate_and_wait(
        self,
        page,
        url: str,
        wait_selector: Optional[str] = None,
        wait_until: str = "networkidle"
    ) -> bool:
        """Navigate to URL and wait for content to load.

        Args:
            page: Playwright Page object
            url: URL to navigate to
            wait_selector: Optional CSS selector to wait for
            wait_until: Navigation condition ("networkidle", "load", "domcontentloaded")

        Returns:
            True if navigation successful, False otherwise
        """
        try:
            self.logger.debug(f"Navigating to: {url}")
            page.goto(url, wait_until=wait_until, timeout=PLAYWRIGHT_TIMEOUT)

            if wait_selector:
                return self._wait_for_content(page, wait_selector)

            return True
        except Exception as e:
            self.logger.error(f"Navigation failed for {url}: {e}")
            return False

    def _extract_text_content(
        self,
        page,
        selector: str,
        attribute: Optional[str] = None
    ) -> List[str]:
        """Extract text content or attributes from matching elements.

        Args:
            page: Playwright Page object
            selector: CSS selector
            attribute: Optional attribute name (None returns text content)

        Returns:
            List of text content or attribute values

        Example:
            # Get all hrefs from links
            links = self._extract_text_content(page, "a.link", "href")

            # Get text from all headings
            headings = self._extract_text_content(page, "h2")
        """
        try:
            if attribute:
                elements = page.query_selector_all(selector)
                return [el.get_attribute(attribute) for el in elements if el]
            else:
                elements = page.query_selector_all(selector)
                return [el.text_content() or "" for el in elements]
        except Exception as e:
            self.logger.warning(f"Failed to extract content: {e}")
            return []

    def _get_page_html(self, page) -> str:
        """Get the current page HTML content.

        Args:
            page: Playwright Page object

        Returns:
            HTML content as string
        """
        return page.content()

    def close(self) -> None:
        """Clean up Playwright resources.

        Overrides BaseScraper.close() to also close browser.
        """
        super().close()

        if self.browser:
            try:
                self.browser.close()
                self.browser = None
            except Exception:
                pass

        if self.playwright:
            try:
                self.playwright.stop()
                self.playwright = None
            except Exception:
                pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with Playwright cleanup."""
        self.close()
