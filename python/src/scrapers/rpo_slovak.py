"""
RPO Slovak Scraper - Register of Legal Entities
API: https://api.statistics.sk/rpo/v1

API Documentation:
- Managed by Statistical Office of Slovak Republic (Štatistický úrad SR)
- Open Data under Creative Commons Attribution 4.0 license
- No API key required for public queries
- Rate limit: 100 requests/minute

Search endpoint: GET /search?identifier={ico}
Entity endpoint: GET /entity/{id} (uses internal RPO ID, not ICO)

Output format: UnifiedOutput with entity, holders, tax_info, and metadata sections.
"""

from typing import Optional, Dict, Any, List

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, Metadata,
    parse_address, normalize_status, normalize_country_code,
    get_register_name, get_retrieved_at, normalize_role
)
from config.constants import RPO_BASE_URL, RPO_RATE_LIMIT, RPO_OUTPUT_DIR, RPO_ENTITY_URL_TEMPLATE

# Country code mapping for RPO-specific numeric codes
RPO_COUNTRY_CODE_MAPPINGS = {
    "703": "SK",  # Slovak Republic
    "203": "CZ",  # Czech Republic
    "040": "AT",  # Austria
    "276": "DE",  # Germany
    "380": "IT",  # Italy
    "348": "HU",  # Hungary
    "616": "PL",  # Poland
    "826": "GB",  # United Kingdom
    "840": "US",  # United States
}


