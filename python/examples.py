#!/usr/bin/env python3
"""
Example usage of SK/CZ Business Registry Scrapers.

This script demonstrates how to use all available scrapers
and the unified output format.

Run: python examples.py
"""

import json
from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.orsr_slovak import ORSRSlovakScraper
from src.scrapers.rpo_slovak import RpoSlovakScraper
from src.scrapers.rpvs_slovak import RpvsSlovakScraper
from src.scrapers.justice_czech import JusticeCzechScraper
from src.scrapers.esm_czech import EsmCzechScraper
from src.scrapers.financna_sprava_slovak import FinancnaSpravaScraper


def print_result(name: str, result: dict, max_depth: int = 2):
    """Pretty print a scraper result."""
    print(f"\n{'='*60}")
    print(f" {name}")
    print(f"{'='*60}")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
    if len(json.dumps(result)) > 2000:
        print("... (truncated)")


def main():
    print("\n" + "="*60)
    print(" SK/CZ BUSINESS REGISTRY SCRAPERS - EXAMPLES")
    print("="*60)

    # 1. ARES Czech - Working API
    print("\n[1] ARES Czech (Working API)")
    with ARESCzechScraper(enable_snapshots=False) as scraper:
        result = scraper.search_by_id("00006947")  # Ministry of Finance
        if result:
            print(f"Company: {result['entity']['company_name_registry']}")
            print(f"Status: {result['entity']['status']}")
            print(f"VAT Status: {result.get('tax_info', {}).get('vat_status')}")
            print(f"Source: {result['metadata']['source']}")
            print(f"Is Mock: {result['metadata']['is_mock']}")

    # 2. ORSR Slovak - Web Scraper
    print("\n[2] ORSR Slovak (Web Scraper)")
    with ORSRSlovakScraper(enable_snapshots=False) as scraper:
        result = scraper.search_by_id("35763491")  # Slovenská sporiteľňa
        if result:
            print(f"Company: {result['entity']['company_name_registry']}")
            print(f"Status: {result['entity'].get('status')}")
        else:
            print("No result (company may not be found)")

    # 3. RPO Slovak - Mock Data
    print("\n[3] RPO Slovak (Mock Data)")
    with RpoSlovakScraper(enable_snapshots=False) as scraper:
        result = scraper.search_by_id("35763491")
        if result:
            print(f"Company: {result['entity']['company_name_registry']}")
            print(f"Legal Form: {result['entity'].get('legal_form')}")
            print(f"Is Mock: {result['metadata']['is_mock']}")

    # 4. RPVS Slovak - UBO Data
    print("\n[4] RPVS Slovak (UBO Data - Mock)")
    with RpvsSlovakScraper(enable_snapshots=False) as scraper:
        result = scraper.search_by_id("35763491")
        if result:
            print(f"Company: {result['entity']['company_name_registry']}")
            print(f"Holders: {len(result.get('holders', []))}")
            for holder in result.get("holders", []):
                print(f"  - {holder['name']} ({holder['holder_type']})")
                print(f"    Ownership: {holder['ownership_pct_direct']}%")

    # 5. Justice Czech - Mock Data
    print("\n[5] Justice Czech (Mock Data)")
    with JusticeCzechScraper(enable_snapshots=False) as scraper:
        result = scraper.search_by_id("06649114")  # Prusa Research
        if result:
            print(f"Company: {result['entity']['company_name_registry']}")
            print(f"Holders: {len(result.get('holders', []))}")
            shareholders = [h for h in result.get("holders", []) if h.get("role") == "shareholder"]
            board = [h for h in result.get("holders", []) if h.get("role") == "statutory_body"]
            print(f"  Shareholders: {len(shareholders)}")
            print(f"  Board Members: {len(board)}")

    # 6. ESM Czech - Restricted
    print("\n[6] ESM Czech (Restricted - Mock Data)")
    with EsmCzechScraper(enable_snapshots=False) as scraper:
        # Check access requirements
        req = scraper.get_access_requirements()
        print(f"Access Required: {req['qualification']}")
        print(f"Website: {req['website']}")

        result = scraper.search_by_id("06649114")
        if result:
            print(f"Company: {result['entity']['company_name_registry']}")
            print(f"Holders: {len(result.get('holders', []))}")

    # 7. Finančná správa - Tax Info
    print("\n[7] Finančná správa (Tax Info - Mock)")
    with FinancnaSpravaScraper(enable_snapshots=False) as scraper:
        result = scraper.search_by_id("35763491")
        if result:
            print(f"Company: {result['entity']['company_name_registry']}")
            tax_info = result.get("tax_info", {})
            print(f"VAT ID: {tax_info.get('vat_id')}")
            print(f"VAT Status: {tax_info.get('vat_status')}")
            debts = tax_info.get("tax_debts", {})
            print(f"Has Debts: {debts.get('has_debts')}")
            print(f"Amount: {debts.get('amount_eur')} EUR")

    # 8. Full JSON Output Example
    print("\n[8] Full JSON Output Example")
    with ARESCzechScraper(enable_snapshots=False) as scraper:
        result = scraper.search_by_id("00006947")
        if result:
            print_result("ARES Full Output", result)

    print("\n" + "="*60)
    print(" EXAMPLES COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
