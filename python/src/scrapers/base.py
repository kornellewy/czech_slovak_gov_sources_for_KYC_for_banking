"""Abstract base scraper class defining the interface for all scrapers."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path
import hashlib
import json
import time
from datetime import datetime

from src.utils.http_client import HTTPClient
from src.utils.json_handler import JSONHandler
from src.utils.logger import get_logger
from src.utils.logger_enhanced import ScraperLogger
from config.constants import BASE_DIR, OUTPUT_DIR


class BaseScraper(ABC):
    """Abstract base class for all scrapers.

    All scrapers must inherit from this class and implement
    the required abstract methods.

    Example:
        class MyScraper(BaseScraper):
            def search_by_id(self, identifier: str) -> Optional[dict]:
                # Implementation here
                pass

            def search_by_name(self, name: str) -> List[dict]:
                # Implementation here
                pass
    """

    def __init__(self, enable_snapshots: bool = False):
        """Initialize base scraper with common utilities.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        self.source_name = self.__class__.__name__.replace("Scraper", "").upper()
        self.logger = get_logger(self.__class__.__name__)
        self.enhanced_logger = ScraperLogger(self.__class__.__name__)
        self.json_handler = JSONHandler()
        self.http_client: Optional[HTTPClient] = None
        self.enable_snapshots = enable_snapshots

        # Create snapshots directory if enabled
        self.snapshots_dir = BASE_DIR / "snapshots"
        if self.enable_snapshots:
            self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Initialized {self.source_name} scraper")

    @abstractmethod
    def search_by_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Search by identification number (IČO for Czech, ICO for Slovak).

        Args:
            identifier: Company/person identification number

        Returns:
            Dictionary with entity data or None if not found

        Example:
            result = scraper.search_by_id("00006947")
            if result:
                print(result['name'])
        """
        pass

    @abstractmethod
    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search by company/person name.

        Args:
            name: Company or person name to search for

        Returns:
            List of dictionaries with matching entities

        Example:
            results = scraper.search_by_name("Ministerstvo financí")
            for entity in results:
                print(f"{entity['name']} - {entity['ico']}")
        """
        pass

    @abstractmethod
    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in appropriate output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file

        Example:
            filepath = scraper.save_to_json(company_data, "company_123.json")
            print(f"Saved to {filepath}")
        """
        pass

    def get_source_name(self) -> str:
        """Return the source name for this scraper.

        Returns:
            Source identifier string
        """
        return self.source_name

    def close(self) -> None:
        """Clean up resources (HTTP connections, etc.)."""
        self.logger.debug(f"Closing {self.source_name} scraper")
        if self.http_client:
            self.http_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # Enhanced logging methods for common operations

    def log_request(self, method: str, url: str, **kwargs):
        """Log HTTP request with context."""
        self.enhanced_logger.log_request(method, url, scraper=self.source_name, **kwargs)

    def log_response(self, url: str, status_code: int, duration_ms: float, **kwargs):
        """Log HTTP response with context."""
        self.enhanced_logger.log_response(url, status_code, duration_ms, scraper=self.source_name, **kwargs)

    def log_parse_start(self, data_source: str, **kwargs):
        """Log parse start."""
        self.enhanced_logger.log_parse_start(data_source, scraper=self.source_name, **kwargs)

    def log_parse_complete(self, data_source: str, items_found: int = 0, **kwargs):
        """Log parse complete."""
        self.enhanced_logger.log_parse_complete(data_source, items_found, scraper=self.source_name, **kwargs)

    def log_maintenance(self, source: str = None, **kwargs):
        """Log maintenance detected."""
        source_name = source or self.source_name
        self.enhanced_logger.log_maintenance(source_name, scraper=self.source_name, **kwargs)

    def log_rate_limit(self, delay: float, **kwargs):
        """Log rate limit delay."""
        self.enhanced_logger.log_rate_limit(delay, scraper=self.source_name, **kwargs)

    def log_mock_fallback(self, reason: str, **kwargs):
        """Log mock data fallback."""
        self.enhanced_logger.log_mock_fallback(self.source_name, reason, scraper=self.source_name, **kwargs)

    def log_operation_start(self, operation: str, **context):
        """Log operation start - returns context manager."""
        return self.enhanced_logger.log_context(operation, scraper=self.source_name, **context)

    def log_search_start(self, identifier: str = None, search_type: str = None):
        """Log search operation start."""
        self.logger.info(f"[{self.source_name}] Search started: {search_type or 'by_id'} = {identifier or 'N/A'}")

    def log_search_complete(self, results_count: int = 0, identifier: str = None):
        """Log search operation complete."""
        if identifier:
            self.logger.info(f"[{self.source_name}] Search complete for {identifier}: {results_count} result(s)")
        else:
            self.logger.info(f"[{self.source_name}] Search complete: {results_count} result(s)")

    def log_save_result(self, filename: str, filepath: str = None):
        """Log result save."""
        self.logger.info(f"[{self.source_name}] Saved result: {filename}")

    def log_error(self, operation: str, error: Exception, **context):
        """Log error with context."""
        self.logger.error(f"[{self.source_name}] {operation} error: {error}", extra={'context': context, 'scraper': self.source_name})

    def log_warning(self, message: str, **context):
        """Log warning with context."""
        self.logger.warning(f"[{self.source_name}] {message}", extra={'context': context, 'scraper': self.source_name})

    def log_debug(self, message: str, **context):
        """Log debug message with context."""
        self.logger.debug(f"[{self.source_name}] {message}", extra={'context': context, 'scraper': self.source_name})

    def log_info(self, message: str, **context):
        """Log info message with context."""
        self.logger.info(f"[{self.source_name}] {message}", extra={'context': context, 'scraper': self.source_name})

    def time_request(self, func):
        """Decorator to time HTTP requests."""
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000

                # Log response timing
                if hasattr(result, 'status_code'):
                    self.log_response(
                        kwargs.get('url', 'unknown'),
                        result.status_code,
                        duration_ms
                    )

                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                self.logger.debug(f"Request failed after {duration_ms:.0f}ms: {e}")
                raise

        return wrapper

    def save_snapshot(self, data: Any, identifier: str, source: str) -> Optional[str]:
        """Save a raw data snapshot for audit trail.

        Args:
            data: Raw data to save (dict, list, or string)
            identifier: Entity identifier (ICO)
            source: Source name (e.g., "ARES_CZ")

        Returns:
            Snapshot file path or None if snapshots disabled

        Example:
            snapshot_ref = scraper.save_snapshot(raw_data, "00006947", "ARES_CZ")
            # Returns: "snapshots/ARES_CZ_00006947_20240115_123045_a1b2c3d4.json"
        """
        if not self.enable_snapshots:
            return None

        try:
            # Create filename with timestamp and hash
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            content = json.dumps(data, default=str, ensure_ascii=False)
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

            filename = f"{source}_{identifier}_{timestamp}_{content_hash}.json"
            filepath = self.snapshots_dir / filename

            # Write snapshot
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, default=str, ensure_ascii=False, indent=2))

            self.logger.debug(f"Saved snapshot: {filepath}")
            return str(filepath.relative_to(BASE_DIR))

        except Exception as e:
            self.logger.warning(f"Failed to save snapshot: {e}")
            return None

    def get_snapshot_reference(self, data: Any, identifier: str, source: str) -> Optional[str]:
        """Generate snapshot reference without saving.

        Creates a consistent reference string based on data content.

        Args:
            data: Raw data
            identifier: Entity identifier
            source: Source name

        Returns:
            Snapshot reference string or None
        """
        if not self.enable_snapshots:
            return None

        try:
            content = json.dumps(data, default=str, ensure_ascii=False, sort_keys=True)
            content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
            return f"{source}_{identifier}_{content_hash}"
        except Exception:
            return None
