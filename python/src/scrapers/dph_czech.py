"""
DPH Czech Scraper - VAT Register (Registr plátců DPH)
Website: https://adisepo.financnispraha.cz

This scraper retrieves VAT (Value Added Tax) registration information from the
Czech Tax Administration's public database.

The DPH register contains:
- VAT payer status
- DIC (VAT ID) information
- Tax registration dates
- Bankruptcy/insolvency status related to taxes

Output format: UnifiedOutput with entity, tax_info, and metadata sections.
"""

import re
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, TaxInfo, TaxDebts, Metadata,
    parse_address, normalize_status, get_register_name, get_retrieved_at
)
from config.constants import (
    DPH_BASE_URL, DPH_SEARCH_URL, DPH_RATE_LIMIT,
    DPH_OUTPUT_DIR, DPH_ENTITY_URL_TEMPLATE
)


class DphCzechScraper(BaseScraper):
    """Scraper for Czech VAT Register (Registr plátců DPH).

    Provides access to VAT payer information including:
    - DIC (VAT ID) validation
    - VAT payer status (active/inactive)
    - Tax registration information
    - Bankruptcy/insolvency status

    The information is available via the Czech Tax Administration's public database.

    Example:
        scraper = DphCzechScraper()

        # Search by DIC (VAT ID)
        data = scraper.search_by_id("CZ05984866")
        print(data.get('tax_info'))

        # Search by ICO (returns DIC if found)
        data = scraper.search_by_id("05984866")
        print(data.get('tax_info'))
    """

    BASE_URL = DPH_BASE_URL
    SEARCH_URL = f"{DPH_BASE_URL}/dpf/hledani"
    SOURCE_NAME = "DPH_CZ"

    def __init__(self, enable_snapshots: bool = True):
        """Initialize DPH Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=DPH_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Search VAT payer by ICO or DIC (VAT ID).

        Args:
            identifier: Czech company ICO (8 digits) or DIC (VAT ID)

        Returns:
            Dictionary with tax data or None if not found
        """
        self.logger.info(f"Searching DPH register for: {identifier}")

        # Determine if input is ICO or DIC
        identifier = identifier.strip()

        # If ICO, need to find DIC first
        ico = None
        dic = None

        if re.match(r'^CZ\d{8,}$', identifier, re.IGNORECASE):
            # Input is DIC (VAT ID)
            dic = identifier.upper()
            ico = re.sub(r'^CZ0*', '', identifier)
        elif re.match(r'^\d{8}$', identifier):
            # Input is ICO, need to get DIC
            ico = identifier
            dic = f"CZ{identifier}" if len(identifier) == 8 else f"CZ{identifier:0>8}"
        else:
            self.logger.warning(f"Invalid identifier format: {identifier}")
            return None

        try:
            # Try API endpoint for DIC lookup
            url = f"{DPH_BASE_URL}/dpf/pslovnik/dic/{dic}"

            try:
                response = self.http_client.get(url, headers={"Accept": "application/json"})
                if response.status_code == 200:
                    data = response.json()
                    if self.enable_snapshots:
                        self.save_snapshot(data, identifier, self.SOURCE_NAME)
                    return self._parse_response(data, ico, dic)
            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

            # Fallback to web scraping
            return self._search_by_dic_web(dic, ico)

        except Exception as e:
            self.logger.error(f"Error searching DPH for {identifier}: {e}")
            return self._get_mock_data(identifier)

    def _search_by_dic_web(self, dic: str, ico: str) -> Optional[Dict[str, Any]]:
        """Search VAT payer by DIC using web scraping (fallback).

        Args:
            dic: VAT ID (e.g., CZ05984866)
            ico: Company ICO

        Returns:
            Unified output dictionary with tax info
        """
        try:
            # The DPH database has a public search form
            url = f"{DPH_BASE_URL}/dpf/hledani"
            params = {"dic": dic}

            html = self.http_client.get_html(url, params=params)
            soup = BeautifulSoup(html, 'lxml')

            # Parse results for VAT status
            is_vat_payer = False
            vat_status = "unknown"
            registration_date = None

            # Look for VAT payer indicators
            page_text = soup.get_text().lower()

            if "plátce dph" in page_text or "registrovaný plátce" in page_text:
                is_vat_payer = True
                vat_status = "active"
            elif "neregistrovaný" in page_text or "neplátce" in page_text:
                is_vat_payer = False
                vat_status = "inactive"

            # Look for entity name
            entity_name = None
            title = soup.find('h1') or soup.find('title')
            if title:
                entity_name = title.get_text(strip=True)

            # Build tax info
            tax_info = TaxInfo(
                vat_id=dic,
                vat_status=vat_status,
                tax_id=ico,
            )

            # Build entity
            entity = Entity(
                ico_registry=ico or "",
                company_name_registry=entity_name or f"Entity {ico}",
            )

            # Build metadata
            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{DPH_BASE_URL}/dpf/hledani?dic={dic}",
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
            return self._get_mock_data(ico or dic)

    def _parse_response(self, data: Dict[str, Any], ico: str, dic: str) -> Optional[Dict[str, Any]]:
        """Parse API response into unified format.

        Args:
            data: Raw API response
            ico: Company ICO
            dic: VAT ID

        Returns:
            Unified output dictionary
        """
        try:
            # Extract VAT status from response
            vat_status = "unknown"
            if data.get("jePlatce"):
                vat_status = "active" if data["jePlatce"] else "inactive"
            elif data.get("platceDPH"):
                vat_status = "active" if data["platceDPH"] else "inactive"

            # Get entity name
            name = data.get("obchodniJmeno") or data.get("nazev") or data.get("name")

            # Build entity
            entity = Entity(
                ico_registry=ico,
                company_name_registry=name,
            )

            # Build tax info
            tax_info = TaxInfo(
                vat_id=dic,
                vat_status=vat_status,
                tax_id=ico,
            )

            # Build metadata
            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{DPH_BASE_URL}/dpf/hledani?dic={dic}",
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
            self.logger.error(f"Error parsing response: {e}")
            return None

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search VAT payer by company name.

        Args:
            name: Company name to search for

        Returns:
            List of matching entities
        """
        self.logger.info(f"Searching DPH by name: {name}")

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
                    if len(cells) >= 3:
                        # Try to extract DIC and name
                        dic = None
                        for cell in cells:
                            text = cell.get_text(strip=True)
                            dic_match = re.search(r'CZ\d{8}', text)
                            if dic_match:
                                dic = dic_match.group(0)
                                break

                        if dic:
                            result = self.search_by_id(dic)
                            if result:
                                results.append(result)

            return results[:10]  # Limit results

        except Exception as e:
            self.logger.error(f"Error searching DPH for {name}: {e}")
            return []

    def check_vat_number(self, dic: str) -> Dict[str, Any]:
        """Check if a VAT number is valid and active.

        Args:
            dic: VAT ID (e.g., CZ05984866)

        Returns:
            Dictionary with validation result
        """
        result = self.search_by_id(dic)

        return {
            "dic": dic,
            "is_valid": result is not None,
            "is_vat_payer": result.get("tax_info", {}).get("vat_status") == "active" if result else False,
            "source": self.SOURCE_NAME,
        }

    def _get_mock_data(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known entities.

        Args:
            identifier: ICO or DIC

        Returns:
            Unified output with mock data or None
        """
        mock_data = {
            "05984866": {
                "dic": "CZ05984866",
                "ico": "05984866",
                "name": "DEVROCK a.s.",
                "vat_status": "active",
                "registration_date": "2017-04-03",
            },
            "06649114": {
                "dic": "CZ06649114",
                "ico": "06649114",
                "name": "Prusa Research a.s.",
                "vat_status": "active",
            },
            "00006947": {
                "dic": "CZ00006947",
                "ico": "00006947",
                "name": "Ministerstvo financí",
                "vat_status": "active",
            },
        }

        # Check by ICO or DIC
        key = None
        if identifier in mock_data:
            key = identifier
        else:
            # Try without CZ prefix for DIC
            dic_without_cz = re.sub(r'^CZ', '', identifier)
            if f"CZ{identifier:0>8}" in mock_data:
                key = f"CZ{identifier:0>8}"
            elif dic_without_cz in mock_data:
                key = dic_without_cz

        if key and key in mock_data:
            data = mock_data[key]

            entity = Entity(
                ico_registry=data["ico"],
                company_name_registry=data["name"],
                status="active",
            )

            tax_info = TaxInfo(
                vat_id=data["dic"],
                vat_status=data["vat_status"],
                tax_id=data["ico"],
            )

            metadata = Metadata(
                source=self.SOURCE_NAME,
                register_name=get_register_name(self.SOURCE_NAME),
                register_url=f"{DPH_BASE_URL}/dpf/hledani?dic={data['dic']}",
                retrieved_at=get_retrieved_at(),
                is_mock=True,
            )

            output = UnifiedOutput(
                entity=entity,
                holders=[],
                tax_info=tax_info,
                metadata=metadata,
            )

            return output.to_dict()

        return None

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in DPH output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="dph")
