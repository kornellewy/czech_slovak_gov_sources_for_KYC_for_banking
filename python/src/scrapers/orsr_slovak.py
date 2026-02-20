"""
ORSR Slovak Scraper - Business Register (Obchodný register)
Website: https://www.orsr.sk

This scraper uses web scraping to retrieve information about Slovak companies
from the official Business Register website.

Output format: UnifiedOutput with entity, holders, tax_info, and metadata sections.
"""

from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, Metadata,
    parse_address, normalize_status, normalize_country_code,
    get_register_name, get_retrieved_at, detect_holder_type, normalize_role
)
from config.constants import (
    ORSR_BASE_URL, ORSR_SEARCH_URL, ORSR_NAME_SEARCH_URL,
    ORSR_RATE_LIMIT, ORSR_OUTPUT_DIR, ORSR_SEARCH_URL_TEMPLATE
)


class ORSRSlovakScraper(BaseScraper):
    """Scraper for the Slovak Business Register (ORSR).

    Uses web scraping to extract company information from the official website.

    Example:
        scraper = ORSRSlovakScraper()

        # Search by ICO
        company = scraper.search_by_id("35763491")
        print(company['name'])  # "Slovenská sporiteľňa, a.s."

        # Search by name
        companies = scraper.search_by_name("Slovenská sporiteľňa")
        for c in companies:
            print(f"{c['name']} - {c['ico']}")

        # Save results
        scraper.save_to_json(company, "company_35763491.json")
    """

    BASE_URL = ORSR_BASE_URL
    SOURCE_NAME = "ORSR_SK"

    # Court code mapping
    COURT_CODES = {
        "Obchodný register Okresného súdu Bratislava I": "OS1BA",
        "Obchodný register Okresného súdu Bratislava II": "OS2BA",
        "Obchodný register Mestského súdu Bratislava I": "MS1BA",
        "Obchodný register Okresného súdu Košice I": "OS1KI",
        "Obchodný register Okresného súdu Trnava": "OSTT",
        "Obchodný register Okresného súdu Nitra": "OSNR",
        "Obchodný register Okresného súdu Žilina": "OSZA",
        "Obchodný register Okresného súdu Banská Bystrica": "OSBB",
        "Obchodný register Okresného súdu Prešov": "OSPO",
    }

    def __init__(self, enable_snapshots: bool = True):
        """Initialize ORSR Slovak scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=ORSR_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search company by ICO (identification number).

        Args:
            ico: Slovak company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        self.logger.info(f"Searching ORSR by ICO: {ico}")

        try:
            # Search by ICO
            params = {"ICO": ico.strip(), "lan": "en"}
            html = self.http_client.get_html(ORSR_SEARCH_URL, params=params)

            # Save snapshot if enabled
            if self.enable_snapshots:
                self.save_snapshot({"html": html}, ico, self.SOURCE_NAME)

            # Parse results
            results = self._parse_search_results(html)

            if not results:
                self.logger.warning(f"No entity found with ICO: {ico}")
                return None

            # Return first result with full details
            return results[0]

        except Exception as e:
            self.logger.error(f"Error searching ORSR for {ico}: {e}")
            return None

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search companies by name.

        Args:
            name: Company name or partial name to search for

        Returns:
            List of matching companies
        """
        self.logger.info(f"Searching ORSR by name: {name}")

        try:
            # Search by name
            params = {"OBMENO": name, "lan": "en"}
            html = self.http_client.get_html(ORSR_NAME_SEARCH_URL, params=params)

            # Parse results
            return self._parse_search_results(html)

        except Exception as e:
            self.logger.error(f"Error searching ORSR for {name}: {e}")
            return []

    def _parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """Parse search results HTML.

        Args:
            html: HTML content from search page

        Returns:
            List of company dictionaries
        """
        results = []
        soup = BeautifulSoup(html, 'lxml')

        # Find result table
        tables = soup.find_all('table')
        if not tables:
            return results

        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Try to extract company data
                    link = row.find('a')
                    if link:
                        company = self._parse_company_row(row)
                        if company:
                            results.append(company)

        return results

    def _parse_company_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single company row from search results into unified format.

        Args:
            row: BeautifulSoup row element

        Returns:
            Unified output dictionary or None
        """
        try:
            cells = row.find_all('td')
            link = row.find('a')

            if not link:
                return None

            # Extract detail URL
            detail_url = link.get('href', '')
            if detail_url:
                detail_url = urljoin(self.BASE_URL, detail_url)

            # Extract text content from cells
            texts = [cell.get_text(strip=True) for cell in cells]

            # Find ICO (8-digit number)
            ico = None
            for text in texts:
                if text.isdigit() and len(text) == 8:
                    ico = text
                    break

            # Extract company name (usually the link text)
            name = link.get_text(strip=True)

            # Extract court info
            court = None
            court_id = None
            for text in texts:
                if "Okresného súdu" in text or "Mestského súdu" in text:
                    court = text
                    court_id = self.COURT_CODES.get(text)
                    break

            if not ico:
                return None

            # Parse address
            address_data = self._parse_address(texts)
            address = None
            if address_data.get("full_address"):
                address = Address(
                    full_address=address_data.get("full_address"),
                    country="Slovensko",
                    country_code="SK",
                )

            # Build entity
            entity = Entity(
                ico_registry=ico,
                company_name_registry=name,
                status="active",  # Active if found in register
                registered_address=address,
            )

            # Build metadata
            register_url = ORSR_SEARCH_URL_TEMPLATE.format(ico=ico) if ico else None
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
                holders=[],  # Basic search doesn't provide holder info
                tax_info=None,  # ORSR doesn't provide tax info
                metadata=metadata,
            )

            return output.to_dict()

        except Exception as e:
            self.logger.debug(f"Error parsing company row: {e}")
            return None

    def _parse_address(self, texts: List[str]) -> Dict[str, str]:
        """Parse address from text fields.

        Args:
            texts: List of text strings from row

        Returns:
            Address dictionary
        """
        address = {}

        for text in texts:
            # Look for postal code pattern (5 digits with space)
            if " " in text and any(c.isdigit() for c in text):
                parts = text.split(",")
                if len(parts) >= 2:
                    address["full_address"] = text.strip()
                    break

        return address

    def get_company_detail(self, detail_url: str) -> Optional[Dict[str, Any]]:
        """Get detailed company information from detail page.

        Args:
            detail_url: URL to company detail page

        Returns:
            Detailed company data or None
        """
        try:
            html = self.http_client.get_html(detail_url)
            return self._parse_detail_page(html)
        except Exception as e:
            self.logger.error(f"Error fetching company detail: {e}")
            return None

    def _parse_detail_page(self, html: str) -> Dict[str, Any]:
        """Parse company detail page into unified format.

        Args:
            html: HTML content from detail page

        Returns:
            Unified output dictionary
        """
        soup = BeautifulSoup(html, 'lxml')

        # Extract data from detail page
        detail_data = {
            "name": None,
            "ico": None,
            "address": None,
            "date_registered": None,
            "court": None,
            "legal_form": None,
        }

        # Extract key-value pairs from tables
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)

                    if "Obchodné meno" in key:
                        detail_data["name"] = value
                    elif "IČO" in key:
                        detail_data["ico"] = value
                    elif "Sídlo" in key:
                        detail_data["address"] = value
                    elif "Dátum zápisu" in key:
                        detail_data["date_registered"] = value
                    elif "Súd" in key:
                        detail_data["court"] = value
                    elif "Právna forma" in key:
                        detail_data["legal_form"] = value

        ico = detail_data.get("ico", "")

        # Build address
        address = None
        if detail_data.get("address"):
            address = Address(
                full_address=detail_data["address"],
                country="Slovensko",
                country_code="SK",
            )

        # Build entity
        entity = Entity(
            ico_registry=ico,
            company_name_registry=detail_data.get("name"),
            legal_form=detail_data.get("legal_form"),
            status="active",
            incorporation_date=detail_data.get("date_registered"),
            registered_address=address,
        )

        # Build metadata
        register_url = ORSR_SEARCH_URL_TEMPLATE.format(ico=ico) if ico else None
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
            holders=[],  # Would need more parsing to extract holders
            tax_info=None,
            metadata=metadata,
        )

        return output.to_dict()

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in ORSR output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="orsr")
