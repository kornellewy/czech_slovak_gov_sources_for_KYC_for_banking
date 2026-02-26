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
        self.log_info(f"{self.SOURCE_NAME} scraper ready (rate limit: {ARES_RATE_LIMIT} req/min)")

    def search_by_id(self, ico: str, include_subsource: bool = False) -> Optional[Dict[str, Any]]:
        """Search company by IČO (identification number).

        Args:
            ico: Czech company identification number (8 digits)
            include_subsource: Whether to include sub-source registration details

        Returns:
            Dictionary with company data or None if not found
        """
        self.log_search_start(identifier=ico.strip(), search_type="by_ICO")

        # ARES API uses path parameter: /ekonomicke-subjekty/{ico}
        url = f"{self.BASE_URL}/{ico.strip()}"

        try:
            import time
            start = time.time()
            response = self.http_client.get(url)
            duration_ms = (time.time() - start) * 1000

            data = response.json()

            # Log response
            self.log_response(url, response.status_code, duration_ms)

            # Check for error response
            if "kod" in data and data["kod"] != "OK":
                error_msg = data.get('popis', 'Unknown error')
                self.log_warning(f"No entity found with IČO: {ico} - {error_msg}")
                return None

            self.log_info(f"Found entity for IČO: {ico} - {data.get('obchodniJmeno', 'Unknown')}", extra={'ico': ico})

            # Save snapshot if enabled
            if self.enable_snapshots:
                self.save_snapshot(data, ico, self.SOURCE_NAME)

            # Parse and standardize response
            self.log_parse_start("ARES_API")
            result = self._parse_response(data)

            # Add sub-source information if requested
            if include_subsource and result:
                self.log_debug("Extracting sub-source data")
                result["subsource"] = self._extract_subsource(data)
                active_count = result["subsource"]["active_count"]
                self.log_info(f"Sub-sources: {active_count} active registries")

            self.log_parse_complete("ARES_API", items_found=1)
            self.log_search_complete(results_count=1, identifier=ico)

            return result

        except Exception as e:
            self.log_error("search_by_id", e, ico=ico)
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

    def _extract_subsource(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract sub-source registration information from ARES response.

        ARES includes data from multiple sub-registries (RZP, ROS, VR, RES, DPH, etc.)
        embedded in the main response via seznamRegistraci and dalsiUdaje.

        Args:
            data: Raw ARES API response

        Returns:
            Dictionary with sub-source information
        """
        subsource = {
            "registrations": {},
            "additional_data": {},
            "active_count": 0
        }

        # Extract seznamRegistraci (sub-source statuses)
        registrace = data.get("seznamRegistraci", {})
        for key, value in registrace.items():
            # Remove 'stavZdroje' prefix for cleaner keys
            clean_key = key.replace("stavZdroje", "")
            subsource["registrations"][clean_key] = {
                "status": value,  # AKTIVNI, NEEXISTUJICI, HISTORICKY
                "is_active": value == "AKTIVNI"
            }

            if value == "AKTIVNI":
                subsource["active_count"] += 1

        # Extract dalsiUdaje (detailed data from sub-sources)
        dalsi = data.get("dalsiUdaje", [])
        for source_data in dalsi:
            source = source_data.get("datovyZdroj", "")

            if source:
                extracted = {}

                # Extract key fields from this source
                for key, value in source_data.items():
                    if key == "datovyZdroj":
                        continue

                    elif key == "obchodniJmeno" and isinstance(value, list) and value:
                        name_data = value[0]
                        if isinstance(name_data, dict):
                            extracted["company_name"] = name_data.get("obchodniJmeno")

                    elif key == "sidlo" and isinstance(value, list) and value:
                        address_data = value[0]
                        if isinstance(address_data, dict) and "sidlo" in address_data:
                            sidlo = address_data["sidlo"]
                            if isinstance(sidlo, dict):
                                extracted["address"] = {
                                    "street": sidlo.get("nazevUlice"),
                                    "city": sidlo.get("nazevObce"),
                                    "postal_code": str(sidlo.get("psc")) if sidlo.get("psc") else None,
                                    "country": sidlo.get("nazevStatu"),
                                }

                    elif key == "spisovaZnacka":
                        extracted["file_reference"] = value

                    elif key == "pravniForma":
                        extracted["legal_form"] = value

                    elif key == "datumZapisu":
                        extracted["registration_date"] = value

                    elif key == "datumVymazu":
                        extracted["deletion_date"] = value

                if extracted:
                    subsource["additional_data"][source] = extracted

        # Add specific sub-source fields
        if "pravniFormaRos" in data:
            subsource["ros_legal_form"] = data.get("pravniFormaRos")

        return subsource
