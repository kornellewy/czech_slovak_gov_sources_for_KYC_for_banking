"""
ARES Czech Scraper - Register of Economic Subjects
API Documentation: https://ares.gov.cz/swagger-ui/

This scraper uses the official ARES REST API to retrieve information
about Czech economic subjects (companies, entrepreneurs, etc.).

Output format: UnifiedOutput with entity, holders, tax_info, and metadata sections.
"""

from typing import Optional, Dict, Any, List

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, TaxDebts, Metadata,
    parse_address, normalize_status, normalize_country_code,
    get_register_name, get_retrieved_at, detect_holder_type, normalize_role
)
from config.constants import ARES_BASE_URL, ARES_RATE_LIMIT, ARES_ENTITY_URL_TEMPLATE, ARES_OUTPUT_DIR


class ARESCzechScraper(BaseScraper):
    """Scraper for the Czech ARES (Register of Economic Subjects) API.

    The ARES API provides comprehensive information about Czech companies
    including identification data, address, legal form, and registration details.

    Example:
        scraper = ARESCzechScraper()

        # Search by IČO
        company = scraper.search_by_id("00006947")
        print(company['name'])  # "Ministerstvo financí"

        # Search by name
        companies = scraper.search_by_name("Agrofert")
        for c in companies:
            print(f"{c['name']} - {c['ico']}")

        # Save results
        scraper.save_to_json(company, "ministry_finance.json")
    """

    BASE_URL = ARES_BASE_URL
    SOURCE_NAME = "ARES_CZ"

    def __init__(self, enable_snapshots: bool = True):
        """Initialize ARES Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=ARES_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search company by IČO (identification number).

        Args:
            ico: Czech company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        self.logger.info(f"Searching ARES by IČO: {ico}")

        # ARES API uses path parameter: /ekonomicke-subjekty/{ico}
        url = f"{self.BASE_URL}/{ico.strip()}"

        try:
            response = self.http_client.get(url)
            data = response.json()

            # Check for error response
            if "kod" in data and data["kod"] != "OK":
                self.logger.warning(f"No entity found with IČO: {ico} - {data.get('popis', 'Unknown error')}")
                return None

            # Save snapshot if enabled
            if self.enable_snapshots:
                self.save_snapshot(data, ico, self.SOURCE_NAME)

            # Parse and standardize response
            return self._parse_response(data)

        except Exception as e:
            self.logger.error(f"Error searching ARES for {ico}: {e}")
            return None

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search companies by name.

        Note: ARES API does not support name search via the standard endpoint.
        This method returns an empty list with a warning.

        Args:
            name: Company name to search for

        Returns:
            Empty list (not supported by ARES API)
        """
        self.logger.warning("ARES API does not support name search. Use IČO search instead.")
        return []

    def _parse_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse ARES API response into unified format.

        Args:
            data: Raw API response

        Returns:
            Unified output dictionary with entity, holders, tax_info, metadata
        """
        ico = data.get("ico", "")

        # Parse address
        sidlo = data.get("sidlo", {})
        address = None
        if sidlo:
            address = Address(
                street=sidlo.get("nazevUlice"),
                city=sidlo.get("nazevObce"),
                postal_code=str(sidlo.get("psc")) if sidlo.get("psc") else None,
                country=sidlo.get("nazevStatu"),
                country_code=normalize_country_code(sidlo.get("nazevStatu")),
                full_address=self._build_full_address(sidlo)
            )

        # Extract legal form
        legal_form = data.get("pravniForma")
        legal_form_code = data.get("pravniFormaKod")

        # Extract NACE codes
        nace_codes = data.get("czNace2008", []) or data.get("czNace", [])

        # Build entity
        entity = Entity(
            ico_registry=ico,
            company_name_registry=data.get("obchodniJmeno"),
            legal_form=legal_form,
            legal_form_code=legal_form_code,
            status="active",  # ARES entities are active by default
            registered_address=address,
            nace_codes=nace_codes if nace_codes else None,
            vat_id=data.get("dic"),
            tax_id=data.get("dic"),
        )

        # Extract tax information
        reg_list = data.get("seznamRegistraci", {})
        vat_status = None
        if reg_list:
            vat_registered = reg_list.get("dph", "ne") == "ano"
            vat_status = "active" if vat_registered else "inactive"

        tax_info = TaxInfo(
            vat_id=data.get("dic"),
            vat_status=vat_status,
            tax_id=data.get("dic"),
        )

        # Build metadata
        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=ARES_ENTITY_URL_TEMPLATE.format(ico=ico),
            retrieved_at=get_retrieved_at(),
            is_mock=False,
        )

        # Create unified output
        output = UnifiedOutput(
            entity=entity,
            holders=[],  # ARES doesn't provide holder information
            tax_info=tax_info,
            metadata=metadata,
        )

        return output.to_dict()

    def _build_full_address(self, sidlo: Dict[str, Any]) -> str:
        """Build full address string from address components.

        Args:
            sidlo: Address data from ARES

        Returns:
            Full address string
        """
        parts = []

        # Street and numbers
        street = sidlo.get("nazevUlice", "")
        house_num = sidlo.get("cisloDomovni", "")
        orient_num = sidlo.get("cisloOrientacni", "")

        if street:
            street_part = street
            if house_num:
                street_part += f" {house_num}"
                if orient_num:
                    street_part += f"/{orient_num}"
            parts.append(street_part)
        elif house_num:
            parts.append(str(house_num))

        # Postal code and city
        psc = sidlo.get("psc", "")
        city = sidlo.get("nazevObce", "")

        if psc:
            psc_str = str(psc)
            formatted_psc = f"{psc_str[:3]} {psc_str[3:]}" if len(psc_str) == 5 else psc_str
            if city:
                parts.append(f"{formatted_psc} {city}")
            else:
                parts.append(formatted_psc)
        elif city:
            parts.append(city)

        return ", ".join(parts)

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in ARES output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="ares")
