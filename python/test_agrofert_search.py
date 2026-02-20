#!/usr/bin/env python3
"""
Search for AGROFERT a.s. across all available scrapers.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.justice_czech import JusticeCzechScraper
import json


# Known AGROFERT related ICOs to try
AGROFERT_ICOS = [
    "25932910",  # Commonly cited AGROFERT a.s. ICO
    "25755241",  # AGROFERT holding a.s.
    "45278749",  # Alternative AGROFERT ICO
    "48153684",  # Another possible AGROFERT ICO
    "25564820",  # Precheza a.s. (AGROFERT subsidiary)
    "25330609",  # Lovo ČR subsidiary
    "27662181",  # Agrofert
]


def search_ares(icos):
    """Search ARES for AGROFERT related ICOs."""
    print("=" * 70)
    print("  Searching ARES Czech for AGROFERT")
    print("=" * 70)

    found = []

    with ARESCzechScraper() as scraper:
        for ico in icos:
            print(f"\n  Trying ICO: {ico}")
            result = scraper.search_by_id(ico)

            if result:
                entity = result.get('entity', {})
                company_name = entity.get('company_name_registry', '')
                is_mock = result.get('metadata', {}).get('is_mock', False)

                print(f"    ✓ Found: {company_name}")
                print(f"    Legal Form: {entity.get('legal_form')}")
                print(f"    Status: {entity.get('status')}")
                print(f"    Is Mock: {is_mock}")

                if 'agrofert' in company_name.lower():
                    print(f"    *** AGROFERT FOUND! ***")
                    found.append((ico, company_name, result))
            else:
                print(f"    ✗ Not found")

    return found


def search_justice_cz(icos):
    """Search Justice Czech (Commercial Register) for AGROFERT."""
    print("\n" + "=" * 70)
    print("  Searching Justice Czech (Obchodní rejstřík) for AGROFERT")
    print("=" * 70)

    found = []

    with JusticeCzechScraper() as scraper:
        for ico in icos:
            print(f"\n  Trying ICO: {ico}")
            result = scraper.get_or_data(ico)

            if result:
                company_name = result.get('company_name', '')
                print(f"    ✓ Found: {company_name}")
                print(f"    Court: {result.get('court')}")
                print(f"    Is Mock: {result.get('mock', False)}")

                if 'agrofert' in company_name.lower():
                    print(f"    *** AGROFERT FOUND! ***")
                    found.append((ico, company_name, result))
            else:
                print(f"    ✗ Not found")

    return found


def test_agrofert_unified_output(ico, company_name, scraper_data):
    """Test and display unified output for AGROFERT."""
    print("\n" + "=" * 70)
    print(f"  UNIFIED OUTPUT FOR: {company_name}")
    print(f"  ICO: {ico}")
    print("=" * 70)

    # Get unified output from the appropriate scraper
    with ARESCzechScraper() as ares:
        result = ares.search_by_id(ico)
        if result:
            print("\n--- entity ---")
            entity = result.get('entity', {})
            for key, value in entity.items():
                if key != 'registered_address':
                    print(f"  {key}: {value}")
                else:
                    print(f"  registered_address:")
                    for ak, av in value.items():
                        print(f"    {ak}: {av}")

            print("\n--- holders ---")
            holders = result.get('holders', [])
            if holders:
                for h in holders:
                    print(f"  - {h.get('name')}: {h.get('role')} ({h.get('holder_type')})")
            else:
                print("  (no holders)")

            print("\n--- tax_info ---")
            tax = result.get('tax_info')
            if tax:
                for tk, tv in tax.items():
                    if tv is not None:
                        print(f"  {tk}: {tv}")

            print("\n--- metadata ---")
            meta = result.get('metadata', {})
            for mk, mv in meta.items():
                print(f"  {mk}: {mv}")


def main():
    """Main search function."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "AGROFERT a.s. SEARCH" + " " * 32 + "║")
    print("╚" + "=" * 68 + "╝")

    # Search ARES
    ares_results = search_ares(AGROFERT_ICOS)

    # Search Justice Czech
    justice_results = search_justice_cz(AGROFERT_ICOS)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    all_results = ares_results + justice_results

    if all_results:
        print(f"\n  Found {len(all_results)} AGROFERT related companies:\n")
        for ico, name, data in all_results:
            print(f"  • {name}")
            print(f"    ICO: {ico}")
            print(f"    Source: {'ARES' if data in [r[2] for r in ares_results] else 'Justice'}")
            print()
    else:
        print("\n  No AGROFERT companies found with the tested ICOs.")
        print("\n  Tried ICOs:")
        for ico in AGROFERT_ICOS:
            print(f"    - {ico}")

        print("\n  Suggestions:")
        print("    1. Verify the correct ICO at https://or.justice.cz")
        print("    2. AGROFERT may be registered under a holding company")
        print("    3. Try searching by company name at justice.cz")

    print("=" * 70)

    return 0 if all_results else 1


if __name__ == "__main__":
    sys.exit(main())
