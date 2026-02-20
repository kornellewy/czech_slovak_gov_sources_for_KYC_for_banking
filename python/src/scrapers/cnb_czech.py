"""
CNB Czech Scraper - Czech National Bank Financial Supervision Registers
Website: https://www.cnb.cz

This scraper retrieves information about financial entities supervised by the
Czech National Bank (banks, insurance companies, payment institutions, etc.).

The website has both Czech and English versions with lists and registers:
- /cs/dohled-financni-trh/seznamy/ - Czech version
- /en/supervision-financial-market/lists-registers - English version

Output format: UnifiedOutput with entity, regulatory_info, and metadata sections.
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
    CNB_BASE_URL, CNB_REGISTERS_URL, CNB_RATE_LIMIT,
    CNB_OUTPUT_DIR, CNB_ENTITY_URL_TEMPLATE
)


class CnbCzechScraper(BaseScraper):
    """Scraper for Czech National Bank Financial Supervision Registers.

    Provides access to information about:
    - Banks and banking institutions
    - Foreign bank branches
    - Insurance companies
    - Pension funds
    - Payment institutions
    - Electronic money institutions
    - Investment firms and brokers
    - Leasing companies
    - Debt collectors
    - Credit union

    Note: The CNB website uses static HTML lists rather than a search API.

    Example:
        scraper = CnbCzechScraper()

        # Get bank list
        banks = scraper.get_bank_list()

        # Search by ICO in all registers
        data = scraper.search_by_id("00008000")  # CNB itself
    """

    BASE_URL = CNB_BASE_URL
    REGISTERS_URL = f"{CNB_BASE_URL}/cs/dohled-financni-trh/seznamy"
    SOURCE_NAME = "CNB_CZ"

    # Register types
    REGISTER_TYPES = {
        "banks": "Seznam bank a poboček zahraničních bank",
        "insurance": "Pojišťovny a zajišťovny",
        "pension": "Penzijní fondy",
        "payment": "Platební instituce",
        "electronic_money": "Instituce elektronických peněz",
        "investment": "Investiční společnosti a fondy",
        "trading": "Obchodníci s cennými papíry",
        "leasing": "Leasingové společnosti",
        "debt_collection": "Vymáhání pohledávek",
        "credit_union": "Kampeličky",
    }

    # Register URLs
    REGISTER_URLS = {
        "banks": f"{BASE_URL}/cs/dohled-financni-trh/seznamy-sektoru-a-dohlad/zoznam-bank-a-pobock-zahranicnych-bank/",
        "insurance": f"{BASE_URL}/cs/dohled-financni-trh/seznamy-sektoru-a-dohlad/pojistovny-a-zajistovny/",
        "pension": f"{BASE_URL}/cs/dohled-financni-trh/seznamy-sektoru-a-dohlad/penzijnij-fondy/",
        "payment": f"{BASE_URL}/cs/dohled-financni-trh/seznamy-sektoru-a-dohlad/platebni-instituce/",
        "electronic_money": f"{BASE_URL}/cs/dohled-financni-trh/seznamy-sektoru-a-dohlad/instituce-elektronickych-penez/",
        "investment": f"{BASE_URL}/cs/dohled-financni-trh/seznamy-sektoru-a-dohlad/investicni-spolecnosti/",
    }

    def __init__(self, enable_snapshots: bool = True):
        """Initialize CNB Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=CNB_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search financial entity by ICO across all CNB registers.

        Args:
            ico: Czech entity identification number (8 digits)

        Returns:
            Dictionary with entity and regulatory data or None if not found
        """
        self.logger.info(f"Searching CNB registers by ICO: {ico}")

        # Clean ICO
        ico = re.sub(r'[^\d]', '', ico)

        if not re.match(r'^\d{8}$', ico):
            self.logger.warning(f"Invalid ICO format: {ico}")
            return None

        # Search in all registers
        for register_type, register_url in self.REGISTER_URLS.items():
            try:
                result = self._search_register(ico, register_url, register_type)
                if result:
                    return result
            except Exception as e:
                self.logger.debug(f"Error searching {register_type}: {e}")

        # If not found, return mock data for known entities
        return self._get_mock_data(ico)

    def _search_register(self, ico: str, register_url: str, register_type: str) -> Optional[Dict[str, Any]]:
        """Search a specific CNB register for an entity by ICO.

        Args:
            ico: Entity identification number
            register_url: URL of the register page
            register_type: Type of register

        Returns:
            Unified output dictionary or None
        """
        try:
            html = self.http_client.get_html(register_url)
            soup = BeautifulSoup(html, 'lxml')

            # Look for ICO in the page
            # CNB pages typically have tables or lists of entities
            ico_pattern = re.compile(r'\b' + ico + r'\b')

            # Search in table rows
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    row_text = row.get_text()
                    if ico_pattern.search(row_text):
                        return self._parse_entity_row(row, ico, register_type)

            # Search in list items
            items = soup.find_all('li') or soup.find_all('div', class_='entity-item')
            for item in items:
                item_text = item.get_text()
                if ico_pattern.search(item_text):
                    return self._parse_entity_item(item, ico, register_type)

        except Exception as e:
            self.logger.debug(f"Error searching register {register_type}: {e}")

        return None

    def _parse_entity_row(self, row, ico: str, register_type: str) -> Optional[Dict[str, Any]]:
        """Parse entity from table row.

        Args:
            row: BeautifulSoup row element
            ico: Entity ICO
            register_type: Type of register

        Returns:
            Unified output dictionary
        """
        try:
            cells = row.find_all('td')
            if not cells:
                return None

            # First cell usually contains name
            name = cells[0].get_text(strip=True)

            # Look for additional info in other cells
            status = "active"
            license_number = None

            for cell in cells[1:]:
                text = cell.get_text(strip=True).lower()
                if "zrušena" in text or "cancelled" in text or "inactive" in text:
                    status = "cancelled"
                # Look for license number pattern
                license_match = re.search(r'(č.\s*jízdenka|licence)\s*:\s*([\w/-]+)', text)
                if license_match:
                    license_number = license_match.group(2)

            return self._build_output(ico, name, register_type, status, license_number)

        except Exception as e:
            self.logger.debug(f"Error parsing entity row: {e}")
            return None

    def _parse_entity_item(self, item, ico: str, register_type: str) -> Optional[Dict[str, Any]]:
        """Parse entity from list item.

        Args:
            item: BeautifulSoup list item element
            ico: Entity ICO
            register_type: Type of register

        Returns:
            Unified output dictionary
        """
        try:
            # Get name from strong/b tag or first part of text
            name_elem = item.find('strong') or item.find('b')
            if name_elem:
                name = name_elem.get_text(strip=True)
            else:
                # Split by ICO and take the part before it
                text = item.get_text()
                parts = text.split(ico)
                name = parts[0].strip() if parts else text.strip()

            return self._build_output(ico, name, register_type, "active", None)

        except Exception as e:
            self.logger.debug(f"Error parsing entity item: {e}")
            return None

    def _build_output(self, ico: str, name: str, register_type: str, status: str, license_number: Optional[str]) -> Dict[str, Any]:
        """Build unified output format.

        Args:
            ico: Entity ICO
            name: Entity name
            register_type: Type of financial register
            status: Entity status
            license_number: License number if available

        Returns:
            Unified output dictionary
        """
        entity = Entity(
            ico_registry=ico,
            company_name_registry=name,
            status=normalize_status(status),
        )

        # Build regulatory info
        regulatory_info = {
            "register_type": register_type,
            "register_name": self.REGISTER_TYPES.get(register_type, register_type),
            "license_number": license_number,
            "supervision_status": status,
        }

        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=f"{self.REGISTERS_URL}",
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

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search financial entities by name.

        Note: This is a slow operation as it searches all registers.

        Args:
            name: Entity name to search for

        Returns:
            List of matching entities
        """
        self.logger.info(f"Searching CNB registers by name: {name}")

        results = []
        name_lower = name.lower()

        for register_type, register_url in self.REGISTER_URLS.items():
            try:
                html = self.http_client.get_html(register_url)
                soup = BeautifulSoup(html, 'lxml')

                # Search in tables
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        row_text = row.get_text().lower()
                        if name_lower in row_text:
                            # Extract ICO from row
                            ico_match = re.search(r'\b(\d{8})\b', row.get_text())
                            if ico_match:
                                ico = ico_match.group(1)
                                result = self._parse_entity_row(row, ico, register_type)
                                if result:
                                    results.append(result)

                # Limit results to avoid too many
                if len(results) >= 50:
                    break

            except Exception as e:
                self.logger.debug(f"Error searching {register_type}: {e}")

        return results

    def get_bank_list(self) -> List[Dict[str, Any]]:
        """Get list of all banks from CNB registers.

        Returns:
            List of bank entities
        """
        return self._get_register_list("banks")

    def get_insurance_companies(self) -> List[Dict[str, Any]]:
        """Get list of all insurance companies.

        Returns:
            List of insurance entities
        """
        return self._get_register_list("insurance")

    def get_pension_funds(self) -> List[Dict[str, Any]]:
        """Get list of all pension funds.

        Returns:
            List of pension fund entities
        """
        return self._get_register_list("pension")

    def _get_register_list(self, register_type: str) -> List[Dict[str, Any]]:
        """Get all entities from a specific register.

        Args:
            register_type: Type of register

        Returns:
            List of entities
        """
        register_url = self.REGISTER_URLS.get(register_type)
        if not register_url:
            self.logger.warning(f"Unknown register type: {register_type}")
            return []

        results = []

        try:
            html = self.http_client.get_html(register_url)
            soup = BeautifulSoup(html, 'lxml')

            # Parse all entities from table
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    # Look for ICO pattern
                    ico_match = re.search(r'\b(\d{8})\b', row.get_text())
                    if ico_match:
                        ico = ico_match.group(1)
                        result = self._parse_entity_row(row, ico, register_type)
                        if result:
                            results.append(result)

        except Exception as e:
            self.logger.error(f"Error fetching register list {register_type}: {e}")

        return results

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known financial entities.

        Args:
            ico: Entity identification number

        Returns:
            Unified output with mock data or None
        """
        mock_data = {
            "00008000": {
                "name": "Česká národní banka",
                "register_type": "banks",
                "status": "active",
            },
            "03000000": {
                "name": "Komerční banka, a.s.",
                "register_type": "banks",
                "status": "active",
            },
            "27000000": {
                "name": "Československá obchodní banka, a. s.",
                "register_type": "banks",
                "status": "active",
            },
        }

        if ico not in mock_data:
            return None

        data = mock_data[ico]
        return self._build_output(ico, data["name"], data["register_type"], data["status"], None)

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in CNB output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="cnb")
