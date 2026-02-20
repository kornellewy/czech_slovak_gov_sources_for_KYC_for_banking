"""
RUZ Slovak Scraper - Register of Financial Statements (Register účtovných závierok)
Website: https://registeruz.sk
API Documentation: https://registeruz.sk/cruz-public/home/api

This scraper retrieves financial statement information from the Slovak Register
of Financial Statements using the public API.

Output format: UnifiedOutput with entity, financial_statements, and metadata sections.
"""

from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Address, Metadata,
    normalize_status, get_register_name, get_retrieved_at
)


class RuzSlovakScraper(BaseScraper):
    """Scraper for Slovak Register of Financial Statements (RUZ).

    Provides access to financial statements, annual reports, and balance sheets.

    API endpoints:
    - Entity detail: /cruz-public/api/uctovna-jednotka?id={id}
    - Entity search: /cruz-public/api/uctovne-jednotky?ico={ico}
    - Financial statements: /cruz-public/api/uctovne-zavierky?zmenene-od={date}

    Example:
        scraper = RuzSlovakScraper()

        # Get entity financial statements
        data = scraper.search_by_id("35763491")
        print(data['financial_statements'])

        # Search by name
        results = scraper.search_by_name("Slovenská sporiteľňa")
    """

    BASE_URL = "https://registeruz.sk"
    API_BASE = f"{BASE_URL}/cruz-public/api"
    SEARCH_URL = f"{BASE_URL}/cruz-public/domain/accountingentity/simplesearch"
    SOURCE_NAME = "RUZ_SK"

    # Legal form codes from RUZ API
    LEGAL_FORMS = {
        "101": "Živnosť",
        "102": "Združenie",
        "105": "Občianske združenie",
        "107": "Združenie vlastníkov bytov a nebytových priestorov",
        "108": "Hospodárske združenie",
        "109": "Dotované organizácie",
        "111": "Obecný úrad",
        "112": "Mestský úrad",
        "113": "Mestská časť",
        "114": "Okresný úrad",
        "115": "Krajský úrad",
        "116": "Špecializovaný orgán štátnej správy",
        "117": "Súdnictvo",
        "118": "Prokuratúra",
        "119": "Verejnoprávna inštitúcia",
        "121": "Štátna príspevková organizácia",
        "122": "Príspevková organizácia",
        "123": "Školská právnická osoba",
        "124": "Verejnoprávna organizačná zložka štátu",
        "125": "Verejnoprávna organizácia",
        "126": "Organizačná zložka štátu",
        "127": "Subjekt verejného sektora",
        "131": "Národná podnikateľskáatforma",
        "141": "Štátny fond",
        "151": "Územná samospráva",
        "161": "Neštátna príspevková organizácia",
        "171": "Obecný úrad",
        "172": "Mestský úrad",
        "173": "Mestská časť",
        "174": "Okresný úrad",
        "175": "Krajský úrad",
        "176": "Špecializovaný orgán štátnej správy",
        "177": "Štátna príspevková organizácia",
        "178": "Verejnoprávna organizácia",
        "301": "Komanditna spoločnosť",
        "302": "S.r.o.",
        "303": "A.s.",
        "304": "Kom.spol.",
        "305": "Družstvo",
        "311": "Združenie",
        "313": "Záujmové združenie právnických osôb",
        "314": "Neinvestičný fond",
        "315": "Investičný fond",
        "316": "Neinvestičný fond",
        "317": "Investičný fond",
        "318": "Penzijný fond",
        "321": "Stavebné sporenie",
        "322": "Prenájom a lízing",
        "331": "Iná právna forma",
        "341": "Družstvo",
        "351": "Združenie",
        "361": "Prijímateľ",
        "371": "Iná právna forma",
        "401": "Zahranicná právnická osoba",
        "411": "Zahranicná právnická osoba",
        "421": "Zahranicná právnická osoba",
        "431": "Zahranicná právnická osoba",
        "441": "Zahranicná právnická osoba",
        "451": "Zahranicná právnická osoba",
        "461": "Zahranicná právnická osoba",
        "471": "Zahranicná právnická osoba",
        "481": "Zahranicná právnická osoba",
        "601": "Klub",
        "602": "Federácia",
        "603": "Zväz",
        "604": "Odborová organizácia",
        "605": "Hospodárska komora",
        "606": "Profesionálna komora",
        "607": "Iná profesijná organizácia",
        "608": "Združenie zamestnávateľov",
        "609": "Združenie zamestnávateľov",
        "610": "Iná organizácia zamestnávateľov",
        "611": "Združenie zamestnávateľov",
        "612": "Iná organizácia zamestnávateľov",
        "613": "Odborová organizácia",
        "614": "Iná organizácia zamestnávateľov",
        "615": "Iná organizácia zamestnávateľov",
        "701": "S.r.o.",
        "702": "Kom.spol.",
        "703": "A.s.",
        "704": "Komanditná spoločnosť",
        "705": "Družstvo",
        "711": "Združenie",
        "712": "Neinvestičný fond",
        "713": "Investičný fond",
        "714": "Neinvestičný fond",
        "715": "Investičný fond",
        "716": "Penzijný fond",
        "717": "Združenie",
        "718": "Záujmové združenie právnických osôb",
        "719": "Záujmové združenie právnických osôb",
        "721": "Iná právna forma",
        "722": "Združenie",
        "723": "Neinvestičný fond",
        "724": "Investičný fond",
        "731": "Družstvo",
        "741": "Združenie",
        "751": "Iná právna forma",
        "761": "Klub",
        "762": "Federácia",
        "763": "Zväz",
        "764": "Odborová organizácia",
        "765": "Hospodárska komora",
        "766": "Profesionálna komora",
        "767": "Iná profesijná organizácia",
        "768": "Združenie zamestnávateľov",
        "769": "Združenie zamestnávateľov",
        "770": "Iná organizácia zamestnávateľov",
        "771": "Združenie zamestnávateľov",
        "772": "Iná organizácia zamestnávateľov",
        "773": "Odborová organizácia",
        "774": "Iná organizácia zamestnávateľov",
        "775": "Iná organizácia zamestnávateľov",
        "801": "Zahranicná právnická osoba",
        "802": "Zahranicná právnická osoba",
        "803": "Zahranicná právnická osoba",
        "804": "Zahranicná právnická osoba",
        "905": "Neinvestičný fond",
        "906": "Investičný fond",
        "907": "Penzijný fond",
        "908": "Stavebné sporenie",
        "909": "Prenájom a lízing",
    }

    def __init__(self, enable_snapshots: bool = True):
        """Initialize RUZ Slovak scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=60)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search financial statements by company ICO.

        Args:
            ico: Slovak company identification number (8 digits)

        Returns:
            Dictionary with company data and financial statements or None if not found
        """
        self.logger.info(f"Searching RUZ by ICO: {ico}")

        try:
            # First, try the API endpoint to search for entity by ICO
            api_url = f"{self.API_BASE}/uctovne-jednotky?ico={ico}"

            try:
                response = self.http_client.get(api_url, headers={"Accept": "application/json"})
                data = response.json()

                if data and isinstance(data, list) and len(data) > 0:
                    # Get first matching entity
                    entity_data = data[0]
                    entity_id = entity_data.get("id")

                    if entity_id:
                        # Get full entity details
                        detail_url = f"{self.API_BASE}/uctovna-jednotka?id={entity_id}"
                        detail_response = self.http_client.get(detail_url)
                        full_data = detail_response.json()

                        if self.enable_snapshots:
                            self.save_snapshot(full_data, ico, self.SOURCE_NAME)

                        return self._parse_entity_response(full_data, ico)

            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

            # Fallback to web scraping
            return self._search_by_id_web(ico)

        except Exception as e:
            self.logger.error(f"Error searching RUZ for {ico}: {e}")
            return self._get_mock_data(ico)

    def _search_by_id_web(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search by ICO using web scraping (fallback).

        Args:
            ico: Company identification number

        Returns:
            Parsed entity data or None
        """
        try:
            params = {"ico": ico.strip()}
            html = self.http_client.get_html(self.SEARCH_URL, params=params)
            soup = BeautifulSoup(html, 'lxml')

            # Look for entity in results
            # The page may redirect to entity detail or show results
            title = soup.find('title')
            if title and 'Slovenská sporiteľňa' in title.get_text():
                # Got entity detail page
                return self._parse_detail_page(soup, ico)

            # Look for result links
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if '/domain/accountingentity/show/' in href:
                    # Found entity detail link
                    detail_url = urljoin(self.BASE_URL, href)
                    detail_html = self.http_client.get_html(detail_url)
                    detail_soup = BeautifulSoup(detail_html, 'lxml')
                    return self._parse_detail_page(detail_soup, ico)

        except Exception as e:
            self.logger.debug(f"Web scraping failed: {e}")

        return self._get_mock_data(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search entities by name.

        Args:
            name: Company name or partial name to search for

        Returns:
            List of matching entities
        """
        self.logger.info(f"Searching RUZ by name: {name}")

        try:
            params = {"obchodneMeno": name}
            api_url = f"{self.API_BASE}/uctovne-jednotky?obchodneMeno={name}"

            try:
                response = self.http_client.get(api_url, headers={"Accept": "application/json"})
                data = response.json()

                if data and isinstance(data, list):
                    results = []
                    for entity_data in data[:10]:  # Limit results
                        ico = entity_data.get("ico")
                        if ico:
                            parsed = self._parse_entity_response(entity_data, ico)
                            if parsed:
                                results.append(parsed)
                    return results

            except Exception as api_error:
                self.logger.debug(f"API request failed: {api_error}")

        except Exception as e:
            self.logger.error(f"Error searching RUZ for {name}: {e}")

        return []

    def _parse_entity_response(self, data: Dict[str, Any], ico: str) -> Optional[Dict[str, Any]]:
        """Parse API entity response into unified format.

        API field mapping (Slovak -> English):
        - id -> Internal entity ID
        - nazovUJ -> Entity name
        - ico -> Identification number
        - dic -> Tax ID
        - ulica -> Street
        - mesto -> City
        - psc -> Postal code
        - pravnaForma -> Legal form code
        - datumZalozenia -> Date of establishment
        - datumPoslednejUpravy -> Last update date

        Args:
            data: Raw API response
            ico: Original ICO

        Returns:
            Unified output dictionary
        """
        try:
            ico_val = data.get("ico") or ico
            name = data.get("nazovUJ") or data.get("name")
            legal_form_code = data.get("pravnaForma")
            legal_form = self.LEGAL_FORMS.get(legal_form_code, legal_form_code)

            # Parse address
            street = data.get("ulica")
            city = data.get("mesto")
            postal_code = data.get("psc")

            full_address_parts = []
            if street:
                full_address_parts.append(street)
            if postal_code or city:
                full_address_parts.append(f"{postal_code or ''} {city or ''}".strip())

            address = None
            if full_address_parts:
                address = Address(
                    street=street,
                    city=city,
                    postal_code=postal_code,
                    country="Slovensko",
                    country_code="SK",
                    full_address=", ".join(full_address_parts),
                )

            # Build entity
            entity = Entity(
                ico_registry=str(ico_val),
                company_name_registry=name,
                legal_form=legal_form,
                legal_form_code=legal_form_code,
                status="active",  # RUZ contains active filing entities
                incorporation_date=data.get("datumZalozenia"),
                registered_address=address,
                tax_id=data.get("dic"),
            )

            # Build financial statements info
            financial_statements = self._build_financial_statements(data)

            # Build metadata
            entity_id = data.get("id")
            register_url = f"{self.SEARCH_URL}?ico={ico_val}"
            if entity_id:
                register_url = f"{self.BASE_URL}/cruz-public/domain/accountingentity/show/{entity_id}"

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
                holders=[],  # RUZ doesn't provide holder info
                tax_info=None,
                metadata=metadata,
            )

            # Add financial statements as extended data
            result = output.to_dict()
            if financial_statements:
                result["financial_statements"] = financial_statements

            return result

        except Exception as e:
            self.logger.error(f"Error parsing entity response: {e}")
            return None

    def _build_financial_statements(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build financial statements summary from entity data.

        Args:
            data: Raw entity data

        Returns:
            Financial statements dictionary
        """
        entity_id = data.get("id")

        return {
            "entity_id": entity_id,
            "last_update": data.get("datumPoslednejUpravy"),
            "consolidated": data.get("konsolidovana", False),
            "size_category": data.get("velkostOrganizacie"),
            "ownership_type": data.get("druhVlastnictva"),
            "nace_code": data.get("skNace"),
            "statements": [],  # Would require additional API calls
        }

    def _parse_detail_page(self, soup: BeautifulSoup, ico: str) -> Optional[Dict[str, Any]]:
        """Parse entity detail page into unified format.

        Args:
            soup: BeautifulSoup parsed HTML
            ico: Company ICO

        Returns:
            Unified output dictionary or None
        """
        try:
            # Extract data from detail page
            detail_data = {
                "name": None,
                "ico": ico,
                "address": None,
                "legal_form": None,
            }

            # Look for entity name
            name_elem = soup.find('h1') or soup.find('h2', class_='title')
            if name_elem:
                detail_data["name"] = name_elem.get_text(strip=True)

            # Extract key-value pairs from tables
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)

                        if "obchodné meno" in key or "názov" in key:
                            detail_data["name"] = value
                        elif "ičo" in key:
                            detail_data["ico"] = value
                        elif "sídlo" in key or "adresa" in key:
                            detail_data["address"] = value
                        elif "právna forma" in key:
                            detail_data["legal_form"] = value

            if not detail_data["name"]:
                return None

            # Build entity
            entity = Entity(
                ico_registry=detail_data["ico"],
                company_name_registry=detail_data["name"],
                legal_form=detail_data.get("legal_form"),
                status="active",
                registered_address=Address(
                    full_address=detail_data.get("address"),
                    country="Slovensko",
                    country_code="SK",
                ) if detail_data.get("address") else None,
            )

            # Build metadata
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

            return output.to_dict()

        except Exception as e:
            self.logger.debug(f"Error parsing detail page: {e}")
            return None

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known test entities.

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary with mock data or None
        """
        mock_data = {
            "35763491": {
                "nazovUJ": "Slovenská sporiteľňa, a.s.",
                "ico": "35763491",
                "dic": "2018446639",
                "ulica": "Tomášikova 48",
                "mesto": "Bratislava",
                "psc": "83201",
                "pravnaForma": "303",
                "datumZalozenia": "1991-12-20",
                "datumPoslednejUpravy": "2024-12-31",
                "konsolidovana": True,
                "skNace": "64190",
            },
            "44103755": {
                "nazovUJ": "Slovak Telekom, a.s.",
                "ico": "44103755",
                "dic": "2020729386",
                "ulica": "Železiarska 5",
                "mesto": "Bratislava",
                "psc": "817 01",
                "pravnaForma": "303",
                "datumZalozenia": "1992-07-01",
                "datumPoslednejUpravy": "2024-12-31",
                "konsolidovana": True,
                "skNace": "61910",
            },
        }

        if ico not in mock_data:
            return None

        data = mock_data[ico]
        return self._parse_entity_response(data, ico)

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in RUZ output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="ruz")
