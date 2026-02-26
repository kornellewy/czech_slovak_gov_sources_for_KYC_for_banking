"""
Justice Czech Scraper - Commercial Register (Obchodní rejstřík)
Website: https://or.justice.cz

Based on patterns from: https://github.com/lubosdz/parser-justice-cz

This scraper retrieves company data from the Czech Commercial Register using web scraping.

Key patterns from parser-justice-cz:
- URL: https://or.justice.cz/ias/ui/rejstrik-firma?ico={ICO}
- HTML structure: table[@class="result-details"]/tbody
- Row 1: td[1]=name, td[2]=ICO
- Row 2: td[1]=file_number, td[2]=date_established
- Row 3: td[1]=address
- Links: ../../ul[1]/li/a (3 links: platny, uplny, sbirkaListin)

Output format: UnifiedOutput with entity, holders, tax_info, and metadata sections.
"""

import re
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.scrapers.base_playwright import (
    PlaywrightBaseScraper, PlaywrightError, PlaywrightNotAvailableError
)
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, Metadata,
    parse_address, normalize_status, normalize_country_code,
    get_register_name, get_retrieved_at, detect_holder_type, normalize_role
)
from config.constants import (
    JUSTICE_BASE_URL, JUSTICE_SEARCH_URL, JUSTICE_RATE_LIMIT,
    JUSTICE_OUTPUT_DIR, JUSTICE_ENTITY_URL_TEMPLATE,
    JUSTICE_MAINTENANCE_INDICATORS, JUSTICE_MAINTENANCE_URL
)


# Czech month names for parsing dates
CZECH_MONTHS = {
    "leden": 1, "ledna": 1,
    "únor": 2, "února": 2,
    "březen": 3, "března": 3,
    "duben": 4, "dubna": 4,
    "květen": 5, "května": 5,
    "červen": 6, "června": 6,
    "červenec": 7, "července": 7,
    "srpen": 8, "srpna": 8,
    "září": 9,
    "říjen": 10, "října": 10,
    "listopad": 11, "listopadu": 11,
    "prosinec": 12, "prosince": 12,
}