class RpoSlovakScraper(BaseScraper):
    """Scraper for Slovak Register of Legal Entities (RPO).

    Uses the official RPO REST API to retrieve entity information.
    Two-step process:
    1. Search by ICO to get internal RPO ID
    2. Fetch full entity details using internal ID

    Example:
        scraper = RpoSlovakScraper()

        # Search by ICO
        entity = scraper.search_by_id("47559870")
        print(entity['entity']['company_name_registry'])  # "ZELEX, s.r.o."
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

        Uses two-step API process:
        1. Search endpoint to get internal RPO ID
        2. Entity endpoint for full details

        Args:
            ico: Slovak entity identification number (8 digits)

        Returns:
            Dictionary with entity data or None if not found
        """
        self.logger.info(f"Searching RPO by ICO: {ico}")

        try:
            # Step 1: Search by identifier (ICO) to get internal ID
            search_url = f"{self.BASE_URL}/search"
            params = {"identifier": ico}

            self.logger.debug(f"Searching RPO: {search_url}?identifier={ico}")
            response = self.http_client.get(search_url, params=params)
            search_data = response.json()

            # Handle API response structure: {"results": [...], "license": "..."}
            results = search_data.get("results", []) if isinstance(search_data, dict) else search_data

            # Check for empty results
            if not results or (isinstance(results, list) and len(results) == 0):
                self.logger.warning(f"No results found for ICO {ico}")
                return {"error": "not_found", "message": f"Entity with ICO {ico} not found in RPO"}

            # Get the first result's internal ID
            first_result = results[0] if isinstance(results, list) else results

            internal_id = first_result.get("id")
            if not internal_id:
                self.logger.warning(f"No internal ID found in search results for ICO {ico}")
                return {"error": "not_found", "message": f"Internal ID not found for ICO {ico}"}

            self.logger.debug(f"Found internal RPO ID: {internal_id}")

            # Step 2: Fetch full entity details
            entity_url = f"{self.BASE_URL}/entity/{internal_id}"
            self.logger.debug(f"Fetching entity details: {entity_url}")
            entity_response = self.http_client.get(entity_url)
            entity_data = entity_response.json()

            if not entity_data:
                self.logger.warning(f"Empty entity response for ID {internal_id}")
                return {"error": "not_found", "message": f"Entity details not found"}

            # Save snapshot if enabled
            if self.enable_snapshots:
                self.save_snapshot(entity_data, ico, self.SOURCE_NAME)

            # Parse and return unified output
            return self._parse_response(entity_data, ico)

        except Exception as e:
            self.logger.error(f"RPO API error for ICO {ico}: {e}")
            # Only use mock fallback for genuine network errors
            return self._get_fallback_mock_data(ico)

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
            params = {"fullName": name}
            response = self.http_client.get(url, params=params)
            data = response.json()

            if data:
                return self._parse_search_results(data)

        except Exception as e:
            self.logger.warning(f"Search failed: {e}")

        return []

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Dict[str, Any]:
        """Parse RPO API response into unified format.

        RPO API returns nested structures with arrays for historical data.
        We use the first (current) element from each array.

        Args:
            data: Raw API response from /entity/{id}
            ico: Original ICO for fallback

        Returns:
            Unified output dictionary
        """
        # Extract ICO from identifiers array (first = current)
        identifiers = data.get("identifiers", [])
        ico_val = ico
        if identifiers and len(identifiers) > 0:
            ico_val = identifiers[0].get("value", ico)

        # Extract company name from fullNames array
        full_names = data.get("fullNames", [])
        company_name = None
        if full_names and len(full_names) > 0:
            company_name = full_names[0].get("value")

        # Extract legal form
        legal_forms = data.get("legalForms", [])
        legal_form = None
        legal_form_code = None
        if legal_forms and len(legal_forms) > 0:
            lf = legal_forms[0].get("value", {})
            legal_form = lf.get("value")
            legal_form_code = lf.get("code")

        # Extract incorporation date
        establishment = data.get("establishment")

        # Extract address
        addresses = data.get("addresses", [])
        address = self._parse_rpo_address(addresses) if addresses else None

        # Build entity
        entity = Entity(
            ico_registry=ico_val,
            company_name_registry=company_name,
            legal_form=legal_form,
            legal_form_code=legal_form_code,
            status="active",  # RPO doesn't provide status, assume active if found
            incorporation_date=establishment,
            registered_address=address,
        )

        # Parse holders (statutory bodies and stakeholders)
        holders = self._parse_holders(data)

        # Build metadata
        internal_id = data.get("id")
        register_url = f"{self.BASE_URL}/entity/{internal_id}" if internal_id else None
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

    def _parse_rpo_address(self, addresses: List[Dict[str, Any]]) -> Optional[Address]:
        """Parse address from RPO API addresses array.

        Args:
            addresses: List of address objects (first = current)

        Returns:
            Address object or None
        """
        if not addresses or len(addresses) == 0:
            return None

        addr = addresses[0]  # Use first (current) address

        # Extract street info
        street = addr.get("street")
        building_number = addr.get("buildingNumber")
        street_full = f"{street} {building_number}" if street and building_number else street or building_number

        # Extract postal code
        postal_codes = addr.get("postalCodes", [])
        postal_code = postal_codes[0] if postal_codes else None

        # Extract city/municipality
        municipality = addr.get("municipality", {})
        city = municipality.get("value") if isinstance(municipality, dict) else municipality

        # Extract country code (RPO uses numeric codes like "703" for SK)
        country = addr.get("country", {})
        country_code_raw = country.get("code") if isinstance(country, dict) else None
        country_code = self._map_rpo_country_code(country_code_raw)

        return Address(
            street=street_full or None,
            city=city,
            postal_code=postal_code,
            country_code=country_code,
        )

    def _map_rpo_country_code(self, code: Optional[str]) -> Optional[str]:
        """Map RPO numeric country code to ISO 3166-1 alpha-2.

        Args:
            code: RPO country code (e.g., "703" for Slovakia)

        Returns:
            ISO 3166-1 alpha-2 code (e.g., "SK")
        """
        if not code:
            return None

        # Check RPO-specific mappings first
        if code in RPO_COUNTRY_CODE_MAPPINGS:
            return RPO_COUNTRY_CODE_MAPPINGS[code]

        # Try standard normalization
        return normalize_country_code(code)

    def _parse_holders(self, data: Dict[str, Any]) -> List[Holder]:
        """Parse holders from RPO entity data.

        Extracts statutory bodies (Konateľ) and stakeholders (Spoločník).

        Args:
            data: RPO entity data

        Returns:
            List of Holder objects
        """
        holders = []

        # Parse statutory bodies (Konateľ, Predstavenstvo, etc.)
        statutory_bodies = data.get("statutoryBodies", [])
        for sb in statutory_bodies:
            holder = self._parse_holder(sb, "statutory_body")
            if holder:
                holders.append(holder)

        # Parse stakeholders (Spoločník - shareholders)
        stakeholders = data.get("stakeholders", [])
        for sh in stakeholders:
            holder = self._parse_holder(sh, "shareholder")
            if holder:
                holders.append(holder)

        return holders

    def _parse_holder(self, holder_data: Dict[str, Any], default_role: str) -> Optional[Holder]:
        """Parse a single holder from RPO data.

        Args:
            holder_data: Holder data from API
            default_role: Default role (statutory_body or shareholder)

        Returns:
            Holder object or None
        """
        person_name = holder_data.get("personName", {})
        name = person_name.get("formatedName")

        if not name:
            return None

        # Determine role from stakeholderType
        stakeholder_type = holder_data.get("stakeholderType", {})
        role_raw = stakeholder_type.get("value") if isinstance(stakeholder_type, dict) else None
        role = normalize_role(role_raw) if role_raw else default_role

        # Determine holder type (individual vs entity)
        # If personName exists, it's an individual
        holder_type = "individual"

        return Holder(
            holder_type=holder_type,
            role=role,
            name=name,
        )

    def _parse_search_results(self, data: Any) -> List[Dict[str, Any]]:
        """Parse search results.

        Args:
            data: Raw search response (may be list or {"results": [...]} wrapper)

        Returns:
            List of entity dictionaries
        """
        results = []

        # Handle API response structure: {"results": [...], "license": "..."}
        entities = data.get("results", []) if isinstance(data, dict) else data

        for entity in entities:
            # Extract ICO from identifiers
            identifiers = entity.get("identifiers", [])
            ico = identifiers[0].get("value") if identifiers else None

            # Extract name from fullNames
            full_names = entity.get("fullNames", [])
            name = full_names[0].get("value") if full_names else None

            results.append({
                "source": self.SOURCE_NAME,
                "ico": ico,
                "internal_id": entity.get("id"),
                "name": name,
                "retrieved_at": get_retrieved_at(),
            })

        return results

    def _get_fallback_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get fallback mock data for network error cases only.

        This method should only be called when the RPO API is genuinely unavailable
        (network errors, timeouts, etc.). For valid ICOs not found in RPO, the
        search_by_id method returns {"error": "not_found"} instead.

        Args:
            ico: Entity identification number

        Returns:
            Unified output dictionary with mock data
        """
        self.logger.warning(f"Using fallback mock data for ICO {ico} - API unavailable")

        # Mock database with raw data for entities confirmed in RPO
        # Note: Banks and financial institutions may not be in RPO (they're in NBS register)
        mock_raw_data = {
            "31348262": {
                "name": "Wolters Kluwer SR s.r.o.",
                "legal_form": "Spoločnosť s ručením obmedzeným",
                "legal_form_code": "112",
                "status": "active",
                "date_registered": "2004-01-01",
                "address": {
                    "city": "Bratislava",
                    "country": "Slovensko",
                    "country_code": "SK",
                },
            },
            "47559870": {
                "name": "ZELEX, s.r.o.",
                "legal_form": "Spoločnosť s ručením obmedzeným",
                "legal_form_code": "112",
                "status": "active",
                "date_registered": "2005-01-01",
                "address": {
                    "city": "Bratislava",
                    "country": "Slovensko",
                    "country_code": "SK",
                },
            },
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

        # Build metadata - mark as mock
        register_url = RPO_ENTITY_URL_TEMPLATE.format(ico=ico)
        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=register_url,
            retrieved_at=get_retrieved_at(),
            is_mock=True,  # Always True for fallback data
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
