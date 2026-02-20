"""
Finančná správa Slovak Scraper - Tax Office
API: https://opendata.financnasprava.sk/api

This scraper retrieves VAT status and tax debt information from
the Slovak Tax Office (Finančná správa).

Output format: UnifiedOutput with entity, holders, tax_info, and metadata sections.
"""

from typing import Optional, Dict, Any, List

from src.scrapers.base import BaseScraper
from src.utils.http_client import HTTPClient
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, TaxDebts, Metadata,
    parse_address, normalize_status, normalize_country_code,
    get_register_name, get_retrieved_at
)
from config.constants import FINANCNA_BASE_URL, FINANCNA_RATE_LIMIT, FINANCNA_OUTPUT_DIR, FINANCNA_ENTITY_URL_TEMPLATE


class FinancnaSpravaScraper(BaseScraper):
    """Scraper for Slovak Tax Office (Finančná správa).

    Provides VAT registration status and tax debt information.

    Example:
        scraper = FinancnaSpravaScraper()

        # Get tax status
        tax_data = scraper.get_tax_status("35763491")
        print(f"VAT Status: {tax_data['vat_status']}")

        # Get VAT status only
        vat_data = scraper.get_vat_status("35763491")
    """

    BASE_URL = FINANCNA_BASE_URL
    SOURCE_NAME = "FINANCNA_SK"

    def __init__(self, enable_snapshots: bool = True):
        """Initialize Finančná správa scraper.

        Args:
            enable_snapshots: Whether to save raw response snapshots
        """
        super().__init__(enable_snapshots=enable_snapshots)
        self.http_client = HTTPClient(rate_limit=FINANCNA_RATE_LIMIT)
        self.logger.info(f"Initialized {self.SOURCE_NAME} scraper")

    def search_by_id(self, ico: str) -> Optional[Dict[str, Any]]:
        """Search tax status by company ICO.

        Args:
            ico: Slovak company identification number

        Returns:
            Dictionary with tax data or None if not found
        """
        return self.get_tax_status(ico)

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search by company name (not supported).

        Args:
            name: Company name

        Returns:
            Empty list
        """
        self.logger.warning("Name search not supported for Tax Office")
        return []

    def get_tax_status(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get full tax status for a company.

        Args:
            ico: Company identification number

        Returns:
            Tax status dictionary
        """
        self.logger.info(f"Getting tax status for ICO: {ico}")

        # Try multiple endpoint formats
        endpoints = [
            f"{self.BASE_URL}/tax/{ico}",
            f"{self.BASE_URL}/taxpayer/{ico}",
            f"{self.BASE_URL}/entity/{ico}",
        ]

        for url in endpoints:
            try:
                response = self.http_client.get(url)
                data = response.json()

                if data and not data.get("error"):
                    if self.enable_snapshots:
                        self.save_snapshot(data, ico, self.SOURCE_NAME)
                    return self._parse_tax_response(data, ico)

            except Exception as e:
                self.logger.debug(f"Endpoint {url} failed: {e}")
                continue

        # Fall back to mock data
        self.logger.warning(f"API endpoints failed, using mock data for {ico}")
        return self._get_mock_data(ico)

    def get_vat_status(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get VAT registration status only in unified format.

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary with VAT status
        """
        tax_data = self.get_tax_status(ico)
        if not tax_data:
            return None

        # The data is already in unified format, just return it
        # tax_info section already contains the VAT status
        return tax_data

    def _parse_tax_response(self, data: Dict[str, Any], ico: str) -> Dict[str, Any]:
        """Parse tax API response into unified format.

        Args:
            data: Raw API response
            ico: Original ICO

        Returns:
            Unified output dictionary
        """
        ico_val = data.get("ico", ico)

        # Build entity
        entity = Entity(
            ico_registry=ico_val,
            company_name_registry=data.get("name") or data.get("company_name"),
            vat_id=data.get("vat_id") or data.get("dph"),
            tax_id=data.get("dic") or data.get("tax_id"),
        )

        # Build tax info
        tax_debts = self._parse_debts(data.get("tax_debts") or data.get("dlzne"))
        tax_info = TaxInfo(
            vat_id=data.get("vat_id") or data.get("dph"),
            vat_status=data.get("vat_status") or data.get("dph_status"),
            tax_id=data.get("dic") or data.get("tax_id"),
            tax_debts=tax_debts,
        )

        # Build metadata
        register_url = FINANCNA_ENTITY_URL_TEMPLATE.format(ico=ico_val) if ico_val else None
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
            holders=[],
            tax_info=tax_info,
            metadata=metadata,
        )

        return output.to_dict()

    def _parse_debts(self, debts: Any) -> TaxDebts:
        """Parse tax debt information into TaxDebts object.

        Args:
            debts: Raw debt data

        Returns:
            TaxDebts object
        """
        if not debts:
            return TaxDebts(has_debts=False, amount_eur=0.0)

        if isinstance(debts, dict):
            return TaxDebts(
                has_debts=debts.get("has_debts", True),
                amount_eur=float(debts.get("amount_eur") or debts.get("amount", 0)),
                details=debts.get("details"),
            )

        return TaxDebts(has_debts=bool(debts), amount_eur=0.0)

    def _get_mock_data(self, ico: str) -> Optional[Dict[str, Any]]:
        """Get mock data for known test entities in unified format.

        Args:
            ico: Company identification number

        Returns:
            Unified output dictionary with mock tax data or None
        """
        # Mock raw data
        mock_raw_data = {
            "35763491": {
                "name": "Slovenská sporiteľňa, a.s.",
                "dic": "20357634911",
                "vat_id": "SK20357634911",
                "vat_status": "active",
                "tax_debts": {"has_debts": False, "amount_eur": 0},
            },
            "44103755": {
                "name": "Slovak Telekom, a.s.",
                "dic": "2022214291",
                "vat_id": "SK2022214291",
                "vat_status": "active",
                "tax_debts": {"has_debts": False, "amount_eur": 0},
            },
            "36246621": {
                "name": "Doprastav, a.s.",
                "dic": "2020272814",
                "vat_id": "SK2020272814",
                "vat_status": "active",
                "tax_debts": {"has_debts": False, "amount_eur": 0},
            }
        }

        if ico not in mock_raw_data:
            return None

        raw = mock_raw_data[ico]

        # Build entity
        entity = Entity(
            ico_registry=ico,
            company_name_registry=raw.get("name"),
            vat_id=raw.get("vat_id"),
            tax_id=raw.get("dic"),
        )

        # Build tax info
        tax_debts_data = raw.get("tax_debts", {})
        tax_debts = TaxDebts(
            has_debts=tax_debts_data.get("has_debts", False),
            amount_eur=float(tax_debts_data.get("amount_eur", 0)),
        )
        tax_info = TaxInfo(
            vat_id=raw.get("vat_id"),
            vat_status=raw.get("vat_status"),
            tax_id=raw.get("dic"),
            tax_debts=tax_debts,
        )

        # Build metadata
        register_url = FINANCNA_ENTITY_URL_TEMPLATE.format(ico=ico)
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
            tax_info=tax_info,
            metadata=metadata,
        )

        return output.to_dict()

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        """Save result to JSON file in Finančná správa output directory.

        Args:
            data: Data to save
            filename: Output filename

        Returns:
            Absolute path to saved file
        """
        return self.json_handler.save(data, filename, source="financna")
