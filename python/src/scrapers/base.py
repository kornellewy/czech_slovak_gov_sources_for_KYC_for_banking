"""Abstract base scraper class defining the interface for all scrapers."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pathlib import Path
import hashlib
import json
from datetime import datetime

from src.utils.http_client import HTTPClient
from src.utils.json_handler import JSONHandler
from src.utils.logger import get_logger
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
        self.logger = get_logger(self.__class__.__name__)
        self.json_handler = JSONHandler()
        self.http_client: Optional[HTTPClient] = None
        self.enable_snapshots = enable_snapshots

        # Create snapshots directory if enabled
        self.snapshots_dir = BASE_DIR / "snapshots"
        if self.enable_snapshots:
            self.snapshots_dir.mkdir(parents=True, exist_ok=True)

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
        return self.__class__.__name__.replace("Scraper", "").upper()

    def close(self) -> None:
        """Clean up resources (HTTP connections, etc.)."""
        if self.http_client:
            self.http_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

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
