#!/usr/bin/env python3
"""
Test script for AGROFERT a.s.

This script tests the ARES Czech scraper with AGROFERT's ICO.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scrapers.ares_czech import ARESCzechScraper
import json


def test_agrofert():
    """Test ARES Czech scraper with AGROFERT a.s."""
    print("=" * 70)
    print("  Testing AGROFERT a.s. with ARES Czech")
    print("=" * 70)

    # AGROFERT a.s. ICO
    agrofert_ico = "25932910"

    print(f"\nSearching for AGROFERT a.s. (ICO: {agrofert_ico})...")

    try:
        with ARESCzechScraper() as scraper:
            result = scraper.search_by_id(agrofert_ico)

            if result:
                print("\n✓ FOUND AGROFERT a.s.!")
                print("\n--- Entity Data ---")
                if 'entity' in result:
                    entity = result['entity']
                    print(f"  Company Name: {entity.get('company_name_registry')}")
                    print(f"  ICO: {entity.get('ico_registry')}")
                    print(f"  Legal Form: {entity.get('legal_form')}")
                    print(f"  Status: {entity.get('status')}")
                    print(f"  VAT ID: {entity.get('vat_id')}")

                    if entity.get('registered_address'):
                        addr = entity['registered_address']
                        print(f"  Address: {addr.get('full_address')}")

                print("\n--- Tax Info ---")
                if result.get('tax_info'):
                    tax = result['tax_info']
                    print(f"  VAT ID: {tax.get('vat_id')}")
                    print(f"  VAT Status: {tax.get('vat_status')}")

                print("\n--- Metadata ---")
                if result.get('metadata'):
                    meta = result['metadata']
                    print(f"  Source: {meta.get('source')}")
                    print(f"  Register: {meta.get('register_name')}")
                    print(f"  Retrieved: {meta.get('retrieved_at')}")
                    print(f"  Is Mock: {meta.get('is_mock')}")

                # Save to JSON
                output_file = scraper.save_to_json(result, "agrofert_ares.json")
                print(f"\n✓ Saved to: {output_file}")

                print("\n" + "=" * 70)
                print("  AGROFERT a.s. Test: PASSED")
                print("=" * 70)
                return True
            else:
                print("\n✗ AGROFERT a.s. NOT FOUND in ARES (404)")
                print("\nThis could mean:")
                print("  1. The ICO 25932910 is incorrect")
                print("  2. AGROFERT a.s. is not in the ARES database")
                print("  3. The company name or structure has changed")

                # Try to search by name
                print("\n--- Trying to find alternative AGROFERT entries ---")
                print("Note: ARES API doesn't support name search in this implementation")

                print("\n" + "=" * 70)
                print("  AGROFERT a.s. Test: NOT FOUND")
                print("=" * 70)
                return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("  AGROFERT a.s. Test: ERROR")
        print("=" * 70)
        return False


def test_known_entity():
    """Test with a known entity to verify ARES is working."""
    print("\n")
    print("=" * 70)
    print("  Testing known entity (Ministerstvo financí) to verify ARES")
    print("=" * 70)

    known_ico = "00006947"

    print(f"\nSearching for Ministerstvo financí (ICO: {known_ico})...")

    try:
        with ARESCzechScraper() as scraper:
            result = scraper.search_by_id(known_ico)

            if result:
                print("\n✓ FOUND!")
                entity = result.get('entity', {})
                print(f"  Name: {entity.get('company_name_registry')}")
                print(f"  Status: {entity.get('status')}")
                print(f"  Is Mock: {result.get('metadata', {}).get('is_mock', False)}")
                print("\nARES API is working correctly.")
                return True
            else:
                print("\n✗ NOT FOUND - ARES API may be down")
                return False

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


if __name__ == "__main__":
    # First test with known entity
    ares_working = test_known_entity()

    # Then test AGROFERT
    if ares_working:
        print("\n")
        agrofert_found = test_agrofert()

        if not agrofert_found:
            print("\n" + "!" * 70)
            print("  SUGGESTION: Try verifying AGROFERT's correct ICO")
            print("  Possible alternatives to check:")
            print("    - Search at https://ares.gov.cz")
            print("    - Check the Commercial Register (Obchodní rejstřík)")
            print("!" * 70)

    sys.exit(0)
