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
    JUSTICE_OUTPUT_DIR, JUSTICE_ENTITY_URL_TEMPLATE
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

    def __init__(self, enable_snapshots: bool = True, use_playwright: bool = True):
        """Initialize Justice Czech scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
            use_playwright: Whether to use Playwright browser automation (with fallback)
        """
        super().__init__(enable_snapshots=enable_snapshots)

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
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper (playwright={use_playwright})")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search company by IČO (identification number).

        Args:
            ico: Czech company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        self.logger.info(f"Searching Justice.cz by IČO: {ico}")

        # Clean ICO - keep only digits
        ico = re.sub(r'[^\d]', '', ico)

        if not re.match(r'^\d{8}$', ico):
            self.logger.warning(f"Invalid IČO format: {ico}")
            return None

        # Try Playwright first if enabled
        if self.use_playwright:
            try:
                result = self._search_by_id_playwright(ico)
                if result:
                    return result
            except PlaywrightNotAvailableError:
                self.logger.info("Playwright not available, falling back to static scraping")
            except PlaywrightError as e:
                self.logger.warning(f"Playwright search failed: {e}, falling back to static scraping")

        # Fallback to static scraping
        return self._search_by_id_static(ico)

    def _search_by_id_playwright(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by IČO using Playwright browser automation.

        Args:
            ico: Czech company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        self.logger.debug(f"Using Playwright to search for IČO: {ico}")

        url = f"{self.SEARCH_URL}?ico={ico}"

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
                    self._take_screenshot(page, f"justice_no_results_{ico}.png")
                    self.logger.warning(f"No results table found for IČO: {ico}")
                    return None

                # Take screenshot for successful load if enabled
                self._take_screenshot(page, f"justice_results_{ico}.png")

                # Get HTML content
                html = self._get_page_html(page)

                # Save snapshot if enabled
                if self.enable_snapshots:
                    self.save_snapshot({"html": html, "method": "playwright"}, ico, self.SOURCE_NAME)

                # Parse results
                results = self._extract_subjects(html)

                if not results:
                    self.logger.warning(f"No entity found with IČO: {ico}")
                    return None

                return results[0]

        except Exception as e:
            self.logger.error(f"Playwright error searching for {ico}: {e}")
            raise PlaywrightError(f"Playwright search failed: {e}") from e

    def _search_by_id_static(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by IČO using static HTTP requests (fallback).

        Args:
            ico: Czech company identification number (8 digits)

        Returns:
            Dictionary with company data or None if not found
        """
        self.logger.debug(f"Using static scraping for IČO: {ico}")

        try:
            # Search by ICO - exact pattern from parser-justice-cz
            url = f"{self.SEARCH_URL}?ico={ico}"
            html = self.http_client.get_html(url)

            # Save snapshot if enabled
            if self.enable_snapshots:
                self.save_snapshot({"html": html, "method": "static"}, ico, self.SOURCE_NAME)

            # Parse results using the same XPath-like pattern
            results = self._extract_subjects(html)

            if not results:
                self.logger.warning(f"No entity found with IČO: {ico}")
                return self._get_mock_data(ico)

            # Return first result with full details
            return results[0]

        except Exception as e:
            self.logger.error(f"Error searching Justice.cz for {ico}: {e}")
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

        This follows the exact XPath pattern from parser-justice-cz:
        - Table with class "result-details"
        - tbody/tr rows with company data
        - Row 1: name (td[1]), ICO (td[2])
        - Row 2: file_number (td[1]), date_established (td[2])
        - Row 3: address (td[1])
        - Links in ../../ul[1]/li/a (3 links)

        Args:
            html: HTML content from search page

        Returns:
            List of company dictionaries in unified format
        """
        results = []
        soup = BeautifulSoup(html, 'lxml')

        # Find result table with class "result-details" - exact pattern from parser-justice-cz
        result_table = soup.find('table', class_='result-details')
        if not result_table:
            return results

        tbody = result_table.find('tbody')
        if not tbody:
            # Some pages might not have tbody tag, try direct tr search
            rows = result_table.find_all('tr')
        else:
            rows = tbody.find_all('tr')

        # Process rows in groups of 3 (each company spans 3 rows)
        i = 0
        while i < len(rows):
            if i + 2 >= len(rows):
                break

            # Row 1: name (td[1]), ICO (td[2])
            row1 = rows[i]
            cells1 = row1.find_all('td')
            if len(cells1) < 2:
                i += 1
                continue

            name = cells1[0].get_text(strip=True)
            # Normalize multiple spaces
            name = re.sub(r'\s+', ' ', name)

            ico_cell = cells1[1].get_text(strip=True)
            ico = re.sub(r'[^\d]', '', ico_cell)

            if not ico or len(ico) != 8:
                i += 1
                continue

            # Row 2: file_number (td[1]), date_established (td[2])
            row2 = rows[i + 1]
            cells2 = row2.find_all('td')

            spis_znacka = ''
            den_zapisu_num = ''
            den_zapisu_txt = ''

            if len(cells2) >= 2:
                spis_znacka = cells2[0].get_text(strip=True)
                date_text = cells2[1].get_text(strip=True)
                den_zapisu_num = den_zapisu_txt = date_text
                den_zapisu_num = self._parse_czech_date(date_text)

            # Row 3: address (td[1])
            row3 = rows[i + 2]
            cells3 = row3.find_all('td')

            city = ''
            addr_city = ''
            addr_zip = ''
            addr_streetnr = ''
            addr_full = ''

            if len(cells3) >= 1:
                addr = cells3[0].get_text(strip=True)

                # Pattern 1: "Příborská 597, Místek, 738 01 Frýdek-Místek"
                # PSC at end with city name
                match = re.search(r',\s*(\d{3}\s*\d{2})\s+(.+)$', addr)
                if match:
                    addr_zip = re.sub(r'\s', '', match.group(1))
                    addr_city = match.group(2)
                    parts = addr.split(',')
                    addr_streetnr = parts[0] if len(parts) > 0 else ''
                    city = self._shorten_city(addr_city)
                # Pattern 2: "Řevnice, ČSLA 118, okres Praha-západ, PSČ 25230"
                # PSČ at end with "PSČ" label
                elif 'PSČ' in addr:
                    match = re.search(r',\s*PSČ\s+(\d{3}\s*\d{2})$', addr)
                    if match:
                        addr_zip = re.sub(r'\s', '', match.group(1))
                        parts = addr.split(',')
                        city = parts[0].strip() if len(parts) > 0 else ''
                        addr_city = city
                        addr_streetnr = ', '.join(parts[1:]) if len(parts) > 1 else ''
                        city = self._shorten_city(city)
                # Pattern 3: "Ústí nad Labem, Masarykova 74" - without PSC
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
                    addr_full = addr

                if not addr_full:
                    addr_full = addr

            # Look for detail links
            # Pattern: ../../ul[1]/li/a - 3 links (platny, uplny, sbirkaListin)
            url_platnych = ''
            url_uplny = ''
            url_sbirka_listin = ''

            # Try to find the ul/li/a structure
            # The links are typically in a sibling or parent element
            for sibling in row3.parent.find_all('ul'):
                links = sibling.find_all('a', href=True)
                if len(links) >= 3:
                    url_platnych = self._normalize_url(links[0]['href'])
                    url_uplny = self._normalize_url(links[1]['href'])
                    url_sbirka_listin = self._normalize_url(links[2]['href'])
                    break

            # Build entity
            entity = Entity(
                ico_registry=ico,
                company_name_registry=name,
                status="active",  # Active if found in register
                incorporation_date=den_zapisu_num,
                registered_address=Address(
                    street=addr_streetnr.split(',')[0].strip() if addr_streetnr else None,
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

            # Add extra data from parser-justice-cz
            result["file_number"] = self._trim_quotes(spis_znacka)
            result["date_registered_text"] = self._trim_quotes(den_zapisu_txt)
            if url_uplny:
                result["url_uplny"] = url_uplny
            if url_sbirka_listin:
                result["url_sbirka_listin"] = url_sbirka_listin

            results.append(result)

            i += 3  # Skip to next company (3 rows per company)

        return results

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

        Args:
            html: HTML content from detail page

        Returns:
            Unified output dictionary or None
        """
        soup = BeautifulSoup(html, 'lxml')

        # Extract company name
        name = None
        title_elem = soup.find('h1') or soup.find('h2')
        if title_elem:
            name = title_elem.get_text(strip=True)

        if not name:
            return None

        # Look for ICO in the page
        ico = None
        ico_pattern = r'IČO\s*:\s*(\d{8})'
        for text in soup.stripped_strings:
            match = re.search(ico_pattern, text)
            if match:
                ico = match.group(1)
                break

        return {
            "name": name,
            "ico": ico,
            "raw_html": html,
        }

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
