"""
IVES Slovak Scraper - Register of Non-Governmental Non-Profit Organizations
Website: https://ives.minv.sk/rmno
Official Name: Register mimovládnych neziskových organizácií (RMNO)

This scraper retrieves information about non-governmental non-profit organizations
registered with the Slovak Ministry of Interior, including:
- Civic associations (Občianske združenia)
- Foundations (Nadácie)
- Non-investment funds (Neinvestičné fondy)
- Non-profit organizations providing general benefit services (NNOs)

The website uses JavaScript-heavy framework and may require Selenium for full functionality.

Output format: UnifiedOutput with entity, ngo_info, and metadata sections.
"""

import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Address, Metadata,
    normalize_status, get_register_name, get_retrieved_at
)
from config.constants import (
    IVES_BASE_URL, IVES_SEARCH_URL, IVES_RATE_LIMIT,
    IVES_OUTPUT_DIR, IVES_ENTITY_URL_TEMPLATE
)


class IvesSlovakScraper(BaseScraper):
    """Scraper for Slovak Register of Non-Governmental Non-Profit Organizations (RMNO).

    Provides access to information about:
    - Občianske združenia (Civic associations)
    - Nadácie (Foundations)
    - Neinvestičné fondy (Non-investment funds)
    - NNO providing general benefit services

    Note: The website at ives.minv.sk/rmno uses a JavaScript framework.
    This implementation provides mock data and a pattern for future implementation.

    Example:
        scraper = IvesSlovakScraper()

        # Search by ICO
        ngo = scraper.search_by_id("12345678")
        print(ngo.get('ngo_info'))
    """

    BASE_URL = IVES_BASE_URL
    SEARCH_URL = f"{IVES_BASE_URL}/rmno"
    SOURCE_NAME = "IVES_SK"

    # NGO types
    NGO_TYPES = {
        "občianske združenie": "civic_association",
        "občianske združenia": "civic_association",
        "nadácia": "foundation",
        "nadácie": "foundation",
        "neinvestičný fond": "non_investment_fund",
        "neinvestičné fondy": "non_investment_fund",
        "nno": "non_profit_organization",
        "zaprísaná úžitková vlastníctvo": "registered_leasehold",
    }

    # Registration statuses
    REGISTRATION_STATUSES = {
        "zapísaná": "registered",
        "vymazaná": "deleted",
        "pozastavená": "suspended",
        "zrušená": "cancelled",
    }

    def __init__(self, enable_snapshots: bool = True):
        """Initialize IVES Slovak scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=IVES_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search NGO by ICO.

        Args:
            ico: Slovak entity identification number (8 digits)

        Returns:
            Dictionary with NGO data or None if not found
        """
        self.logger.info(f"Searching IVES RMNO by ICO: {ico}")

        # Clean ICO
        ico = re.sub(r'[^\d]', '', ico)

        if not re.match(r'^\d{8}$', ico):
            self.logger.warning(f"Invalid ICO format: {ico}")
            return None

        try:
            # Try API endpoint if available
            api_url = f"{self.SEARCH_URL}/api/organizations/{ico}"

            try:
                response = self.http_client.get(api_url, headers={"Accept": "application/json"})
                if response.status_code == 200:
                    data = response.json()
                    if self.enable_snapshots:
                        self.save_snapshot(data, ico, self.SOURCE_NAME)
                    return self._parse_response(data, ico)
            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

            # Fallback to web scraping (may not work due to JS)
            return self._search_by_id_web(ico)

        except Exception as e:
            self.logger.error(f"Error searching IVES for {ico}: {e}")
            return self._get_mock_data(ico)

    def _search_by_id_web(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by ICO using web scraping (fallback).

        Note: The RMNO website uses client-side rendering with JavaScript.
        Simple HTTP requests may not return the complete content.

        Args:
            ico: Entity identification number

        Returns:
            Parsed NGO data or mock data
        """
        try:
            # The website likely requires JavaScript rendering
            # For now, return mock data
            return self._get_mock_data(ico)
        except Exception as e:
            self.logger.debug(f"Web scraping failed: {e}")
            return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search NGOs by name.

        Args:
            name: NGO name to search for

        Returns:
            List of matching NGOs
        """
        self.logger.info(f"Searching IVES RMNO by name: {name}")

        try:
            # Try API endpoint
            api_url = f"{self.SEARCH_URL}/api/search"
            params = {"name": name}

            try:
                response = self.http_client.get(api_url, params=params, headers={"Accept": "application/json"})
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    return [self._parse_response(r, r.get("ico")) for r in results if r.get("ico")]
            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error})

        except Exception as e:
            self.logger.error(f"Error searching IVES for {name}: {e}")

        return []

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Optional[Dict[str, Any]]:
        """Parse API response into unified format.

        Args:
            data: Raw API response
            ico: Entity ICO

        Returns:
            Unified output dictionary
        """
        try:
            ico_val = data.get("ico") or data.get("identificationNumber") or ico
            name = data.get("name") or data.get("nazov") or data.get("obchodneMeno")
            ngo_type = data.get("ngoType") or data.get("typOrganizacie")
            address_data = data.get("address") or data.get("adresa")

            # Parse address
            address = None
            if address_data:
                address = Address(
                    street=address_data.get("street") or address_data.get("ulica"),
                    city=address_data.get("city") or address_data.get("obec"),
                    postal_code=address_data.get("postalCode") or address_data.get("psc"),
                    country="Slovenská republika",
                    country_code="SK",
                    full_address=address_data.get("full") or address_data.get("cela"),
                )

            # Build entity
            entity = Entity(
                ico_registry=str(ico_val),
                company_name_registry=name,
                status=normalize_status(data.get("status") or "active"),
                registered_address=address,
            )

            # Build NGO-specific info
            ngo_info = {
                "ngo_type": self._normalize_ngo_type(ngo_type),
                "ngo_type_original": ngo_type,
                "registration_date": data.get("registrationDate") or data.get("datumZapisu"),
                "court": data.get("court") or data.get("sud"),
                "file_number": data.get("fileNumber") or data.get("znacka"),
                "scope_of_activities": data.get("scope") or data.get("cinnost"),
                "registered_general_benefits": data.get("generalBenefits") or [],
            }

            # Build metadata
            register_url = f"{self.SEARCH_URL}?ico={ico_val}"
            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=register_url,
                retrieved_at=get_retrieved_at(),
                is_mock=False,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                tax_info=None,
                metadata=metadata,
            )

            result = output.to_dict()
            result["ngo_info"] = ngo_info
            return result

        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            return None

    def _normalize_ngo_type(self, ngo_type: Optional[str]) -> Optional[str]:
        """Normalize NGO type to standard value.

        Args:
            ngo_type: Original NGO type string

        Returns:
            Normalized NGO type
        """
        if not ngo_type:
            return None

        ngo_type_lower = ngo_type.lower().strip()
        return self.NGO_TYPES.get(ngo_type_lower, "other")

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known NGOs.

        Args:
            ico: Entity identification number

        Returns:
            Unified output with mock data or None
        """
        mock_data = {
            "00123456": {
                "name": "Example Civic Association",
                "ico": "00123456",
                "ngo_type": "občianske združenie",
                "registration_date": "2010-05-15",
                "court": "Okresný súd Bratislava I",
                "file_number": "OZ-123/2010",
                "address": {
                    "street": "Example Street 123",
                    "city": "Bratislava",
                    "postal_code": "811 01",
                    "full": "Example Street 123, 811 01 Bratislava",
                },
            },
            "00223456": {
                "name": "Example Foundation",
                "ico": "00223456",
                "ngo_type": "nadácia",
                "registration_date": "2015-03-01",
                "court": "Okresný súd Bratislava I",
                "file_number": "N-456/2015",
                "address": {
                    "street": "Foundation Street 456",
                    "city": "Bratislava",
                    "postal_code": "811 02",
                    "full": "Foundation Street 456, 811 02 Bratislava",
                },
            },
        }

        if ico not in mock_data:
            return None

        data = mock_data[ico]

        # Build entity
        entity = Entity(
            ico_registry=data["ico"],
            company_name_registry=data["name"],
            status="active",
            registered_address=Address(
                street=data["address"].get("street"),
                city=data["address"].get("city"),
                postal_code=data["address"].get("postal_code"),
                country="Slovenská republika",
                country_code="SK",
                full_address=data["address"].get("full"),
            ),
        )

        # Build NGO info
        ngo_info = {
            "ngo_type": self._normalize_ngo_type(data["ngo_type"]),
            "ngo_type_original": data["ngo_type"],
            "registration_date": data["registration_date"],
            "court": data["court"],
            "file_number": data["file_number"],
        }

        # Build metadata
        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=f"{self.SEARCH_URL}?ico={data['ico']}",
            retrieved_at=get_retrieved_at(),
            is_mock=True,
        )

        output = UnifiedOutput(
            entity=entity,
            holders=[],
            tax_info=None,
            metadata=metadata,
        )

        result = output.to_dict()
        result["ngo_info"] = ngo_info
        return result

    def get_ngo_types(self) -> Dict[str, str]:
        """Get available NGO type mappings.

        Returns:
            Dictionary of NGO type names to normalized values
        """
        return self.NGO_TYPES.copy()

    def get_registration_info(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get detailed registration information for an NGO.

        Args:
            ico: Entity identification number

        Returns:
            Detailed registration info or None
        """
        result = self.search_by_id(ico)
        if result:
            return {
                "ico": ico,
                "name": result.get("entity", {}).get("company_name_registry"),
                "ngo_info": result.get("ngo_info"),
                "metadata": result.get("metadata"),
            }
        return None

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in IVES output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="ives")
