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
        self.log_info(f"{self.SOURCE_NAME} scraper ready (rate limit: {ORSR_RATE_LIMIT} req/min)")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search company by ICO (identification number).

        Args:
            ico: Slovak company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        import time
        self.log_search_start(identifier=ico.strip(), search_type="by_ICO")

        try:
            # Search by ICO
            params = {"ICO": ico.strip(), "lan": "en"}
            url = f"{ORSR_SEARCH_URL}?ICO={ico.strip()}&lan=en"

            self.log_request("GET", url)
            start = time.time()

            html = self.http_client.get_html(ORSR_SEARCH_URL, params=params)

            duration_ms = (time.time() - start) * 1000
            self.log_response(url, 200, duration_ms)

            # Save snapshot if enabled
            if self.enable_snapshots:
                self.save_snapshot({"html": html}, ico, self.SOURCE_NAME)

            # Parse results
            self.log_parse_start("HTML")
            results = self._parse_search_results(html, ico=ico)

            if not results:
                self.log_warning(f"No entity found with ICO: {ico}")
                return None

            first_result = results[0]
            self.log_parse_complete("HTML", items_found=len(results))

            # Try to fetch complete data from detail page
            detail_url = first_result.get("detail_url")
            if detail_url:
                self.log_debug(f"Fetching detail page: {detail_url}")
                detail_result = self.get_company_detail(detail_url)
                if detail_result:
                    self.log_search_complete(results_count=1, identifier=ico)
                    return detail_result
                else:
                    self.log_warning("Failed to fetch detail page, using basic info")

            self.log_search_complete(results_count=1, identifier=ico)

            # Return first result (with or without detail data)
            return first_result

        except Exception as e:
            self.log_error("search_by_id", e, ico=ico)
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

    def _parse_search_results(self, html: str, ico: Optional[str] = None) -> List[Dict[str, Any]]:
        """Parse search results HTML.

        Args:
            html: HTML content from search page
            ico: Optional ICO (when searching by ID) to include in results

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
                    # Check if this is a data row (has vypis.asp link to detail page)
                    # This filters out header rows and other non-result rows
                    has_detail_link = False
                    for cell in cells:
                        links = cell.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            if 'vypis.asp' in href and 'ID=' in href:
                                has_detail_link = True
                                break
                        if has_detail_link:
                            break

                    if has_detail_link:
                        company = self._parse_company_row(row, ico=ico)
                        if company:
                            results.append(company)

        return results

    def _parse_company_row(self, row, ico: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parse a single company row from search results into unified format.

        ORSR search results table structure:
        - Cell 0: Row number (1., 2., etc.)
        - Cell 1: Company name
        - Cell 2: Extract links (Actual, Full)
        - Cell 3: Document collection link

        Args:
            row: BeautifulSoup row element
            ico: Optional ICO (when searching by ID) - if not provided, will try to extract from row

        Returns:
            Unified output dictionary or None
        """
        try:
            cells = row.find_all('td')

            # Need at least 3 cells for a valid result row
            if len(cells) < 3:
                return None

            # Extract text content from cells
            texts = [cell.get_text(strip=True) for cell in cells]

            # Find ICO (8-digit number) - use provided ICO or try to extract from row
            if not ico:
                for text in texts:
                    if text.isdigit() and len(text) == 8:
                        ico = text
                        break

            if not ico:
                return None

            # Extract company name from second cell (index 1)
            # Company name is in a div with class "sbj"
            name = cells[1].get_text(strip=True) if len(cells) > 1 else ""

            # Extract detail URL from third cell (index 2) - look for "Actual" link
            detail_url = None
            if len(cells) > 2:
                # Find all links in the extract column
                links = cells[2].find_all('a')
                for link in links:
                    link_text = link.get_text(strip=True)
                    href = link.get('href', '')
                    # Prefer "Actual" link (P=0), fallback to "Full" link (P=1)
                    if 'vypis.asp' in href and 'ID=' in href:
                        detail_url = urljoin(self.BASE_URL, href)
                        # Prefer Actual (P=0) over Full (P=1)
                        if 'P=0' in href or 'Actual' in link_text:
                            break

            # Extract court info
            court = None
            court_id = None
            for text in texts:
                if "Okresného súdu" in text or "Mestského súdu" in text:
                    court = text
                    court_id = self.COURT_CODES.get(text)
                    break

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

            result = output.to_dict()
            # Include detail_url for fetching complete data
            if detail_url:
                result["detail_url"] = detail_url
            return result

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

        The detail page HTML structure has nested tables. Each field is structured as:
        <tr>
            <td><span class="tl">Label:&nbsp;</span></td>
            <td><table width="100%" border="0">
                <tr>
                    <td width="67%"> <span class='ra'> VALUE </span><br></td>
                    <td width="33%" valign='top'>&nbsp; <span class='ra'>(from: DATE)</span></td>
                </tr>
                </table></td>
        </tr>

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

        # Define label patterns (both English and Slovak)
        # Order matters - more specific patterns first
        label_patterns = {
            "name": ["Business name", "Obchodné meno", "business name"],
            "ico": ["Identification number (I", "Identification number (IČO)", "IČO:", "Identification number"],
            "address": ["Registered seat", "Sídlo", "registered seat"],
            "date_registered": ["Date of entry", "Dátum zápisu", "date of entry"],
            "court": ["Court", "Súd", "District Court"],
            "legal_form": ["Legal form", "Právna forma", "legal form"],
        }

        # Extract key-value pairs from tables
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)

                    # Value might be directly in cell or in nested table
                    # Find the value in the first nested table's first cell, or direct text
                    value_cell = cells[1]
                    nested_table = value_cell.find('table')
                    if nested_table:
                        # Value is in nested table structure
                        nested_rows = nested_table.find_all('tr')
                        if nested_rows:
                            nested_cells = nested_rows[0].find_all('td')
                            if nested_cells:
                                value = nested_cells[0].get_text(strip=True)
                            else:
                                value = value_cell.get_text(strip=True)
                        else:
                            value = value_cell.get_text(strip=True)
                    else:
                        value = value_cell.get_text(strip=True)

                    # Match key to field using patterns
                    for field, patterns in label_patterns.items():
                        if any(pattern.lower() in key.lower() for pattern in patterns):
                            # Clean up the value (remove extra whitespace and date suffixes)
                            value = value.split("(from:")[0].strip()
                            if value:
                                detail_data[field] = value
                            break

        # Clean up ICO (remove spaces and format)
        if detail_data.get("ico"):
            ico = detail_data["ico"].replace(" ", "").split("(from:")[0].strip()
            detail_data["ico"] = ico

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