class JusticeCzechScraper(PlaywrightBaseScraper):
    """Scraper for Czech Commercial Register (Obchodní rejstřík).

    Uses web scraping to extract company information from the official Justice.cz website.
    Implementation based on parser-justice-cz patterns.

    Search endpoints:
    - By ICO: https://or.justice.cz/ias/ui/rejstrik-firma?ico={ICO}
    - By name: https://or.justice.cz/ias/ui/rejstrik-firma?nazev={name}

    Example:
        scraper = JusticeCzechScraper()

        # Search by IČO
        company = scraper.search_by_id("44315945")
        print(company['entity']['company_name_registry'])

        # Search by name
        companies = scraper.search_by_name("auto")
        for c in companies:
            print(f"{c['name']} - {c['ico']}")
    """

    BASE_URL = JUSTICE_BASE_URL
    SEARCH_URL = JUSTICE_SEARCH_URL  # Uses correct URL: /ias/ui/rejstrik-$firma
    SOURCE_NAME = "JUSTICE_CZ"

    # Default delay between requests (seconds)
    DEFAULT_DELAY = 10  # 10 seconds between requests to avoid blocking

    def __init__(
        self,
        enable_snapshots: bool = True,
        use_playwright: bool = True,
        delay_between_requests: float = DEFAULT_DELAY
    ):
        """Initialize Justice Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
            use_playwright: Whether to use Playwright browser automation (with fallback)
            delay_between_requests: Delay between requests in seconds (default: 10)
                - Recommended: 10 seconds for safe scraping
                - Minimum: 1 second (may trigger rate limiting)
                - Set to 0 to disable delays (not recommended)
        """
        super().__init__(enable_snapshots=enable_snapshots)

        # Rate limiting: delay between requests to avoid blocking
        self.delay_between_requests = delay_between_requests
        self._last_request_time = 0

        # Justice.cz requires proper browser headers to avoid blocking
        justice_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'cs-CZ,cs;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }

        self.http_client = HTTPClient(rate_limit=JUSTICE_RATE_LIMIT)
        # Override headers for Justice.cz
        self.http_client.session.headers.update(justice_headers)

        self.use_playwright = use_playwright
        self.log_info(f"{self.SOURCE_NAME} scraper ready (playwright={use_playwright}, delay={delay_between_requests}s)")

    def _wait_for_rate_limit(self) -> None:
        """Wait before next request to avoid rate limiting.

        Implements a delay between requests to Justice.cz to prevent IP blocking.
        The delay is configurable via `delay_between_requests` parameter.
        """
        if self.delay_between_requests <= 0:
            return  # No delay configured

        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay_between_requests:
            wait_time = self.delay_between_requests - elapsed
            self.log_rate_limit(wait_time)
            time.sleep(wait_time)

        self._last_request_time = time.time()

    def _check_maintenance(self, html: str) -> bool:
        """Check if Justice.cz is showing maintenance page.

        Args:
            html: HTML response from Justice.cz

        Returns:
            True if maintenance page is detected, False otherwise
        """
        if not html:
            return False

        # Check for maintenance indicators
        for indicator in JUSTICE_MAINTENANCE_INDICATORS:
            if indicator in html:
                self.log_maintenance("Justice.cz")
                return True

        # Check for maintenance background image
        if JUSTICE_MAINTENANCE_URL and JUSTICE_MAINTENANCE_URL in html:
            self.log_maintenance("Justice.cz")
            return True

        return False

    def _create_maintenance_response(self) -> Dict[str, Any]:
        """Create a standardized maintenance response.

        Returns:
            Dictionary with maintenance information
        """
        return {
            "entity": {
                "ico_registry": None,
                "company_name_registry": None,
                "status": "maintenance",
                "registered_address": None,
            },
            "holders": [],
            "tax_info": {
                "vat_id": None,
                "vat_status": None,
            },
            "metadata": {
                "source": self.SOURCE_NAME,
                "register_name": get_register_name(self.SOURCE_NAME),
                "register_url": JUSTICE_BASE_URL,
                "retrieved_at": get_retrieved_at(),
                "is_mock": False,
                "maintenance": True,
                "maintenance_message": "Justice.cz is under maintenance (Momentálně probíhá údržba)",
                "note": "Please try again later. Typical maintenance: Sunday nights 02:00-06:00 CET"
            }
        }

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search company by IČO (identification number).

        Args:
            ico: Czech company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        # Clean ICO - keep only digits
        ico_clean = re.sub(r'[^\d]', '', ico)

        self.log_search_start(identifier=ico_clean, search_type="by_ICO")

        if not re.match(r'^\d{8}$', ico_clean):
            self.log_warning(f"Invalid IČO format: {ico_clean}")
            return None

        # Try Playwright first if enabled
        if self.use_playwright:
            try:
                result = self._search_by_id_playwright(ico_clean)
                if result:
                    return result
            except PlaywrightNotAvailableError:
                self.log_info("Playwright not available, falling back to static scraping")
            except PlaywrightError as e:
                self.log_warning(f"Playwright search failed: {e}, falling back to static scraping")

        # Fallback to static scraping
        return self._search_by_id_static(ico_clean)

    def _search_by_id_playwright(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by IČO using Playwright browser automation.

        Args:
            ico: Czech company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        self.log_debug(f"Using Playwright to search for IČO: {ico}")

        # Wait before request to avoid rate limiting
        self._wait_for_rate_limit()

        url = f"{self.SEARCH_URL}?ico={ico}"
        self.log_request("GET", url)

        start = time.time()

        try:
            with self._get_page() as page:
                # Navigate to search page
                if not self._navigate_and_wait(
                    page,
                    url,
                    wait_selector="table.result-details",
                    wait_until="networkidle"
                ):
                    # Check for maintenance page (no results table)
                    html = self._get_page_html(page)
                    if self._check_maintenance(html):
                        duration_ms = (time.time() - start) * 1000
                        self.log_response(url, 503, duration_ms)
                        return self._create_maintenance_response()

                    # Take screenshot for debugging if enabled
                    self._take_screenshot(page, f"justice_no_results_{ico}.png")
                    duration_ms = (time.time() - start) * 1000
                    self.log_response(url, 404, duration_ms)
                    self.log_warning(f"No results table found for IČO: {ico}")
                    return None

                # Take screenshot for successful load if enabled
                self._take_screenshot(page, f"justice_results_{ico}.png")

                # Get HTML content
                html = self._get_page_html(page)
                duration_ms = (time.time() - start) * 1000
                self.log_response(url, 200, duration_ms)

                # Check for maintenance (after navigation)
                if self._check_maintenance(html):
                    return self._create_maintenance_response()

                # Save snapshot if enabled
                if self.enable_snapshots:
                    self.save_snapshot({"html": html, "method": "playwright"}, ico, self.SOURCE_NAME)

                # Parse results
                self.log_parse_start("HTML")
                results = self._extract_subjects(html)

                if not results:
                    self.log_warning(f"No entity found with IČO: {ico}")
                    return None

                self.log_parse_complete("HTML", items_found=len(results))
                self.log_search_complete(results_count=1, identifier=ico)
                return results[0]

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self.log_response(url, 500, duration_ms)
            self.log_error("_search_by_id_playwright", e, ico=ico)
            raise PlaywrightError(f"Playwright search failed: {e}") from e

    def _search_by_id_static(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by IČO using static HTTP requests (fallback).

        Args:
            ico: Czech company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        self.log_debug(f"Using static scraping for IČO: {ico}")

        # Wait before request to avoid rate limiting
        self._wait_for_rate_limit()

        url = f"{self.SEARCH_URL}?ico={ico}"

        try:
            self.log_request("GET", url)
            start = time.time()

            # Search by ICO - exact pattern from parser-justice-cz
            html = self.http_client.get_html(url)

            duration_ms = (time.time() - start) * 1000
            self.log_response(url, 200, duration_ms)

            # Check for maintenance page first
            if self._check_maintenance(html):
                return self._create_maintenance_response()

            # Save snapshot if enabled
            if self.enable_snapshots:
                self.save_snapshot({"html": html, "method": "static"}, ico, self.SOURCE_NAME)

            # Parse results using the same XPath-like pattern
            self.log_parse_start("HTML")
            results = self._extract_subjects(html)

            if not results:
                self.log_warning(f"No entity found with IČO: {ico}")
                self.log_mock_fallback("Static scraping returned no results")
                return self._get_mock_data(ico)

            self.log_parse_complete("HTML", items_found=len(results))
            self.log_search_complete(results_count=1, identifier=ico)

            # Return first result with full details
            return results[0]

        except Exception as e:
            self.log_response(url, 500, 0)
            self.log_error("_search_by_id_static", e, ico=ico)

            # Check if error is related to maintenance (503 Service Unavailable)
            error_str = str(e).lower()
            if any(x in error_str for x in ['503', 'service unavailable', 'maintenance', 'údržba']):
                self.log_maintenance("Justice.cz")
                return self._create_maintenance_response()

            # Return mock data as fallback
            self.log_mock_fallback(f"API unavailable: {e}")
            return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search companies by name.

        Args:
            name: Company name or partial name to search for (min 3 characters)

        Returns:
            List of matching companies
        """
        self.logger.info(f"Searching Justice.cz by name: {name}")

        name = name.strip()
        if len(name) < 3:
            self.logger.warning("Name search requires at least 3 characters")
            return []

        try:
            # Check if searching by ICO (8 digits)
            if re.match(r'^\d{8}$', name):
                result = self.search_by_id(name)
                return [result] if result else []

            # Try Playwright first if enabled
            if self.use_playwright:
                try:
                    results = self._search_by_name_playwright(name)
                    if results:
                        return results
                except PlaywrightNotAvailableError:
                    self.logger.info("Playwright not available, falling back to static scraping")
                except PlaywrightError as e:
                    self.logger.warning(f"Playwright search failed: {e}, falling back to static scraping")

            # Fallback to static scraping
            return self._search_by_name_static(name)

        except Exception as e:
            self.logger.error(f"Error searching Justice.cz for {name}: {e}")
            return []

    def _search_by_name_playwright(self, name: str) -> List[Dict[str, Any]]:
        """Search by name using Playwright browser automation.

        Args:
            name: Company name or partial name to search for

        Returns:
            List of matching companies
        """
        self.logger.debug(f"Using Playwright to search for name: {name}")

        # Wait before request to avoid rate limiting
        self._wait_for_rate_limit()

        url = f"{self.SEARCH_URL}?nazev={name}"

        try:
            with self._get_page() as page:
                # Navigate to search page
                if not self._navigate_and_wait(
                    page,
                    url,
                    wait_selector="table.result-details",
                    wait_until="networkidle"
                ):
                    # Take screenshot for debugging if enabled
                    self._take_screenshot(page, f"justice_no_results_name_{name[:20]}.png")
                    self.logger.warning(f"No results table found for name: {name}")
                    return []

                # Take screenshot for successful load if enabled
                self._take_screenshot(page, f"justice_results_name_{name[:20]}.png")

                # Get HTML content
                html = self._get_page_html(page)

                # Parse results
                return self._extract_subjects(html)

        except Exception as e:
            self.logger.error(f"Playwright error searching for name {name}: {e}")
            raise PlaywrightError(f"Playwright search failed: {e}") from e

    def _search_by_name_static(self, name: str) -> List[Dict[str, Any]]:
        """Search by name using static HTTP requests (fallback).

        Args:
            name: Company name or partial name to search for

        Returns:
            List of matching companies
        """
        self.logger.debug(f"Using static scraping for name: {name}")

        # Wait before request to avoid rate limiting
        self._wait_for_rate_limit()

        try:
            # Search by name - exact pattern from parser-justice-cz
            url = f"{self.SEARCH_URL}?nazev={name}"
            html = self.http_client.get_html(url)

            # Parse results
            return self._extract_subjects(html)

        except Exception as e:
            self.logger.error(f"Static scraping error for {name}: {e}")
            return []

    def _extract_subjects(self, html: str) -> List[Dict[str, Any]]:
        """Extract subjects from Justice.cz HTML response.

        HTML structure (actual):
        <table class="result-details">
          <tbody>
            <tr>
              <th>Název subjektu:</th>
              <td><strong>Company Name</strong></td>
              <th>IČO:</th>
              <td>06649114</td>
            </tr>
            <tr>
              <th>Spisová značka:</th>
              <td>B 23056...</td>
              <th>Den zápisu:</th>
              <td>1. prosince 2017</td>
            </tr>
            <tr>
              <th>Sídlo:</th>
              <td colspan="3">Address...</td>
            </tr>
          </tbody>
        </table>
        <ul class="result-links">
          <li><a href="...">Výpis platných</a></li>
          <li><a href="...">Úplný výpis</a></li>
          <li><a href="...">Sbírka listin</a></li>
        </ul>

        Args:
            html: HTML content from search page

        Returns:
            List of company dictionaries in unified format
        """
        results = []
        soup = BeautifulSoup(html, 'lxml')

        # Find all result tables (one per company)
        result_tables = soup.find_all('table', class_='result-details')

        for result_table in result_tables:
            result = self._parse_result_table(result_table)
            if result:
                results.append(result)

        return results

    def _parse_result_table(self, table) -> Optional[Dict[str, Any]]:
        """Parse a single result table into unified format.

        Args:
            table: BeautifulSoup table element with class 'result-details'

        Returns:
            Unified output dictionary or None if parsing fails
        """
        tbody = table.find('tbody')
        if not tbody:
            rows = table.find_all('tr')
        else:
            rows = tbody.find_all('tr')

        if not rows:
            return None

        # Initialize extracted data
        name = ''
        ico = ''
        spis_znacka = ''
        den_zapisu_txt = ''
        den_zapisu_num = ''
        addr_full = ''

        # Parse each row looking for th/td pairs
        for row in rows:
            ths = row.find_all('th')
            tds = row.find_all('td')

            for th in ths:
                th_text = th.get_text(strip=True).lower()

                # Find the corresponding td (next sibling or based on position)
                td = th.find_next_sibling('td')
                if not td:
                    # Try to find by position
                    th_index = list(row.children).index(th)
                    for td_elem in tds:
                        if list(row.children).index(td_elem) > th_index:
                            td = td_elem
                            break

                if not td:
                    continue

                td_text = td.get_text(strip=True)

                # Name: "Název subjektu"
                if 'název' in th_text and 'subjekt' in th_text:
                    name = td_text
                    name = re.sub(r'\s+', ' ', name)

                # ICO: "IČO"
                elif 'ičo' in th_text or 'ico' in th_text:
                    ico = re.sub(r'[^\d]', '', td_text)

                # File number: "Spisová značka"
                elif 'spisov' in th_text and 'znač' in th_text:
                    spis_znacka = td_text

                # Registration date: "Den zápisu"
                elif 'zápis' in th_text:
                    den_zapisu_txt = td_text
                    den_zapisu_num = self._parse_czech_date(td_text)

                # Address: "Sídlo"
                elif 'sídlo' in th_text:
                    addr_full = td_text

        # Validate required fields
        if not ico or len(ico) != 8:
            return None

        if not name:
            return None

        # Parse address components
        addr_city, addr_zip, addr_streetnr = self._parse_address(addr_full)

        # Find detail links (sibling ul.result-links)
        url_platnych, url_uplny, url_sbirka_listin = self._find_detail_links(table)

        # Build entity
        entity = Entity(
            ico_registry=ico,
            company_name_registry=name,
            status="active",  # Active if found in register
            incorporation_date=den_zapisu_num,
            registered_address=Address(
                street=addr_streetnr or None,
                city=addr_city or None,
                postal_code=addr_zip or None,
                country="Česká republika",
                country_code="CZ",
                full_address=addr_full or None,
            ) if addr_full else None,
        )

        # Build metadata
        register_url = url_platnych or f"{self.SEARCH_URL}?ico={ico}"
        metadata = Metadata(
            source=self.SOURCE_NAME,
            register_name=get_register_name(self.SOURCE_NAME),
            register_url=register_url,
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

        # Add extra data
        result["file_number"] = self._trim_quotes(spis_znacka)
        result["date_registered_text"] = self._trim_quotes(den_zapisu_txt)
        if url_uplny:
            result["url_uplny"] = url_uplny
        if url_sbirka_listin:
            result["url_sbirka_listin"] = url_sbirka_listin

        return result

    def _parse_address(self, addr: str) -> tuple:
        """Parse address string into components.

        Args:
            addr: Full address string

        Returns:
            Tuple of (city, postal_code, street)
        """
        if not addr:
            return ('', '', '')

        city = ''
        addr_city = ''
        addr_zip = ''
        addr_streetnr = ''

        # Pattern 1: "Příborská 597, Místek, 738 01 Frýdek-Místek"
        match = re.search(r',\s*(\d{3}\s*\d{2})\s+(.+)$', addr)
        if match:
            addr_zip = re.sub(r'\s', '', match.group(1))
            addr_city = match.group(2)
            parts = addr.split(',')
            addr_streetnr = parts[0].strip() if parts else ''
            city = self._shorten_city(addr_city)
        # Pattern 2: "Řevnice, ČSLA 118, okres Praha-západ, PSČ 25230"
        elif 'PSČ' in addr:
            match = re.search(r',\s*PSČ\s+(\d{3}\s*\d{2})$', addr)
            if match:
                addr_zip = re.sub(r'\s', '', match.group(1))
                parts = addr.split(',')
                city = parts[0].strip() if parts else ''
                addr_city = city
                addr_streetnr = ', '.join(parts[1:-1]).strip() if len(parts) > 1 else ''
                city = self._shorten_city(city)
        # Pattern 3: "Partyzánská 188/7a, Holešovice, 170 00 Praha 7"
        elif re.search(r',\s*(\d{3}\s*\d{2})\s+', addr):
            # Find PSC in middle of address
            match = re.search(r',\s*(\d{3}\s*\d{2})\s+(.+)$', addr)
            if match:
                addr_zip = re.sub(r'\s', '', match.group(1))
                addr_city = match.group(2)
                parts = addr.split(',')
                addr_streetnr = parts[0].strip() if parts else ''
                city = self._shorten_city(addr_city)
            else:
                city = addr
                addr_city = addr
        # Pattern 4: Without PSC
        elif not re.search(r'\d{3}\s*\d{2}', addr):
            parts = addr.split(',')
            if len(parts) >= 2:
                city = parts[0].strip()
                addr_streetnr = ', '.join(parts[1:]).strip()
                addr_city = city
                city = self._shorten_city(city)
            else:
                city = addr
                addr_city = addr
        else:
            addr_city = addr

        return (addr_city, addr_zip, addr_streetnr)

    def _find_detail_links(self, table) -> tuple:
        """Find detail page links from result table.

        Links are in a sibling <ul class="result-links"> element.

        Args:
            table: BeautifulSoup table element

        Returns:
            Tuple of (url_platnych, url_uplny, url_sbirka_listin)
        """
        url_platnych = ''
        url_uplny = ''
        url_sbirka_listin = ''

        # Find the parent container (usually div.inner)
        parent = table.parent
        if not parent:
            return (url_platnych, url_uplny, url_sbirka_listin)

        # Look for ul.result-links within the same container
        links_ul = parent.find('ul', class_='result-links')
        if not links_ul:
            # Try siblings of parent
            for sibling in parent.next_siblings:
                if hasattr(sibling, 'find'):
                    links_ul = sibling.find('ul', class_='result-links')
                    if links_ul:
                        break

        if links_ul:
            links = links_ul.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()

                if 'platn' in text or 'typ=platny' in href.lower():
                    url_platnych = self._normalize_url(href)
                elif 'úpln' in text or 'upln' in text or 'typ=uplny' in href.lower():
                    url_uplny = self._normalize_url(href)
                elif 'sbirk' in text or 'sbirka' in text or 'vypis-sl' in href.lower():
                    url_sbirka_listin = self._normalize_url(href)

        return (url_platnych, url_uplny, url_sbirka_listin)

    def _parse_czech_date(self, text: str) -> Optional[str]:
        """Parse Czech date format (e.g., "26. srpna 1992") to ISO format.

        Pattern from parser-justice-cz: "30. ledna 2000" -> "2000-01-30"

        Args:
            text: Text containing date

        Returns:
            ISO formatted date string or None
        """
        # Pattern: DD. month_name YYYY
        date_pattern = r'(\d{1,2})\.\s+([a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]+)\s+(\d{4})'
        match = re.search(date_pattern, text)
        if match:
            day = int(match.group(1))
            month_name = match.group(2).lower()
            year = int(match.group(3))

            month = self._numerize_month(month_name)
            if month:
                try:
                    return f"{year:04d}-{month:02d}-{day:02d}"
                except ValueError:
                    pass

        return None

    def _numerize_month(self, month: str) -> Optional[int]:
        """Convert Czech month name to number.

        From parser-justice-cz numerizeMonth function.

        Args:
            month: Month name in Czech

        Returns:
            Month number (1-12) or None
        """
        month = month.lower()

        for name, num in CZECH_MONTHS.items():
            if month.startswith(name[:4]):  # Match first 4 chars for flexibility
                return num

        return None

    def _shorten_city(self, city: str) -> str:
        """Shorten city name (e.g., "Praha 10" -> "Praha").

        From parser-justice-cz pattern.

        Args:
            city: Full city name

        Returns:
            Shortened city name
        """
        if not city:
            return city

        # "Praha 10 - Dolní Měcholupy" -> "Praha 10"
        city = city.split('-')[0].strip()

        # "Praha 5" -> "Praha"
        city = re.sub(r'\d+$', '', city).strip()

        return city

    def _normalize_url(self, url: str) -> str:
        """Normalize relative URL to absolute URL.

        From parser-justice-cz normalizeUrl function.

        Args:
            url: Relative or absolute URL

        Returns:
            Absolute URL
        """
        if not url:
            return ''

        # Convert relative URL to absolute
        if url.startswith('./'):
            url = url[2:]
        elif url.startswith('/'):
            url = url[1:]

        # Build absolute URL
        url = f"{self.BASE_URL}/ias/ui/{url}"

        # Remove session hash (&sp=...)
        url = url.split('&sp=')[0]

        return url

    def _trim_quotes(self, text: str) -> str:
        """Remove quotes from text.

        From parser-justice-cz trimQuotes function.

        Args:
            text: Text to trim

        Returns:
            Trimmed text
        """
        return text.strip().strip('"').strip("'")

    def get_detail_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Get detailed company information from detail page.

        Args:
            url: URL to company detail page (platný or úplný výpis)

        Returns:
            Detailed company data or None
        """
        try:
            html = self.http_client.get_html(url)
            return self._parse_detail_page(html)
        except Exception as e:
            self.logger.error(f"Error fetching detail page: {e}")
            return None

    def _parse_detail_page(self, html: str) -> Optional[Dict[str, Any]]:
        """Parse company detail page into unified format.

        The detail page HTML structure uses:
        - div.vr-hlavicka for section headers
        - div.div-table/div-row/div-cell for key-value pairs
        - Nested div.aunp-content for person data
        - span.nowrap for ICO with special spacing

        Args:
            html: HTML content from detail page

        Returns:
            Dictionary with company data or None
        """
        soup = BeautifulSoup(html, 'lxml')

        data = {
            'name': None,
            'ico': None,
            'file_number': None,
            'address': None,
            'incorporation_date': None,
            'legal_form': None,
            'statutory_body': [],
            'shareholders': [],
            'raw_html': html,
        }

        # Extract company name from h2 (first span after "Výpis z obchodního rejstříku")
        h2 = soup.find('h2')
        if h2:
            spans = h2.find_all('span')
            if len(spans) > 1:
                data['name'] = spans[1].get_text(strip=True)

        # Extract ICO from span.nowrap (has special formatting with spaces)
        ico_span = soup.find('span', class_='nowrap')
        if ico_span:
            ico_text = ico_span.get_text()
            # Remove all non-digit characters
            ico_clean = re.sub(r'[^\d]', '', ico_text)
            if len(ico_clean) == 8:
                data['ico'] = ico_clean

        # Iterate through all div-table rows to extract key-value pairs
        for div_row in soup.find_all('div', class_='div-row'):
            cells = div_row.find_all('div', class_='div-cell')
            if len(cells) >= 2:
                header_cell = cells[0]
                value_cell = cells[1]

                header_text = header_cell.get_text(strip=True).lower()
                value_text = value_cell.get_text(strip=True)

                # Match sections
                if 'obchodn' in header_text and 'firma' in header_text:
                    data['name'] = value_text
                elif 'identifika' in header_text and ('cislo' in header_text or 'ico' in header_text):
                    # Try to extract ICO if not found yet
                    if not data['ico']:
                        # Look for nowrap span in value cell
                        ico_span = value_cell.find('span', class_='nowrap')
                        if ico_span:
                            ico_text = ico_span.get_text()
                            ico_clean = re.sub(r'[^\d]', '', ico_text)
                            if len(ico_clean) == 8:
                                data['ico'] = ico_clean
                        else:
                            ico_clean = re.sub(r'[^\d]', '', value_text)
                            if len(ico_clean) == 8:
                                data['ico'] = ico_clean
                elif 'spisov' in header_text and 'zna' in header_text:
                    data['file_number'] = value_text
                elif 'sidl' in header_text:
                    # Address is often in nested spans
                    addr_spans = value_cell.find_all('span')
                    if addr_spans:
                        # Find the span with address-like content (has numbers and text)
                        for span in addr_spans:
                            span_text = span.get_text(strip=True)
                            if re.search(r'\d', span_text) and len(span_text) > 10:
                                data['address'] = span_text
                                break
                    if not data['address']:
                        data['address'] = value_text
                elif 'datum vzniku' in header_text or 'datum zapis' in header_text:
                    data['incorporation_date'] = value_text
                elif 'pravn' in header_text and 'forma' in header_text:
                    data['legal_form'] = value_text
                elif 'statut' in header_text and 'org' in header_text:
                    # Extract statutory body members from nested content
                    self._extract_persons_from_section(value_cell, data, 'statutory_body')
                elif 'spole' in header_text and ('cn' in header_text or 'kci' in header_text):
                    # Extract shareholders from nested content
                    self._extract_persons_from_section(value_cell, data, 'shareholders')

        # Also try to find persons by looking for "jednatel" or "společník" headers
        for header in soup.find_all('div', class_='vr-hlavicka'):
            header_text = header.get_text(strip=True).lower()

            if 'jednatel' in header_text or 'predstavenstv' in header_text:
                # Find parent content div
                parent = header.find_parent('div', class_='aunp-content')
                if parent:
                    self._extract_persons_from_section(parent, data, 'statutory_body')

            elif 'spolecn' in header_text or 'akcionar' in header_text:
                parent = header.find_parent('div', class_='aunp-content')
                if parent:
                    self._extract_persons_from_section(parent, data, 'shareholders')

        return data

    def _extract_persons_from_section(self, container, data: dict, field: str):
        """Extract person names from a section container.

        Args:
            container: BeautifulSoup element containing person data
            data: Data dictionary to update
            field: Field name ('statutory_body' or 'shareholders')
        """
        if not container:
            return

        # Look for person entries - they typically have "dat. nar." or dates
        text = container.get_text(strip=True)

        # Pattern: "NAME, dat. nar. DATE" or "NAME, nar. DATE"
        # Split by common delimiters and look for names
        patterns = [
            r'([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž\s]+),\s*(?:dat\.)?\s*nar\.',
            r'([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž\s]+)\s*,\s*\d{1,2}\.\s*\w+\s*\d{4}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                name = match.strip()
                # Skip if it's a header or too short
                if name and len(name) > 3 and name.lower() not in ['jednatel', 'společník', 'akcionář']:
                    if name not in data[field]:
                        data[field].append(name)

    def _parse_detail_page_for_holders(self, html: str) -> List[Dict[str, Any]]:
        """Parse detail page to extract shareholders and board members.

        Note: justice.cz doesn't contain beneficial owner data directly - that's
        in ESM register (restricted). justice.cz only has shareholders and
        statutory body members.

        Args:
            html: HTML content from detail page (úplný výpis)

        Returns:
            List of Holder objects
        """
        holders = []
        soup = BeautifulSoup(html, 'lxml')

        # Look for sections containing shareholder/board member data
        # Common section headers:
        # - "Společníci" (shareholders for s.r.o.)
        # - "Akcionáři" (shareholders for a.s.)
        # - "Statutární orgán" (statutory body)
        # - "Představenstvo" (board of directors)
        # - "Dozorčí rada" (supervisory board)

        section_patterns = {
            'shareholder': ['společník', 'akcionář'],
            'statutory_body': ['statutární orgán', 'představenstvo', 'jednatel'],
            'supervisory_board': ['dozorčí rada'],
        }

        # Find all div sections with class vr-hlavicka (section headers)
        for header in soup.find_all('div', class_='vr-hlavicka'):
            header_text = header.get_text(strip=True).lower()

            # Determine section type
            section_type = None
            for stype, patterns in section_patterns.items():
                if any(p in header_text for p in patterns):
                    section_type = stype
                    break

            if not section_type:
                continue

            # Get the content div (next sibling or parent's next sibling)
            content = header.find_next_sibling('div', class_='vr-child')
            if not content:
                parent = header.parent
                content = parent.find_next_sibling('div', class_='vr-child') if parent else None

            if not content:
                continue

            # Extract persons from content
            if section_type == 'shareholder':
                holders.extend(self._extract_shareholders_from_section(content))
            elif section_type == 'statutory_body':
                holders.extend(self._extract_board_members_from_section(content))

        return holders

    def _extract_shareholders_from_section(self, section) -> List[Dict[str, Any]]:
        """Extract shareholder information from a section.

        Args:
            section: BeautifulSoup element containing shareholder data

        Returns:
            List of Holder dictionaries
        """
        holders = []

        # Look for person entries
        for person_div in section.find_all('div', recursive=True):
            text = person_div.get_text(strip=True)
            if not text:
                continue

            # Try to extract name and ownership percentage
            # Patterns:
            # - "Jan Novák, nar. 1.1.1980"
            # - "Company s.r.o., IČO: 12345678"
            # - ownership might be in separate element

            name = None
            ownership_pct = None

            # Check for name (usually first line or in strong tag)
            strong = person_div.find('strong')
            if strong:
                name = strong.get_text(strip=True)
            elif text:
                # Take first part before comma or date
                parts = re.split(r',|\s+nar\.\s+', text)
                if parts:
                    name = parts[0].strip()

            if name and len(name) > 2:
                # Try to find ownership percentage
                pct_match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', text)
                if pct_match:
                    ownership_pct = float(pct_match.group(1).replace(',', '.'))

                # Determine if individual or entity
                holder_type = 'entity' if any(x in name.lower() for x in ['s.r.o.', 'a.s.', 'spol.', 'k.s.', 'v.o.s.']) else 'individual'

                holder = {
                    'holder_type': holder_type,
                    'role': 'shareholder',
                    'name': name,
                    'ownership_pct_direct': ownership_pct,
                    'voting_rights_pct': ownership_pct,  # Often same for simple cases
                }
                holders.append(holder)

        return holders

    def _extract_board_members_from_section(self, section) -> List[Dict[str, Any]]:
        """Extract board member information from a section.

        Args:
            section: BeautifulSoup element containing board member data

        Returns:
            List of Holder dictionaries
        """
        holders = []

        # Look for person entries
        for person_div in section.find_all('div', recursive=True):
            text = person_div.get_text(strip=True)
            if not text:
                continue

            name = None
            role = 'statutory_body'

            # Check for name
            strong = person_div.find('strong')
            if strong:
                name = strong.get_text(strip=True)
            elif text:
                parts = re.split(r',|\s+nar\.\s+', text)
                if parts:
                    name = parts[0].strip()

            # Try to determine role
            if 'jednatel' in text.lower():
                role = 'managing_director'
            elif 'předseda' in text.lower():
                role = 'chairman'
            elif 'místopředseda' in text.lower():
                role = 'vice_chairman'
            elif 'člen' in text.lower():
                role = 'board_member'
            elif 'ředitel' in text.lower():
                role = 'director'

            if name and len(name) > 2:
                holder = {
                    'holder_type': 'individual',
                    'role': role,
                    'name': name,
                    'ownership_pct_direct': None,
                    'voting_rights_pct': None,
                }
                holders.append(holder)

        return holders

    def get_or_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get commercial register data (alias for search_by_id).

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary or None
        """
        return self.search_by_id(ico)

    def get_shareholders(self, ico: str) -> List[Dict[str, Any]]:
        """Extract shareholders from detail page.

        Args:
            ico: Company identification number

        Returns:
            List of shareholder dictionaries
        """
        result = self.search_by_id(ico)
        if not result:
            return []

        url_uplny = result.get('url_uplny')
        if not url_uplny:
            # Return empty list if no detail page available
            return []

        try:
            detail = self.get_detail_page(url_uplny)
            if detail and detail.get('raw_html'):
                return self._parse_detail_page_for_holders(detail['raw_html'])
        except Exception as e:
            self.logger.error(f"Error fetching shareholders for {ico}: {e}")

        return []

    def get_board_members(self, ico: str) -> List[Dict[str, Any]]:
        """Extract board members from detail page.

        Args:
            ico: Company identification number

        Returns:
            List of board member dictionaries
        """
        # Same implementation as get_shareholders since both are in detail page
        return self.get_shareholders(ico)

    def get_filing_history(self, ico: str) -> List[Dict[str, Any]]:
        """Get filing history (stub - requires different endpoint).

        Args:
            ico: Company identification number

        Returns:
            List of filing records (empty for now)
        """
        # Filing history is in "Sbírka listin" - different endpoint
        # This would require additional implementation
        return []

    def supplement_ares_data(self, ares_data: Dict) -> Dict:
        """Supplement ARES data with justice.cz data.

        Args:
            ares_data: Data from ARES scraper

        Returns:
            Enhanced data dictionary with commercial register info
        """
        ico = ares_data.get('ico')
        if not ico:
            # Try entity structure
            entity = ares_data.get('entity', {})
            ico = entity.get('ico_registry') or entity.get('ico')

        if not ico:
            return ares_data

        justice_data = self.search_by_id(ico)
        if justice_data:
            ares_data['commercial_register'] = {
                'source': self.SOURCE_NAME,
                'file_number': justice_data.get('file_number'),
                'registration_date': justice_data.get('date_registered_text'),
                'url_platny': justice_data.get('metadata', {}).get('register_url'),
                'url_uplny': justice_data.get('url_uplny'),
            }

            # Also add holders if available
            if justice_data.get('holders'):
                ares_data['commercial_register']['holders'] = justice_data['holders']

        return ares_data

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known test entities.

        Mock data from parser-justice-cz examples.

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary with mock data or None
        """
        # Mock data from parser-justice-cz example and ARES
        mock_raw_data = {
            "05984866": {
                "name": "DEVROCK a.s.",
                "ico": "05984866",
                "city": "Praha",
                "addr_city": "Praha 1",
                "addr_zip": "11000",
                "addr_streetnr": "Václavské náměstí 2132/47",
                "addr_full": "Václavské náměstí 2132/47, Nové Město, 11000 Praha 1",
                "den_zapisu_num": "2017-04-03",
                "den_zapisu_txt": "3. dubna 2017",
                "spis_znacka": "B 22379/MSPH",
            },
            "44315945": {
                "name": "Jana Kudláčková",
                "ico": "44315945",
                "city": "Praha",
                "addr_city": "Praha 4",
                "addr_zip": "14900",
                "addr_streetnr": "Filipova 2016",
                "addr_full": "Filipova 2016, PSČ 14900",
                "den_zapisu_num": "1992-08-26",
                "den_zapisu_txt": "26. srpna 1992",
                "spis_znacka": "A 6887 vedená u Městského soudu v Praze",
            },
            "06649114": {
                "name": "Prusa Research a.s.",
                "ico": "06649114",
                "city": "Praha",
                "addr_city": "Praha",
                "addr_zip": "17000",
                "addr_street": "Vlašská",
                "addr_streetnr": "344/15",
                "addr_full": "Vlašská 344/15, 170 00 Praha 7",
                "den_zapisu_num": "2017-09-14",
                "den_zapisu_txt": "14. září 2017",
                "spis_znacka": "B 28291",
            },
            "00216305": {
                "name": "Česká pošta, s.p.",
                "ico": "00216305",
                "city": "Praha",
                "addr_city": "Praha 1",
                "addr_zip": "11499",
                "addr_streetnr": "Poštovní 959/9",
                "addr_full": "Poštovní 959/9, 114 99 Praha 1",
                "den_zapisu_num": "1993-01-01",
                "spis_znacka": "B 5678",
            },
            "00006947": {
                "name": "Ministerstvo financí",
                "ico": "00006947",
                "city": "Praha",
                "addr_city": "Praha 1",
                "addr_zip": "11100",
                "addr_streetnr": "Letenská 15",
                "addr_full": "Letenská 15, 111 00 Praha 1",
                "den_zapisu_num": "1993-01-01",
                "spis_znacka": "A 123",
            },
        }

        if ico not in mock_raw_data:
            return None

        raw = mock_raw_data[ico]

        # Build entity
        entity = Entity(
            ico_registry=raw["ico"],
            company_name_registry=raw["name"],
            status="active",
            incorporation_date=raw.get("den_zapisu_num"),
            registered_address=Address(
                street=raw.get("addr_street") or raw.get("addr_streetnr"),
                city=raw.get("addr_city"),
                postal_code=raw.get("addr_zip"),
                country="Česká republika",
                country_code="CZ",
                full_address=raw.get("addr_full"),
            ) if raw.get("addr_full") else None,
        )

        # Build metadata
        register_url = f"{self.SEARCH_URL}?ico={raw['ico']}"
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
            holders=[],
            tax_info=None,
            metadata=metadata,
        )

        result = output.to_dict()
        result["file_number"] = raw.get("spis_znacka")
        result["date_registered_text"] = raw.get("den_zapisu_txt")

        return result

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in Justice output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="justice")
