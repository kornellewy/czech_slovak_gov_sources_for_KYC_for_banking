"""
RPO Slovak Scraper - Register of Legal Entities
API: https://api.statistics.sk/rpo/v1

Note: API parameter format needs discovery.
This implementation provides mock data fallback for known entities.

Output format: UnifiedOutput with entity, holders, tax_info, and metadata sections.
"""

from typing import Optional, Dict, Any, List

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, Metadata,
    parse_address, normalize_status, normalize_country_code,
    get_register_name, get_retrieved_at
)
from config.constants import RPO_BASE_URL, RPO_RATE_LIMIT, RPO_OUTPUT_DIR, RPO_ENTITY_URL_TEMPLATE


class RpoSlovakScraper(BaseScraper):
    """Scraper for Slovak Register of Legal Entities (RPO).

    Note: API endpoint format needs discovery. This implementation
    tries multiple endpoint formats and falls back to mock data.

    Example:
        scraper = RpoSlovakScraper()

        # Search by ICO
        entity = scraper.search_by_id("35763491")
        print(entity['name'])  # "Slovenská sporiteľňa, a.s."
    """

    BASE_URL = RPO_BASE_URL
    SOURCE_NAME = "RPO_SK"

    def __init__(self, enable_snapshots: bool = True):
        """Initialize RPO Slovak scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=RPO_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search entity by ICO.

        Args:
            ico: Slovak entity identification number

        Returns:
            Dictionary with entity data or None if not found
        """
        self.logger.info(f"Searching RPO by ICO: {ico}")

        # Try multiple endpoint formats
        endpoints = [
            f"{self.BASE_URL}/entity/{ico}",
            f"{self.BASE_URL}/search?ico={ico}",
            f"{self.BASE_URL}/{ico}",
        ]

        for url in endpoints:
            try:
                response = self.http_client.get(url)
                data = response.json()

                # Check for valid response
                if data and not data.get("error"):
                    if self.enable_snapshots:
                        self.save_snapshot(data, ico, self.SOURCE_NAME)
                    return self._parse_response(data, ico)

            except Exception as e:
                self.logger.debug(f"Endpoint {url} failed: {e}")
                continue

        # Fall back to mock data
        self.logger.warning(f"API endpoints failed, using mock data for {ico}")
        return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search entities by name.

        Args:
            name: Entity name to search for

        Returns:
            List of matching entities
        """
        self.logger.info(f"Searching RPO by name: {name}")

        try:
            url = f"{self.BASE_URL}/search"
            params = {"name": name}
            response = self.http_client.get(url, params=params)
            data = response.json()

            if data and not data.get("error"):
                return self._parse_search_results(data)

        except Exception as e:
            self.logger.warning(f"Search failed: {e}")

        return []

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Dict[str, Any]:
        """Parse API response into unified format.

        Args:
            data: Raw API response
            ico: Original ICO

        Returns:
            Unified output dictionary
        """
        ico_val = data.get("ico", ico)

        # Parse address
        address_data = self._parse_address(data)
        address = parse_address(address_data)

        # Build entity
        entity = Entity(
            ico_registry=ico_val,
            company_name_registry=data.get("name") or data.get("obchodne_meno"),
            legal_form=data.get("legal_form") or data.get("pravna_forma"),
            legal_form_code=data.get("legal_form_code"),
            status=normalize_status(data.get("status")),
            incorporation_date=data.get("date_registered") or data.get("datum_zapisu"),
            registered_address=address,
        )

        # Build metadata
        register_url = RPO_ENTITY_URL_TEMPLATE.format(ico=ico_val) if ico_val else None
        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=register_url,
            retrieved_at=get_retrieved_at(),
            is_mock=False,
        )

        # Create unified output
        output = UnifiedOutput(
            entity=entity,
            holders=[],
            tax_info=None,
            metadata=metadata,
        )

        return output.to_dict()

    def _parse_address(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Parse address from response data.

        Args:
            data: Response data

        Returns:
            Address dictionary
        """
        addr = data.get("address") or data.get("sidlo") or {}
        if isinstance(addr, str):
            return {"full_address": addr}
        return addr

    def _parse_search_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse search results.

        Args:
            data: Raw search response

        Returns:
            List of entity dictionaries
        """
        results = []
        entities = data.get("results") or data.get("entities") or []

        for entity in entities:
            results.append({
                "source": self.SOURCE_NAME,
                "ico": entity.get("ico"),
                "name": entity.get("name") or entity.get("obchodne_meno"),
                "legal_form": entity.get("legal_form"),
                "retrieved_at": get_retrieved_at(),
            })

        return results

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known test entities in unified format.

        Args:
            ico: Entity identification number

        Returns:
            Unified output dictionary with mock data
        """
        # Mock database with raw data
        mock_raw_data = {
            "35763491": {
                "name": "Slovenská sporiteľňa, a.s.",
                "legal_form": "Akciová spoločnosť",
                "legal_form_code": "112",
                "status": "active",
                "date_registered": "1991-01-01",
                "address": {
                    "street": "Tomášikova 48",
                    "city": "Bratislava",
                    "postal_code": "832 37",
                    "country": "Slovensko",
                    "country_code": "SK",
                    "full_address": "Tomášikova 48, 832 37 Bratislava"
                },
            },
            "31328356": {
                "name": "Všeobecná úverová banka, a.s.",
                "legal_form": "Akciová spoločnosť",
                "status": "active",
                "address": {
                    "city": "Bratislava",
                    "country": "Slovensko",
                    "country_code": "SK",
                },
            },
            "44103755": {
                "name": "Slovak Telekom, a.s.",
                "legal_form": "Akciová spoločnosť",
                "status": "active",
                "address": {
                    "city": "Bratislava",
                    "country": "Slovensko",
                    "country_code": "SK",
                },
            },
            "36246621": {
                "name": "Doprastav, a.s.",
                "legal_form": "Akciová spoločnosť",
                "status": "active",
                "address": {
                    "city": "Bratislava",
                    "country": "Slovensko",
                    "country_code": "SK",
                },
            }
        }

        # Get raw data or create default
        if ico in mock_raw_data:
            raw = mock_raw_data[ico]
        else:
            raw = {
                "name": f"Unknown Entity ({ico})",
                "status": "unknown",
                "address": None,
            }

        # Parse address
        address = parse_address(raw.get("address"))

        # Build entity
        entity = Entity(
            ico_registry=ico,
            company_name_registry=raw.get("name"),
            legal_form=raw.get("legal_form"),
            legal_form_code=raw.get("legal_form_code"),
            status=normalize_status(raw.get("status")),
            incorporation_date=raw.get("date_registered"),
            registered_address=address,
        )

        # Build metadata
        register_url = RPO_ENTITY_URL_TEMPLATE.format(ico=ico)
        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=register_url,
            retrieved_at=get_retrieved_at(),
            is_mock=True,
        )

        # Create unified output
        output = UnifiedOutput(
            entity=entity,
            holders=[],
            tax_info=None,
            metadata=metadata,
        )

        return output.to_dict()

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in RPO output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="rpo")
