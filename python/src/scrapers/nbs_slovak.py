"""
NBS Slovak Scraper - National Bank of Slovakia - Financial Entities Register
Website: https://subjekty.nbs.sk

This scraper retrieves information about financial entities supervised by the
National Bank of Slovakia (banks, insurance companies, payment institutions, etc.).

The website is JavaScript-heavy and may require Selenium for full functionality.

Output format: UnifiedOutput with entity, regulatory_info, and metadata sections.
"""

import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, Metadata,
    normalize_status, get_register_name, get_retrieved_at
)
from config.constants import (
    NBS_BASE_URL, NBS_SEARCH_URL, NBS_RATE_LIMIT,
    NBS_OUTPUT_DIR, NBS_ENTITY_URL_TEMPLATE
)


class NbsSlovakScraper(BaseScraper):
    """Scraper for National Bank of Slovakia Financial Entities Register.

    Provides access to information about:
    - Banks and banking institutions
    - Insurance companies
    - Payment institutions
    - Electronic money institutions
    - Investment firms
    - Pension funds
    - Leasing companies

    Note: The website is JavaScript-heavy. This implementation provides mock data
    and a framework for future Selenium-based implementation.

    Example:
        scraper = NbsSlovakScraper()

        # Get financial entity data
        data = scraper.search_by_id("35763491")
        print(data.get('regulatory_info'))
    """

    BASE_URL = NBS_BASE_URL
    SEARCH_URL = NBS_BASE_URL
    SOURCE_NAME = "NBS_SK"

    # Entity types from NBS register
    ENTITY_TYPES = {
        "bank": "Banka",
        "pobocka": "Pobočka zahraničnej banky",
        "poisťovňa": "Poistovňa",
        "poisťovací agent": "Poistovací agent",
        "zaisťovateľ": "Zaistovateľ",
        "distribútor": "Distribútor poisťovacích produktov",
        "penzijný fond": "Penzijný fond",
        "správca dôchodkového fondu": "Správca dôchodkového fondu",
        "investičná spoločnosť": "Investičná spoločnosť",
        "správca aktív": "Správca aktív",
        "obchodník s cennými papiermi": "Obchodník s cennými papiermi",
        "platobná inštitúcia": "Platobná inštitúcia",
        "inštitúcia elektronických peňazí": "Inštitúcia elektronických peňazí",
        "zmenárenský servis": "Zmenárenský servis",
        "leasingová spoločnosť": "Leasingová spoločnosť",
        "nebankový poskytovateľ úverov": "Nebankový poskytovateľ úverov",
        "prevádzkovateľ bounding systému": "Prevádzkovateľ bounding systému",
        "inzercny agent": "Inzercný agent",
        "sprostredkovateľ": "Sprostredkovateľ",
    }

    def __init__(self, enable_snapshots: bool = True):
        """Initialize NBS Slovak scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=NBS_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search financial entity by ICO.

        Args:
            ico: Slovak company identification number (8 digits)

        Returns:
            Dictionary with entity and regulatory data or None if not found
        """
        self.logger.info(f"Searching NBS by ICO: {ico}")

        # Clean ICO
        ico = re.sub(r'[^\d]', '', ico)

        if not re.match(r'^\d{8}$', ico):
            self.logger.warning(f"Invalid ICO format: {ico}")
            return None

        try:
            # NBS website requires JavaScript, try API endpoint if available
            api_url = f"{NBS_SEARCH_URL}/api/subject/{ico}"

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
            self.logger.error(f"Error searching NBS for {ico}: {e}")
            return self._get_mock_data(ico)

    def _search_by_id_web(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by ICO using web scraping (fallback).

        Note: This may not work as the NBS website is JavaScript-heavy.

        Args:
            ico: Company identification number

        Returns:
            Parsed entity data or mock data
        """
        try:
            # The website likely uses client-side rendering
            # Return mock data for known entities
            return self._get_mock_data(ico)
        except Exception as e:
            self.logger.debug(f"Web scraping failed: {e}")
            return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search financial entities by name.

        Args:
            name: Entity name or partial name to search for

        Returns:
            List of matching entities
        """
        self.logger.info(f"Searching NBS by name: {name}")

        try:
            # Try API endpoint first
            api_url = f"{NBS_SEARCH_URL}/api/search"
            params = {"name": name}

            try:
                response = self.http_client.get(api_url, params=params, headers={"Accept": "application/json"})
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    return [self._parse_response(r, r.get("ico")) for r in results if r.get("ico")]
            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

        except Exception as e:
            self.logger.error(f"Error searching NBS for {name}: {e}")

        return []

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Optional[Dict[str, Any]]:
        """Parse API response into unified format.

        Args:
            data: Raw API response
            ico: Original ICO

        Returns:
            Unified output dictionary
        """
        try:
            ico_val = data.get("ico") or data.get("ico") or ico
            name = data.get("name") or data.get("nazov") or data.get("obchodneMeno")
            legal_form = data.get("legalForm") or data.get("pravnaForma")
            entity_type = data.get("entityType") or data.get("typSubjektu")

            # Build entity
            entity = Entity(
                ico_registry=str(ico_val),
                company_name_registry=name,
                legal_form=legal_form,
                status="active",
            )

            # Build regulatory info
            regulatory_info = {
                "entity_type": entity_type,
                "license_number": data.get("licenseNumber") or data.get("cisloLicencie"),
                "supervision_status": data.get("supervisionStatus") or data.get("statusDozoru"),
                "nace_codes": data.get("naceCodes") or data.get("naciez"),
                "registration_date": data.get("registrationDate") or data.get("datumRegistracie"),
            }

            # Build metadata
            register_url = f"{self.BASE_URL}/subject/{ico_val}"
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
            result["regulatory_info"] = regulatory_info
            return result

        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            return None

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known financial entities.

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary with mock data or None
        """
        mock_data = {
            "35763491": {
                "name": "Slovenská sporiteľňa, a.s.",
                "ico": "35763491",
                "legal_form": "Akciová spoločnosť",
                "entity_type": "bank",
                "license_number": "NBS-B-001/2008",
                "supervision_status": "active",
                "nace_codes": ["64.19"],
                "registration_date": "1991-12-20",
                "address": {
                    "street": "Tomášikova 48",
                    "city": "Bratislava",
                    "postal_code": "832 01",
                    "country": "Slovenská republika",
                },
            },
            "31328356": {
                "name": "Všeobecná úverová banka, a.s.",
                "ico": "31328356",
                "legal_form": "Akciová spoločnosť",
                "entity_type": "bank",
                "license_number": "NBS-B-002/1991",
                "supervision_status": "active",
                "nace_codes": ["64.19"],
                "registration_date": "1991-12-20",
                "address": {
                    "street": "Mlynské nivy 1",
                    "city": "Bratislava",
                    "postal_code": "829 11",
                    "country": "Slovenská republika",
                },
            },
            "44103755": {
                "name": "Slovak Telekom, a.s.",
                "ico": "44103755",
                "legal_form": "Akciová spoločnosť",
                "entity_type": None,  # Not a financial entity per NBS
                "license_number": None,
                "supervision_status": "not_regulated",
            },
        }

        if ico not in mock_data:
            return None

        data = mock_data[ico]

        # Build entity
        entity = Entity(
            ico_registry=data["ico"],
            company_name_registry=data["name"],
            legal_form=data.get("legal_form"),
            status="active" if data.get("supervision_status") == "active" else "inactive",
        )

        # Build regulatory info
        regulatory_info = {
            "entity_type": data.get("entity_type"),
            "license_number": data.get("license_number"),
            "supervision_status": data.get("supervision_status"),
            "nace_codes": data.get("nace_codes"),
            "registration_date": data.get("registration_date"),
        }

        # Build address
        address = None
        if data.get("address"):
            addr = data["address"]
            address = Address(
                street=addr.get("street"),
                city=addr.get("city"),
                postal_code=addr.get("postal_code"),
                country=addr.get("country"),
                country_code="SK",
                full_address=f"{addr.get('street', '')}, {addr.get('postal_code', '')} {addr.get('city', '')}".strip(", "),
            )

        # Build metadata
        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=f"{self.BASE_URL}/subject/{data['ico']}",
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
        result["regulatory_info"] = regulatory_info
        if address:
            result["entity"]["registered_address"] = address.to_dict()

        return result

    def get_bank_list(self) -> List[Dict[str, Any]]:
        """Get list of all banks registered in Slovakia.

        Returns:
            List of bank entities
        """
        try:
            api_url = f"{NBS_SEARCH_URL}/api/banks"
            response = self.http_client.get(api_url, headers={"Accept": "application/json"})
            if response.status_code == 200:
                data = response.json()
                return data.get("banks", [])
        except Exception as e:
            self.logger.error(f"Error fetching bank list: {e}")

        return []

    def get_insurance_companies(self) -> List[Dict[str, Any]]:
        """Get list of all insurance companies registered in Slovakia.

        Returns:
            List of insurance entities
        """
        try:
            api_url = f"{NBS_SEARCH_URL}/api/insurance"
            response = self.http_client.get(api_url, headers={"Accept": "application/json"})
            if response.status_code == 200:
                data = response.json()
                return data.get("companies", [])
        except Exception as e:
            self.logger.error(f"Error fetching insurance list: {e}")

        return []

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in NBS output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="nbs")
