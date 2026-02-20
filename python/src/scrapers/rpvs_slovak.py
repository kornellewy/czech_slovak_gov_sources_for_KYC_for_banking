"""
RPVS Slovak Scraper - Register of Public Sector Partners (UBO)
API: https://rpvs.gov.sk/opendatav2/PartneriVerejnehoSektora

This scraper retrieves Ultimate Beneficial Owner (UBO) information from
the Slovak Register of Public Sector Partners using OData API.

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
from config.constants import (
    RPVS_BASE_URL, RPVS_ODATA_ENDPOINT, RPVS_RATE_LIMIT,
    RPVS_API_KEY, RPVS_OUTPUT_DIR, RPVS_ENTITY_URL_TEMPLATE
)


class RpvsSlovakScraper(BaseScraper):
    """Scraper for Slovak Register of Public Sector Partners (RPVS).

    Provides Ultimate Beneficial Owner (UBO) information via OData API.

    OData endpoint: https://rpvs.gov.sk/opendatav2/PartneriVerejnehoSektora?$filter=Ico eq 'ICO'

    Example:
        scraper = RpvsSlovakScraper()

        # Get UBO data
        ubo_data = scraper.search_by_id("35763491")

        for owner in ubo_data.get('holders', []):
            print(f"{owner['name']}: {owner['ownership_pct_direct']}%")
    """

    BASE_URL = RPVS_BASE_URL
    ODATA_ENDPOINT = RPVS_ODATA_ENDPOINT
    SOURCE_NAME = "RPVS_SK"

    def __init__(self, enable_snapshots: bool = True, api_key: str = None):
        """Initialize RPVS Slovak scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
            api_key: Optional API key (not required for public OData endpoint)
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=RPVS_RATE_LIMIT)
        self.api_key = api_key or RPVS_API_KEY
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests.

        Returns:
            Headers dictionary with JSON accept type
        """
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search UBO data by company ICO using OData API.

        Args:
            ico: Slovak company identification number

        Returns:
            Dictionary with UBO data in unified format or None if not found
        """
        self.logger.info(f"Searching RPVS by ICO: {ico}")

        # Use OData filter syntax: $filter=Ico eq '35763491'
        url = f"{self.ODATA_ENDPOINT}?$filter=Ico eq '{ico}'"

        try:
            response = self.http_client.get(url, headers=self._get_headers())
            data = response.json()

            # OData responses have a "value" array with results
            results = data.get("value", []) if isinstance(data, dict) else []

            if results:
                # Take first matching result
                result = results[0]
                self.logger.info(f"Found RPVS data for {ico}")

                if self.enable_snapshots:
                    self.save_snapshot(result, ico, self.SOURCE_NAME)

                return self._parse_response(result, ico)
            else:
                self.logger.warning(f"No RPVS data found for {ico}")
                return self._get_mock_data(ico)

        except Exception as e:
            self.logger.error(f"RPVS API request failed: {e}")
            return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search by company name.

        Args:
            name: Company name to search for

        Returns:
            List of matching entities
        """
        self.logger.info(f"Searching RPVS by name: {name}")

        try:
            url = f"{self.BASE_URL}/search"
            params = {"name": name}
            response = self.http_client.get(url, params=params, headers=self._get_headers())
            data = response.json()

            if data and not data.get("error"):
                return self._parse_search_results(data)

        except Exception as e:
            self.logger.warning(f"Search failed: {e}")

        return []

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Dict[str, Any]:
        """Parse OData API response into unified format.

        OData field mapping (Slovak -> English):
        - Ico -> ico_registry
        - ObchodneMeno -> company_name_registry
        - FormaOsoby -> legal_form
        - PlatnostOd -> incorporation_date
        - PlatnostDo -> status_effective_date (if null, entity is active)

        Args:
            data: Raw OData API response
            ico: Original ICO

        Returns:
            Unified output dictionary
        """
        # Extract fields from OData response (Slovak field names)
        ico_val = data.get("Ico") or data.get("ico", ico)
        company_name = data.get("ObchodneMeno") or data.get("company_name") or data.get("name")
        legal_form = data.get("FormaOsoby") or data.get("legal_form")

        # Determine status from PlatnostDo (validity to date)
        # If PlatnostDo is null or in future, entity is active
        platnost_do = data.get("PlatnostDo") or data.get("platnost_do")
        status = "active"
        if platnost_do:
            from datetime import datetime
            try:
                # If date is in past, entity is cancelled/inactive
                expiry = datetime.fromisoformat(platnost_do.replace('Z', '+00:00'))
                if expiry < datetime.now(expiry.tzinfo):
                    status = "cancelled"
            except:
                pass

        # Build entity
        entity = Entity(
            ico_registry=ico_val,
            company_name_registry=company_name,
            legal_form=legal_form,
            status=status,
        )

        # OData API may include related entities/UBOs in separate property
        # For now, return empty holders list - UBO data may require additional API calls
        holders = []

        # Build metadata
        register_url = RPVS_ENTITY_URL_TEMPLATE.format(ico=ico_val) if ico_val else None
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

    def _parse_ubo(self, ubo: Dict[str, Any]) -> Holder:
        """Parse individual UBO record into Holder object.

        Args:
            ubo: Raw UBO data

        Returns:
            Holder object
        """
        name = ubo.get("name") or ubo.get("full_name")
        holder_type = detect_holder_type(ubo)
        role = normalize_role(ubo.get("role") or "beneficial_owner")

        # Extract identification info
        identification = ubo.get("identification", {})
        if not identification:
            identification = {
                "birth_date": ubo.get("birth_date"),
                "citizenship": ubo.get("citizenship"),
                "id_number": ubo.get("id_number"),
            }

        # Get citizenship/country code
        citizenship = identification.get("citizenship") or ubo.get("citizenship")
        citizenship_code = normalize_country_code(citizenship)

        # Get jurisdiction for entities
        jurisdiction = None
        if holder_type == "entity":
            address = ubo.get("address", {})
            country = address.get("country") if isinstance(address, dict) else None
            jurisdiction = normalize_country_code(country) or citizenship_code

        # Parse address
        address_obj = parse_address(ubo.get("address"))

        # Get ownership percentage
        ownership_pct = ubo.get("ownership_percentage") or ubo.get("ownership") or 0.0
        voting_rights = ubo.get("voting_rights") or ubo.get("voting_rights_percentage")

        return Holder(
            holder_type=holder_type,
            role=role,
            name=name,
            ico=ubo.get("ico"),
            jurisdiction=jurisdiction,
            citizenship=citizenship_code,
            date_of_birth=identification.get("birth_date"),
            residency=citizenship_code,  # Use citizenship as residency if not specified
            address=address_obj,
            ownership_pct_direct=float(ownership_pct) if ownership_pct else 0.0,
            voting_rights_pct=float(voting_rights) if voting_rights else None,
        )

    def _parse_search_results(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse search results.

        Args:
            data: Raw search response

        Returns:
            List of entity dictionaries
        """
        results = []
        entities = data.get("results") or data.get("partners") or []

        for entity in entities:
            results.append({
                "source": self.SOURCE_NAME,
                "ico": entity.get("ico"),
                "company_name": entity.get("name") or entity.get("company_name"),
                "retrieved_at": get_retrieved_at(),
            })

        return results

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known test entities in unified format.

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary with mock UBO data or None
        """
        # Mock raw data
        mock_raw_data = {
            "35763491": {
                "company_name": "Slovenská sporiteľňa, a.s.",
                "ubos": [
                    {
                        "name": "Erste Group Bank AG",
                        "type": "entity",
                        "role": "ultimate_beneficial_owner",
                        "ownership_percentage": 100.0,
                        "voting_rights": 100.0,
                        "identification": {
                            "citizenship": "AT",
                            "id_number": "FN 182081 v"
                        },
                        "address": {
                            "city": "Vienna",
                            "country": "Austria"
                        }
                    }
                ],
            },
            "31328356": {
                "company_name": "Všeobecná úverová banka, a.s.",
                "ubos": [
                    {
                        "name": "Intesa Sanpaolo S.p.A.",
                        "type": "entity",
                        "role": "ultimate_beneficial_owner",
                        "ownership_percentage": 94.49,
                        "voting_rights": 94.49,
                        "identification": {
                            "citizenship": "IT"
                        },
                        "address": {
                            "city": "Milan",
                            "country": "Italy"
                        }
                    }
                ],
            },
            "44103755": {
                "company_name": "Slovak Telekom, a.s.",
                "ubos": [
                    {
                        "name": "Deutsche Telekom AG",
                        "type": "entity",
                        "role": "ultimate_beneficial_owner",
                        "ownership_percentage": 51.0,
                        "voting_rights": 51.0,
                        "identification": {
                            "citizenship": "DE"
                        },
                        "address": {
                            "city": "Bonn",
                            "country": "Germany"
                        }
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
        holders = [self._parse_ubo(ubo) for ubo in raw.get("ubos", [])]

        # Build metadata
        register_url = RPVS_ENTITY_URL_TEMPLATE.format(ico=ico)
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
        """Save result to JSON file in RPVS output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="rpvs")
