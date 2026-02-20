"""
RES Czech Scraper - Resident Income Tax Register (Rezidentní daň z příjmů)
Website: https://adisepo.financnispraha.cz

This scraper retrieves resident income tax information from the
Czech Tax Administration's database.

The RES register contains:
- Resident tax status
- Income tax registration
- Tax residency information
- Related tax obligations

Output format: UnifiedOutput with entity, tax_info, and metadata sections.
"""

import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, TaxInfo, Metadata,
    parse_address, normalize_status, get_register_name, get_retrieved_at
)
from config.constants import (
    RES_BASE_URL, RES_SEARCH_URL, RES_RATE_LIMIT,
    RES_OUTPUT_DIR, RES_ENTITY_URL_TEMPLATE
)


class ResCzechScraper(BaseScraper):
    """Scraper for Czech Resident Income Tax Register (Rezidentní daň z příjmů).

    Provides access to resident tax information including:
    - Tax residency status
    - Income tax registration
    - Tax identification information

    The information is available via the Czech Tax Administration's database.

    Example:
        scraper = ResCzechScraper()

        # Search by ICO
        data = scraper.search_by_id("05984866")
        print(data.get('tax_info'))

        # Check tax residency
        status = scraper.check_tax_residency("05984866")
    """

    BASE_URL = RES_BASE_URL
    SEARCH_URL = RES_SEARCH_URL
    SOURCE_NAME = "RES_CZ"

    def __init__(self, enable_snapshots: bool = True):
        """Initialize RES Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=RES_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Search tax residency by ICO.

        Args:
            identifier: Czech company ICO (8 digits)

        Returns:
            Dictionary with tax data or None if not found
        """
        self.logger.info(f"Searching RES register for: {identifier}")

        identifier = identifier.strip()

        # Validate ICO format
        if not re.match(r'^\d{8}$', identifier):
            self.logger.warning(f"Invalid ICO format: {identifier}")
            return None

        try:
            # Try API endpoint first
            url = f"{self.BASE_URL}/dpf/z/zoznam"

            try:
                params = {"ico": identifier}
                response = self.http_client.get(url, params=params, headers={"Accept": "application/json"})

                if response.status_code == 200:
                    data = response.json()
                    if self.enable_snapshots:
                        self.save_snapshot(data, identifier, self.SOURCE_NAME)

                    # Check if data was returned
                    if data and not isinstance(data, dict) or data.get('results') or data.get('value'):
                        return self._parse_response(data, identifier)
            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

            # Fallback to web scraping
            return self._search_by_web(identifier)

        except Exception as e:
            self.logger.error(f"Error searching RES for {identifier}: {e}")
            return self._get_mock_data(identifier)

    def _search_by_web(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search tax residency by ICO using web scraping.

        Args:
            ico: Company ICO

        Returns:
            Unified output dictionary with tax info
        """
        try:
            # RES database search page
            url = f"{self.BASE_URL}/dpf/z/zoznam"
            params = {"ico": ico}

            html = self.http_client.get_html(url, params=params)
            soup = BeautifulSoup(html, 'lxml')

            # Parse results for tax residency status
            is_tax_resident = False
            tax_residency_status = "unknown"

            # Look for tax residency indicators
            page_text = soup.get_text().lower()

            if "rezident" in page_text or "resident" in page_text:
                is_tax_resident = True
                tax_residency_status = "resident"
            elif "nerezident" in page_text or "non-resident" in page_text:
                is_tax_resident = False
                tax_residency_status = "non_resident"

            # Look for entity name
            entity_name = None
            title = soup.find('h1') or soup.find('title')
            if title:
                entity_name = title.get_text(strip=True)

            # Build entity
            entity = Entity(
                ico_registry=ico,
                company_name_registry=entity_name or f"Entity {ico}",
            )

            # Build tax info
            tax_info = TaxInfo(
                tax_id=ico,
            )

            # Add residency status as additional field
            if tax_residency_status != "unknown":
                tax_info_dict = tax_info.to_dict()
                tax_info_dict['tax_residency_status'] = tax_residency_status
                tax_info_dict['is_tax_resident'] = is_tax_resident

            # Build metadata
            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{self.BASE_URL}/dpf/z/zoznam?ico={ico}",
                retrieved_at=get_retrieved_at(),
                is_mock=False,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                tax_info=tax_info,
                metadata=metadata,
            )

            return output.to_dict()

        except Exception as e:
            self.logger.debug(f"Web scraping failed: {e}")
            return self._get_mock_data(ico)

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Optional[Dict[str, Any]]:
        """Parse API response into unified format.

        Args:
            data: Raw API response
            ico: Company ICO

        Returns:
            Unified output dictionary
        """
        try:
            # Extract tax residency status
            tax_residency_status = "unknown"
            is_tax_resident = False

            # Check various possible response formats
            results = data.get('results') or data.get('value') or []
            if not results and isinstance(data, list):
                results = data

            entity_data = results[0] if results else {}

            if entity_data.get('jeRezident') or entity_data.get('isResident'):
                is_tax_resident = True
                tax_residency_status = "resident"
            elif entity_data.get('jeRezident') is False or entity_data.get('isResident') is False:
                is_tax_resident = False
                tax_residency_status = "non_resident"

            # Get entity name
            name = entity_data.get("obchodniJmeno") or entity_data.get("nazev") or entity_data.get("name")

            # Build entity
            entity = Entity(
                ico_registry=ico,
                company_name_registry=name,
            )

            # Build tax info
            tax_info = TaxInfo(
                tax_id=ico,
            )

            # Add residency status
            tax_info_dict = tax_info.to_dict()
            if tax_residency_status != "unknown":
                tax_info_dict['tax_residency_status'] = tax_residency_status
                tax_info_dict['is_tax_resident'] = is_tax_resident

            # Build metadata
            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{self.BASE_URL}/dpf/z/zoznam?ico={ico}",
                retrieved_at=get_retrieved_at(),
                is_mock=False,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                metadata=metadata,
            )

            result = output.to_dict()
            result['tax_info'] = tax_info_dict

            return result

        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            return None

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search tax residency by company name.

        Args:
            name: Company name to search for

        Returns:
            List of matching entities
        """
        self.logger.info(f"Searching RES by name: {name}")

        try:
            params = {"nazev": name}
            html = self.http_client.get_html(self.SEARCH_URL, params=params)
            soup = BeautifulSoup(html, 'lxml')

            results = []
            # Parse result table
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        # Try to extract ICO
                        ico_match = re.search(r'\d{8}', cells[1].get_text())
                        if ico_match:
                            ico = ico_match.group(0)
                            result = self.search_by_id(ico)
                            if result:
                                results.append(result)

            return results[:10]  # Limit results

        except Exception as e:
            self.logger.error(f"Error searching RES for {name}: {e}")
            return []

    def check_tax_residency(self, ico: str) -> Dict[str, Any]:
        """Check if entity is a tax resident.

        Args:
            ico: Company ICO

        Returns:
            Dictionary with residency status
        """
        result = self.search_by_id(ico)

        tax_info = result.get('tax_info', {}) if result else {}

        return {
            "ico": ico,
            "is_tax_resident": tax_info.get('is_tax_resident', False),
            "tax_residency_status": tax_info.get('tax_residency_status', 'unknown'),
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
                "is_tax_resident": True,
                "tax_residency_status": "resident",
            },
            "00006947": {
                "ico": "00006947",
                "name": "Ministerstvo financí",
                "is_tax_resident": True,
                "tax_residency_status": "resident",
            },
            "06649114": {
                "ico": "06649114",
                "name": "Prusa Research a.s.",
                "is_tax_resident": True,
                "tax_residency_status": "resident",
            },
        }

        if identifier in mock_data:
            data = mock_data[identifier]

            entity = Entity(
                ico_registry=data["ico"],
                company_name_registry=data["name"],
                status="active",
            )

            tax_info = TaxInfo(
                tax_id=data["ico"],
            )
            tax_info_dict = tax_info.to_dict()
            tax_info_dict['tax_residency_status'] = data['tax_residency_status']
            tax_info_dict['is_tax_resident'] = data['is_tax_resident']

            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{self.BASE_URL}/dpf/z/zoznam?ico={data['ico']}",
                retrieved_at=get_retrieved_at(),
                is_mock=True,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                metadata=metadata,
            )

            result = output.to_dict()
            result['tax_info'] = tax_info_dict

            return result

        return None

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in RES output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="res")
