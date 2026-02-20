"""
ESM Czech Scraper - Register of Beneficial Owners
Website: https://issm.justice.cz

IMPORTANT: This API is RESTRICTED and requires AML certification.
This implementation is a PLACEHOLDER for demonstration purposes only.

Access to the ESM register is limited to:
- Notaries
- Banks and financial institutions
- Auditors
- Tax advisors
- Other AML-obligated persons

Output format: UnifiedOutput with entity, holders, tax_info, and metadata sections.
"""

import os
from typing import Optional, Dict, Any, List

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, Metadata,
    parse_address, normalize_status, normalize_country_code,
    get_register_name, get_retrieved_at, detect_holder_type, normalize_role
)
from config.constants import ESM_BASE_URL, ESM_RATE_LIMIT, ESM_API_KEY, ESM_OUTPUT_DIR, ESM_ENTITY_URL_TEMPLATE


class EsmCzechScraper(BaseScraper):
    """Scraper for Czech Register of Beneficial Owners (ESM).

    IMPORTANT: This is a PLACEHOLDER implementation. The actual ESM API
    requires AML certification and is not publicly accessible.

    For access requirements, see: https://issm.justice.cz

    Example:
        scraper = EsmCzechScraper()

        # This will return mock data only
        ubo_data = scraper.search_by_id("06649114")

        # Check access requirements
        requirements = scraper.get_access_requirements()
    """

    BASE_URL = ESM_BASE_URL
    SOURCE_NAME = "ESM_CZ"

    ACCESS_REQUIREMENTS = {
        "qualification": "AML obligated person (bank, notary, auditor, etc.)",
        "registration": "Required registration at issm.justice.cz",
        "api_key": "API key required for access",
        "website": "https://issm.justice.cz",
        "legal_basis": "Zákon o evidenci skutečných majitelů"
    }

    def __init__(self, enable_snapshots: bool = True, api_key: str = None):
        """Initialize ESM Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
            api_key: API key for ESM access (requires AML certification)
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=ESM_RATE_LIMIT)
        self.api_key = api_key or ESM_API_KEY
        self.logger.warning(
            f"Initialized {self.SOURCE_NAME} scraper - PLACEHOLDER MODE. "
            "ESM requires AML certification for access."
        )

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search beneficial owners by company IČO.

        Note: Returns mock data unless valid API key is provided.

        Args:
            ico: Czech company identification number

        Returns:
            Dictionary with beneficial owner data or mock data
        """
        self.logger.info(f"Getting beneficial owners for IČO: {ico}")

        # Without API key, return mock data only
        if not self.api_key:
            self.logger.warning("No API key provided - returning mock data")
            return self._get_mock_data(ico)

        # Try API call with API key
        try:
            url = f"{self.BASE_URL}/ubo/{ico}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            response = self.http_client.get(url, headers=headers)
            data = response.json()

            if data and not data.get("error"):
                if self.enable_snapshots:
                    self.save_snapshot(data, ico, self.SOURCE_NAME)
                return self._parse_response(data, ico)

        except Exception as e:
            self.logger.error(f"API call failed: {e}")

        # Fall back to mock data
        return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search by company name (not supported).

        Args:
            name: Company name

        Returns:
            Empty list
        """
        self.logger.warning("Name search not supported for ESM")
        return []

    def get_access_requirements(self) -> Dict[str, str]:
        """Get information about ESM access requirements.

        Returns:
            Dictionary with access requirement details
        """
        return self.ACCESS_REQUIREMENTS.copy()

    def check_compliance(self, ico: str) -> Optional[Dict[str, Any]]:
        """Check if a company has filed their beneficial owner declaration.

        Args:
            ico: Company identification number

        Returns:
            Compliance status dictionary
        """
        ubo_data = self.search_by_id(ico)
        if not ubo_data:
            return None

        beneficial_owners = ubo_data.get("beneficial_owners", [])

        return {
            "source": self.SOURCE_NAME,
            "ico": ico,
            "has_filed": ubo_data.get("has_filed", True),
            "filing_date": ubo_data.get("filing_date"),
            "beneficial_owners_count": len(beneficial_owners),
            "compliance_status": "compliant" if ubo_data.get("has_filed", True) else "non_compliant",
            "note": "Mock data - actual compliance check requires API access",
            "mock": True,
            "retrieved_at": get_retrieved_at()
        }

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Dict[str, Any]:
        """Parse API response into unified format.

        Args:
            data: Raw API response
            ico: Original ICO

        Returns:
            Unified output dictionary
        """
        ico_val = data.get("ico", ico)
        company_name = data.get("company_name") or data.get("obchodni_jmeno")

        # Build entity
        entity = Entity(
            ico_registry=ico_val,
            company_name_registry=company_name,
        )

        # Parse holders/UBOs
        owners_data = data.get("beneficial_owners") or data.get("skutecni_majitele") or []
        holders = [self._parse_owner(o) for o in owners_data]

        # Build metadata
        register_url = ESM_ENTITY_URL_TEMPLATE.format(ico=ico_val) if ico_val else None
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
            holders=holders,
            tax_info=None,
            metadata=metadata,
        )

        return output.to_dict()

    def _parse_owner(self, owner: Dict[str, Any]) -> Holder:
        """Parse individual beneficial owner record into Holder object.

        Args:
            owner: Raw owner data

        Returns:
            Holder object
        """
        name = owner.get("name") or owner.get("jmeno")
        holder_type = detect_holder_type(owner)
        role = normalize_role(owner.get("role") or "beneficial_owner")

        # Get citizenship/country code
        citizenship = owner.get("citizenship") or owner.get("statni_prislusnost")
        citizenship_code = normalize_country_code(citizenship)

        # Get jurisdiction for entities
        jurisdiction = None
        if holder_type == "entity":
            address = owner.get("address") or owner.get("bydliste")
            if isinstance(address, dict):
                country = address.get("country")
                jurisdiction = normalize_country_code(country) or citizenship_code

        # Parse address
        address_data = owner.get("address") or owner.get("bydliste")
        address_obj = parse_address(address_data)

        # Get ownership percentage
        ownership_pct = owner.get("ownership_percentage") or owner.get("podil") or 0.0
        voting_rights = owner.get("voting_rights") or owner.get("hlasovaci_prava")

        return Holder(
            holder_type=holder_type,
            role=role,
            name=name,
            jurisdiction=jurisdiction,
            citizenship=citizenship_code,
            date_of_birth=owner.get("birth_date") or owner.get("datum_narozeni"),
            residency=citizenship_code,
            address=address_obj,
            ownership_pct_direct=float(ownership_pct) if ownership_pct else 0.0,
            voting_rights_pct=float(voting_rights) if voting_rights else None,
        )

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known test entities in unified format.

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary with mock UBO data or None
        """
        # Mock raw data
        mock_raw_data = {
            "06649114": {
                "company_name": "Prusa Research a.s.",
                "filing_date": "2021-06-01",
                "beneficial_owners": [
                    {
                        "name": "Josef Průša",
                        "type": "individual",
                        "role": "beneficial_owner",
                        "ownership_percentage": 100.0,
                        "voting_rights": 100.0,
                        "birth_date": "1990-05-24",
                        "citizenship": "CZ",
                        "address": {
                            "city": "Praha",
                            "country": "Česká republika",
                            "country_code": "CZ",
                        }
                    }
                ],
            },
            "00216305": {
                "company_name": "Česká pošta, s.p.",
                "filing_date": "2021-06-15",
                "beneficial_owners": [
                    {
                        "name": "Česká republika",
                        "type": "entity",
                        "role": "beneficial_owner",
                        "ownership_percentage": 100.0,
                        "voting_rights": 100.0,
                        "citizenship": "CZ",
                    }
                ],
            },
            "00006947": {
                "company_name": "Ministerstvo financí",
                "filing_date": "2021-06-01",
                "beneficial_owners": [
                    {
                        "name": "Česká republika",
                        "type": "entity",
                        "role": "beneficial_owner",
                        "ownership_percentage": 100.0,
                    }
                ],
            }
        }

        if ico not in mock_raw_data:
            return None

        raw = mock_raw_data[ico]

        # Build entity
        entity = Entity(
            ico_registry=ico,
            company_name_registry=raw.get("company_name"),
        )

        # Parse holders
        holders = [self._parse_owner(ubo) for ubo in raw.get("beneficial_owners", [])]

        # Build metadata
        register_url = ESM_ENTITY_URL_TEMPLATE.format(ico=ico)
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
            holders=holders,
            tax_info=None,
            metadata=metadata,
        )

        return output.to_dict()

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in ESM output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="esm")
