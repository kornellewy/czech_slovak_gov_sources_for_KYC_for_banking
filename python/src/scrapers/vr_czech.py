"""
VR Czech Scraper - Vermont Register (Register oddělovaných nemovitostí)
Website: https://rpvs.gov.cz

This scraper retrieves information about separated real estate properties
from the Czech Vermont Register (part of RPVS - Register veřejných sektorů).

The Vermont register contains:
- Separated real estate properties
- Property ownership information
- Property details and addresses

Output format: UnifiedOutput with entity, property_info, and metadata sections.
"""

import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, TaxInfo, Metadata, Address,
    parse_address, normalize_status, get_register_name, get_retrieved_at
)
from config.constants import (
    VR_BASE_URL, VR_ODATA_ENDPOINT, VR_RATE_LIMIT,
    VR_OUTPUT_DIR, VR_ENTITY_URL_TEMPLATE
)


class VrCzechScraper(BaseScraper):
    """Scraper for Czech Vermont Register (Register oddělovaných nemovitostí).

    Provides access to separated real estate information including:
    - Property ownership details
    - Property addresses and descriptions
    - Legal ownership information

    The information is available via the RPVS OData API.

    Example:
        scraper = VrCzechScraper()

        # Search by ICO (company properties)
        data = scraper.search_by_id("05984866")
        print(data.get('property_info'))

        # Search by owner name
        results = scraper.search_by_name("Jan Novák")
    """

    BASE_URL = VR_BASE_URL
    ODATA_ENDPOINT = VR_ODATA_ENDPOINT
    SOURCE_NAME = "VR_CZ"

    def __init__(self, enable_snapshots: bool = True):
        """Initialize VR Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=VR_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Search properties by ICO.

        Args:
            identifier: Czech company ICO (8 digits)

        Returns:
            Dictionary with property data or None if not found
        """
        self.logger.info(f"Searching VR register for: {identifier}")

        identifier = identifier.strip()

        # Validate ICO format
        if not re.match(r'^\d{8}$', identifier):
            self.logger.warning(f"Invalid ICO format: {identifier}")
            return None

        try:
            # Try OData endpoint first
            # The Vermont register uses OData format
            url = f"{self.BASE_URL}/openapi/v2/DssvzdyOvlastena"

            try:
                # Try filtering by ICO if supported
                filter_query = f"Ico eq '{identifier}'"
                full_url = f"{url}?$filter={quote(filter_query)}"

                response = self.http_client.get(full_url, headers={"Accept": "application/json"})
                if response.status_code == 200:
                    data = response.json()
                    if self.enable_snapshots:
                        self.save_snapshot(data, identifier, self.SOURCE_NAME)

                    # Parse OData response
                    if 'value' in data and len(data['value']) > 0:
                        return self._parse_odata_response(data['value'][0], identifier)
                    elif data.get('d'):
                        # Another OData format
                        results = data['d'].get('results', []) if isinstance(data['d'], dict) else []
                        if results:
                            return self._parse_odata_response(results[0], identifier)
            except Exception as api_error:
                self.logger.debug(f"OData request failed: {api_error}")

            # Fallback to web scraping
            return self._search_by_web(identifier)

        except Exception as e:
            self.logger.error(f"Error searching VR for {identifier}: {e}")
            return self._get_mock_data(identifier)

    def _search_by_web(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search properties by ICO using web scraping.

        Args:
            ico: Company ICO

        Returns:
            Unified output dictionary with property info
        """
        try:
            # Vermont register search page
            url = f"{self.BASE_URL}/cs/verejne-sektory"

            html = self.http_client.get_html(url)
            soup = BeautifulSoup(html, 'lxml')

            # Look for property information
            # The Vermont register is part of RPVS
            property_count = 0
            properties = []

            # Try to find property listings
            property_tables = soup.find_all('table', class_=re.compile('property|nemovitost'))
            for table in property_tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        properties.append({
                            'description': cells[0].get_text(strip=True),
                            'address': cells[1].get_text(strip=True)
                        })
                        property_count += 1

            # Build entity
            entity = Entity(
                ico_registry=ico,
                company_name_registry=f"Entity {ico}",
            )

            # Build property info
            property_info = {
                'property_count': property_count,
                'properties': properties
            }

            # Build metadata
            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=url,
                retrieved_at=get_retrieved_at(),
                is_mock=False,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                metadata=metadata,
            )

            result = output.to_dict()
            if property_count > 0:
                result['property_info'] = property_info

            return result

        except Exception as e:
            self.logger.debug(f"Web scraping failed: {e}")
            return self._get_mock_data(ico)

    def _parse_odata_response(self, data: Dict[str, Any], ico: str) -> Optional[Dict[str, Any]]:
        """Parse OData response into unified format.

        Args:
            data: Raw OData response item
            ico: Company ICO

        Returns:
            Unified output dictionary
        """
        try:
            # Extract property information
            properties = []
            property_count = 0

            # Check for property-related fields
            if 'nemovitosti' in data:
                properties = data['nemovitosti']
                property_count = len(properties)
            elif 'Properties' in data:
                properties = data['Properties']
                property_count = len(properties)

            # Get entity name
            name = data.get("nazev") or data.get("obchodniJmeno") or data.get("name")

            # Build entity
            entity = Entity(
                ico_registry=ico,
                company_name_registry=name,
            )

            # Build metadata
            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{self.BASE_URL}/openapi/v2/DssvzdyOvlastena?ico={ico}",
                retrieved_at=get_retrieved_at(),
                is_mock=False,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                metadata=metadata,
            )

            result = output.to_dict()
            if property_count > 0:
                result['property_info'] = {
                    'property_count': property_count,
                    'properties': properties
                }

            return result

        except Exception as e:
            self.logger.error(f"Error parsing OData response: {e}")
            return None

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search properties by owner name.

        Args:
            name: Owner name to search for

        Returns:
            List of matching properties
        """
        self.logger.info(f"Searching VR by name: {name}")

        try:
            # Use OData endpoint with name filter
            url = self.ODATA_ENDPOINT

            # URL encode the name parameter
            encoded_name = quote(name)

            try:
                response = self.http_client.get(
                    f"{url}?meno={encoded_name}",
                    headers={"Accept": "application/json"}
                )

                if response.status_code == 200:
                    data = response.json()

                    results = []
                    if 'value' in data:
                        for item in data['value'][:10]:  # Limit results
                            ico = item.get('Ico') or item.get('ico')
                            if ico:
                                parsed = self._parse_odata_response(item, ico)
                                if parsed:
                                    results.append(parsed)
                    elif data.get('d', {}).get('results'):
                        for item in data['d']['results'][:10]:
                            ico = item.get('Ico') or item.get('ico')
                            if ico:
                                parsed = self._parse_odata_response(item, ico)
                                if parsed:
                                    results.append(parsed)

                    return results

            except Exception as api_error:
                self.logger.debug(f"OData name search failed: {api_error}")

            # Fallback: return mock data
            return []

        except Exception as e:
            self.logger.error(f"Error searching VR for {name}: {e}")
            return []

    def check_property_ownership(self, ico: str) -> Dict[str, Any]:
        """Check if entity owns separated real estate.

        Args:
            ico: Company ICO

        Returns:
            Dictionary with ownership status
        """
        result = self.search_by_id(ico)

        property_info = result.get('property_info', {}) if result else {}
        property_count = property_info.get('property_count', 0)

        return {
            "ico": ico,
            "has_properties": property_count > 0,
            "property_count": property_count,
            "source": self.SOURCE_NAME,
        }

    def _get_mock_data(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known entities.

        Args:
            identifier: ICO

        Returns:
            Unified output with mock data or None
        """
        mock_data = {
            "05984866": {
                "ico": "05984866",
                "name": "DEVROCK a.s.",
                "properties": [],
                "property_count": 0,
                "notes": "No separated real estate found in Vermont register"
            },
            "00006947": {
                "ico": "00006947",
                "name": "Ministerstvo financí",
                "properties": [
                    {
                        "description": "Government building",
                        "address": "Letenská 10, Praha 1"
                    }
                ],
                "property_count": 1,
            },
        }

        if identifier in mock_data:
            data = mock_data[identifier]

            entity = Entity(
                ico_registry=data["ico"],
                company_name_registry=data["name"],
                status="active",
            )

            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{self.BASE_URL}/openapi/v2/DssvzdyOvlastena?ico={data['ico']}",
                retrieved_at=get_retrieved_at(),
                is_mock=True,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                metadata=metadata,
            )

            result = output.to_dict()
            result['property_info'] = {
                'property_count': data.get('property_count', 0),
                'properties': data.get('properties', [])
            }

            return result

        return None

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in VR output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="vr")
