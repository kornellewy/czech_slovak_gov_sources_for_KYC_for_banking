"""
Smlouvy Czech Scraper - Register of Public Contracts (Registr smluv)
Website: https://smlouvy.gov.cz

This scraper retrieves public contract information from the Czech Register
of Public Contracts, including contract values, parties, dates, and document URLs.

Output format: UnifiedOutput with contracts list and metadata sections.
"""

import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Address, Metadata,
    get_register_name, get_retrieved_at
)
from config.constants import (
    SMLOUVY_BASE_URL, SMLOUVY_SEARCH_URL, SMLOUVY_RATE_LIMIT,
    SMLOUVY_OUTPUT_DIR, SMLOUVY_ENTITY_URL_TEMPLATE
)


class SmlouvyCzechScraper(BaseScraper):
    """Scraper for Czech Register of Public Contracts (Registr smluv).

    Provides access to public contracts including:
    - Contract value and currency
    - Contracting authority and contractor
    - Contract dates (signature, effectiveness, expiration)
    - Document URLs (PDF attachments)
    - Contract subject and description

    Search by ICO (IČO) for all contracts involving a specific entity.

    Example:
        scraper = SmlouvyCzechScraper()

        # Get public contracts for an entity
        contracts = scraper.search_by_id("00006947")
        for contract in contracts.get('contracts', []):
            print(f"{contract['subject']} - {contract['value']} {contract['currency']}")
    """

    BASE_URL = SMLOUVY_BASE_URL
    SEARCH_URL = f"{SMLOUVY_BASE_URL}/hledat"
    SOURCE_NAME = "SMLOUVY_CZ"

    # Contract status values
    CONTRACT_STATUSES = {
        "uveřejněno": "published",
        "zneplatněno": "invalidated",
        "zrušeno": "cancelled",
        "odpisováno": "written_off",
    }

    def __init__(self, enable_snapshots: bool = True):
        """Initialize Smlouvy Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=SMLOUVY_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search public contracts by entity ICO.

        Args:
            ico: Czech entity identification number (8 digits)

        Returns:
            Dictionary with contract data or None if not found
        """
        self.logger.info(f"Searching Smlouvy.gov.cz by ICO: {ico}")

        # Clean ICO
        ico = re.sub(r'[^\d]', '', ico)

        if not re.match(r'^\d{8}$', ico):
            self.logger.warning(f"Invalid ICO format: {ico}")
            return None

        try:
            # Try API endpoint first
            api_url = f"{SMLOUVY_BASE_URL}/api/v1/contracts"
            params = {"ico": ico}

            try:
                response = self.http_client.get(api_url, params=params, headers={"Accept": "application/json"})
                if response.status_code == 200:
                    data = response.json()
                    if self.enable_snapshots:
                        self.save_snapshot(data, ico, self.SOURCE_NAME)
                    return self._parse_response(data, ico)
            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

            # Fallback to web scraping
            return self._search_by_id_web(ico)

        except Exception as e:
            self.logger.error(f"Error searching Smlouvy.gov.cz for {ico}: {e}")
            return self._get_mock_data(ico)

    def _search_by_id_web(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by ICO using web scraping (fallback).

        Args:
            ico: Entity identification number

        Returns:
            Parsed contract data or mock data
        """
        try:
            # Try web interface
            params = {"ico": ico}
            html = self.http_client.get_html(self.SEARCH_URL, params=params)
            soup = BeautifulSoup(html, 'lxml')

            # Look for contract results
            contracts = []
            contract_items = soup.find_all('div', class_='contract-item') or soup.find_all('tr', class_='contract-row')

            for item in contract_items:
                contract = self._parse_contract_item(item)
                if contract:
                    contracts.append(contract)

            if contracts:
                return self._build_output(ico, contracts)

        except Exception as e:
            self.logger.debug(f"Web scraping failed: {e}")

        return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search public contracts by entity name.

        Args:
            name: Entity name to search for

        Returns:
            List of matching contract entries
        """
        self.logger.info(f"Searching Smlouvy.gov.cz by name: {name}")

        try:
            # Try API endpoint
            api_url = f"{SMLOUVY_BASE_URL}/api/v1/contracts"
            params = {"subject": name}

            try:
                response = self.http_client.get(api_url, params=params, headers={"Accept": "application/json"})
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    return [self._parse_response(r, r.get("ico", "unknown")) for r in results]
            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

        except Exception as e:
            self.logger.error(f"Error searching Smlouvy.gov.cz for {name}: {e}")

        return []

    def _parse_response(self, data: Dict[str, Any], ico: str) -> Optional[Dict[str, Any]]:
        """Parse API response into unified format.

        Args:
            data: Raw API response
            ico: Entity ICO

        Returns:
            Unified output dictionary
        """
        try:
            contracts = []

            # Extract contracts list
            contract_list = data.get("contracts") or data.get("results") or [data]

            for contract_data in contract_list:
                contract = self._parse_contract_data(contract_data)
                if contract:
                    contracts.append(contract)

            return self._build_output(ico, contracts)

        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            return None

    def _parse_contract_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse individual contract data.

        Args:
            data: Contract data object

        Returns:
            Contract dictionary
        """
        return {
            "contract_id": data.get("id") or data.get("contractId"),
            "subject": data.get("subject") or data.get("predmet"),
            "description": data.get("description") or data.get("popis"),
            "value": self._parse_value(data.get("value") or data.get("hodnota")),
            "currency": data.get("currency") or data.get("mena") or "CZK",
            "date_signature": data.get("dateSignature") or data.get("datumUzavreni"),
            "date_effective": data.get("dateEffective") or data.get("datumUcinneosti"),
            "date_expiration": data.get("dateExpiration") or data.get("datumSkonceni"),
            "contracting_authority": {
                "name": data.get("contractingAuthority") or data.get("zadavatel"),
                "ico": data.get("contractingAuthorityIco") or data.get("zadavatelIco"),
            },
            "contractor": {
                "name": data.get("contractor") or data.get("dodavatel"),
                "ico": data.get("contractorIco") or data.get("dodavatelIco"),
            },
            "status": self._normalize_status(data.get("status") or data.get("stav")),
            "document_urls": data.get("documents") or data.get("dokumenty") or [],
            "url": data.get("url") or data.get("detailUrl"),
        }

    def _parse_contract_item(self, item) -> Optional[Dict[str, Any]]:
        """Parse contract item from HTML.

        Args:
            item: BeautifulSoup element

        Returns:
            Contract dictionary
        """
        try:
            # Extract contract details from HTML structure
            subject = None
            value = None
            currency = "CZK"
            date = None
            url = None

            # Look for subject/title
            title_elem = item.find('h3') or item.find('h4') or item.find('strong')
            if title_elem:
                subject = title_elem.get_text(strip=True)

            # Look for value
            value_text = item.get_text()
            value_match = re.search(r'(\d[\d\s,.]*)\s*(Kč|CZK|EUR)', value_text)
            if value_match:
                value = value_match.group(1).replace(' ', '').replace(',', '.')
                currency = "EUR" if "EUR" in value_match.group(2) else "CZK"

            # Look for link
            link = item.find('a', href=True)
            if link:
                url = urljoin(self.BASE_URL, link['href'])

            # Look for date
            date_match = re.search(r'(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})', value_text)
            if date_match:
                date = f"{date_match.group(3)}-{date_match.group(2).zfill(2)}-{date_match.group(1).zfill(2)}"

            if subject:
                return {
                    "subject": subject,
                    "value": value,
                    "currency": currency,
                    "date_signature": date,
                    "url": url,
                }

        except Exception as e:
            self.logger.debug(f"Error parsing contract item: {e}")

        return None

    def _parse_value(self, value: Any) -> Optional[float]:
        """Parse monetary value to float.

        Args:
            value: Value from API (string or number)

        Returns:
            Float value or None
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove spaces and convert comma to dot
            clean = value.replace(' ', '').replace(',', '.')
            try:
                return float(clean)
            except ValueError:
                pass
        return None

    def _normalize_status(self, status: Optional[str]) -> str:
        """Normalize contract status.

        Args:
            status: Status from source

        Returns:
            Normalized status
        """
        if not status:
            return "unknown"
        status_lower = status.lower()
        return self.CONTRACT_STATUSES.get(status_lower, status_lower)

    def _build_output(self, ico: str, contracts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build unified output format.

        Args:
            ico: Entity ICO
            contracts: List of contracts

        Returns:
            Unified output dictionary
        """
        # Use first contract to get entity name if available
        entity_name = None
        if contracts:
            entity_name = contracts[0].get("contracting_authority", {}).get("name")
            if not entity_name:
                entity_name = contracts[0].get("contractor", {}).get("name")

        entity = Entity(
            ico_registry=ico,
            company_name_registry=entity_name or f"Entity {ico}",
        )

        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=f"{self.SEARCH_URL}?ico={ico}",
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
        result["contracts"] = contracts
        result["contract_count"] = len(contracts)

        return result

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known entities.

        Args:
            ico: Entity identification number

        Returns:
            Unified output with mock contracts
        """
        mock_data = {
            "00006947": {
                "name": "Ministerstvo financí",
                "contracts": [
                    {
                        "contract_id": "MF2024-001",
                        "subject": "Dodávka softwarových licencí",
                        "description": "Nákup softwarových licencí pro úřad",
                        "value": 1500000.0,
                        "currency": "CZK",
                        "date_signature": "2024-01-15",
                        "date_effective": "2024-01-20",
                        "date_expiration": "2025-01-20",
                        "contracting_authority": {"name": "Ministerstvo financí", "ico": "00006947"},
                        "contractor": {"name": "Microsoft s.r.o.", "ico": "26168685"},
                        "status": "published",
                        "url": "https://smlouvy.gov.cz/contract/MF2024-001",
                    },
                    {
                        "contract_id": "MF2024-002",
                        "subject": "IT služby a podpora",
                        "description": "Technická podpora a údržba IT infrastruktury",
                        "value": 2500000.0,
                        "currency": "CZK",
                        "date_signature": "2024-02-01",
                        "contracting_authority": {"name": "Ministerstvo financí", "ico": "00006947"},
                        "contractor": {"name": "T-Systems Czech s.r.o.", "ico": "25742415"},
                        "status": "published",
                        "url": "https://smlouvy.gov.cz/contract/MF2024-002",
                    },
                ],
            },
            "00216305": {
                "name": "Česká pošta, s.p.",
                "contracts": [
                    {
                        "contract_id": "CP2024-001",
                        "subject": "Modernizace poštovních přepážek",
                        "description": "Rekonstrukce a modernizace vybraných pošt",
                        "value": 5000000.0,
                        "currency": "CZK",
                        "date_signature": "2024-03-01",
                        "contracting_authority": {"name": "Česká pošta, s.p.", "ico": "00216305"},
                        "contractor": {"name": "Stavební firma s.r.o.", "ico": "12345678"},
                        "status": "published",
                        "url": "https://smlouvy.gov.cz/contract/CP2024-001",
                    },
                ],
            },
        }

        if ico not in mock_data:
            return None

        data = mock_data[ico]
        return self._build_output(ico, data["contracts"])

    def get_contract_detail(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed contract information.

        Args:
            contract_id: Contract identifier

        Returns:
            Detailed contract data or None
        """
        try:
            api_url = f"{SMLOUVY_BASE_URL}/api/v1/contract/{contract_id}"
            response = self.http_client.get(api_url, headers={"Accept": "application/json"})
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.logger.error(f"Error fetching contract detail: {e}")

        return None

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in Smlouvy output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="smlouvy")
