"""
Stats Slovak Scraper - Statistics Office (StatDat)
API: https://statdat.statistics.sk/api

This scraper retrieves statistical datasets from the Slovak Statistics Office.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.field_mapper import get_retrieved_at
from config.constants import STATS_BASE_URL, STATS_API_URL, STATS_OUTPUT_DIR


class StatsSlovakScraper(BaseScraper):
    """Scraper for Slovak Statistics Office (StatDat).

    Note: This scraper focuses on datasets rather than individual entities.

    Example:
        scraper = StatsSlovakScraper()

        # List available datasets
        datasets = scraper.list_datasets()
        for ds in datasets:
            print(f"{ds['id']}: {ds['title']}")

        # Search datasets by keyword
        datasets = scraper.search_by_name("podniky")

        # Get specific dataset
        data = scraper.get_dataset("podniky_2024")
    """

    BASE_URL = STATS_BASE_URL
    API_URL = STATS_API_URL
    SOURCE_NAME = "STATS_SK"

    def __init__(self, enable_snapshots: bool = False):
        """Initialize Stats Slovak scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=120)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get dataset by ID.

        Args:
            identifier: Dataset ID

        Returns:
            Dataset dictionary or None
        """
        return self.get_dataset(identifier)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search datasets by keyword.

        Args:
            name: Keyword to search for

        Returns:
            List of matching datasets
        """
        return self.search_datasets(name)

    def list_datasets(self) -> List[Dict[str, Any]]:
        """List available datasets.

        Returns:
            List of dataset metadata dictionaries
        """
        self.logger.info("Listing available datasets")

        # Try to fetch from API, fall back to mock data
        try:
            url = f"{self.API_URL}/datasets"
            response = self.http_client.get(url)
            data = response.json()
            return data.get("datasets", [])
        except Exception as e:
            self.logger.warning(f"Failed to fetch datasets from API: {e}")
            return self._get_mock_datasets()

    def search_datasets(self, keyword: str) -> List[Dict[str, Any]]:
        """Search datasets by keyword.

        Args:
            keyword: Search keyword

        Returns:
            List of matching datasets
        """
        self.logger.info(f"Searching datasets for: {keyword}")

        all_datasets = self.list_datasets()

        keyword_lower = keyword.lower()
        return [
            ds for ds in all_datasets
            if keyword_lower in ds.get("title", "").lower()
            or keyword_lower in ds.get("description", "").lower()
        ]

    def get_dataset(self, dataset_id: str, format: str = "json") -> Optional[Dict[str, Any]]:
        """Get specific dataset by ID.

        Args:
            dataset_id: Dataset identifier
            format: Output format (json, csv)

        Returns:
            Dataset dictionary or None
        """
        self.logger.info(f"Getting dataset: {dataset_id}")

        try:
            url = f"{self.API_URL}/datasets/{dataset_id}"
            params = {"format": format}
            response = self.http_client.get(url, params=params)
            data = response.json()

            return {
                "source": self.SOURCE_NAME,
                "dataset_id": dataset_id,
                "records": data.get("records", []),
                "total_records": data.get("total", 0),
                "retrieved_at": get_retrieved_at(),
            }

        except Exception as e:
            self.logger.warning(f"Failed to fetch dataset {dataset_id}: {e}")
            return self._get_mock_dataset(dataset_id)

    def get_economic_indicators(self, year: int = None) -> Optional[Dict[str, Any]]:
        """Get economic indicators dataset.

        Args:
            year: Year for indicators (optional)

        Returns:
            Economic indicators dictionary
        """
        year = year or datetime.now().year
        return self.get_dataset(f"economic_indicators_{year}")

    def get_regional_statistics(self, region: str = None) -> Optional[Dict[str, Any]]:
        """Get regional statistics.

        Args:
            region: Region code (optional)

        Returns:
            Regional statistics dictionary
        """
        if region:
            return self.get_dataset(f"regional_{region}")
        return self.get_dataset("regional_all")

    def _get_mock_datasets(self) -> List[Dict[str, Any]]:
        """Get mock dataset list for demonstration.

        Returns:
            List of mock datasets
        """
        return [
            {
                "id": "podniky_2024",
                "title": "Podniky 2024 (Enterprises 2024)",
                "description": "Statistics on Slovak enterprises",
                "category": "economy",
                "updated": "2024-01-15"
            },
            {
                "id": "population_2024",
                "title": "Obyvateľstvo 2024 (Population 2024)",
                "description": "Population statistics",
                "category": "demographics",
                "updated": "2024-01-10"
            },
            {
                "id": "economic_indicators_2024",
                "title": "Ekonomické ukazovatele 2024",
                "description": "Key economic indicators",
                "category": "economy",
                "updated": "2024-01-20"
            },
            {
                "id": "regional_all",
                "title": "Regionálna štatistika",
                "description": "Regional statistics for all Slovakia",
                "category": "regional",
                "updated": "2024-01-05"
            },
        ]

    def _get_mock_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Get mock dataset for demonstration.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Mock dataset dictionary
        """
        return {
            "source": self.SOURCE_NAME,
            "dataset_id": dataset_id,
            "records": [],
            "total_records": 0,
            "note": "Mock data for demonstration",
            "mock": True,
            "retrieved_at": get_retrieved_at()
        }

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in Stats output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="stats")
