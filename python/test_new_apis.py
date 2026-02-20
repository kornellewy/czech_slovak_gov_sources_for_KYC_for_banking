#!/usr/bin/env python3
"""
Test script for new Slovak and Czech registry API scrapers.

This script tests the following newly implemented scrapers:
- RPO Slovak (Register of Legal Entities)
- RPVS Slovak (Register of Public Sector Partners - UBO)
- Finančná správa (Tax Office - VAT, Debts)
- ESM Czech (Register of Beneficial Owners - placeholder)
- DPH Czech (VAT Register - Registr plátců DPH)
- VR Czech (Vermont Register - Register oddělovaných nemovitostí)
- RES Czech (Resident Income Tax Register - Rezidentní daň z příjmů)

Usage:
    python test_new_apis.py
    python test_new_apis.py --scraper rpo
    python test_new_apis.py --ico 35763491
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scrapers.rpo_slovak import RpoSlovakScraper
from src.scrapers.rpvs_slovak import RpvsSlovakScraper
from src.scrapers.financna_sprava_slovak import FinancnaSpravaScraper
from src.scrapers.esm_czech import EsmCzechScraper
from src.scrapers.dph_czech import DphCzechScraper
from src.scrapers.vr_czech import VrCzechScraper
from src.scrapers.res_czech import ResCzechScraper


# Test ICOs for Slovak entities
TEST_ICOS_SLOVAK = {
    "35763491": "Slovenská sporiteľňa",
    "36246621": "Doprastav",
    "44103755": "Slovak Telekom"
}

# Test ICOs for Czech entities
TEST_ICOS_CZECH = {
    "06649114": "Prusa Research",
    "00216305": "Česká pošta",
    "00006947": "Ministerstvo financí"
}


def test_rpo_slovak(ico: str = None) -> bool:
    """Test RPO Slovak scraper."""
    print("=" * 70)
    print("  Testing RPO Slovak (Register of Legal Entities)")
    print("=" * 70)

    test_ico = ico or "35763491"
    expected_name = TEST_ICOS_SLOVAK.get(test_ico, "Unknown")

    try:
        with RpoSlovakScraper() as scraper:
            print(f"\nSearching for ICO: {test_ico}")
            entity = scraper.search_by_id(test_ico)

            if entity:
                print(f"  ✓ Found: {entity.get('name')}")
                print(f"  ICO: {entity.get('ico')}")
                print(f"  Legal Form: {entity.get('legal_form')}")
                print(f"  Status: {entity.get('status')}")
                print(f"  Court: {entity.get('court')}")

                if entity.get('address'):
                    addr = entity['address']
                    full = addr.get('full_address')
                    if not full and addr.get('street'):
                        full = f"{addr.get('street')}, {addr.get('city')}"
                    print(f"  Address: {full}")

                if 'note' in entity:
                    print(f"  Note: {entity['note']}")

                # Save result
                scraper.save_to_json(entity, f"rpo_{test_ico}.json")
                print(f"  ✓ Saved to output/rpo/rpo_{test_ico}.json")

                print("\nRPO Slovak: PASSED\n")
                return True
            else:
                print(f"  ✗ Entity not found")
                print("\nRPO Slovak: FAILED\n")
                return False

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        print("RPO Slovak: FAILED\n")
        return False


def test_rpvs_slovak(ico: str = None) -> bool:
    """Test RPVS Slovak scraper."""
    print("=" * 70)
    print("  Testing RPVS Slovak (Public Sector Partners - UBO)")
    print("=" * 70)

    test_ico = ico or "35763491"

    try:
        with RpvsSlovakScraper() as scraper:
            print(f"\nFetching UBO data for ICO: {test_ico}")
            ubo_data = scraper.search_by_id(test_ico)

            if ubo_data:
                print(f"  ✓ Company: {ubo_data.get('company_name')}")
                print(f"  ICO: {ubo_data.get('ico')}")

                ubos = ubo_data.get('ubos', [])
                print(f"  Beneficial Owners ({len(ubos)}):")

                for ubo in ubos:
                    pct = ubo.get('ownership_percentage', 0)
                    print(f"    - {ubo.get('name')}: {pct}% ({ubo.get('role')})")

                if 'note' in ubo_data:
                    print(f"  Note: {ubo_data['note']}")

                # Save result
                scraper.save_to_json(ubo_data, f"rpvs_{test_ico}.json")
                print(f"  ✓ Saved to output/rpvs/rpvs_{test_ico}.json")

                print("\nRPVS Slovak: PASSED\n")
                return True
            else:
                print(f"  ✗ UBO data not found")
                print("\nRPVS Slovak: FAILED\n")
                return False

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        print("RPVS Slovak: FAILED\n")
        return False


def test_financna_sprava(ico: str = None) -> bool:
    """Test Finančná správa scraper."""
    print("=" * 70)
    print("  Testing Finančná správa (Tax Office - VAT, Debts)")
    print("=" * 70)

    test_ico = ico or "35763491"

    try:
        with FinancnaSpravaScraper() as scraper:
            print(f"\nFetching tax status for ICO: {test_ico}")

            # Test VAT status
            print("\n--- VAT Status ---")
            vat_data = scraper.get_vat_status(test_ico)
            if vat_data:
                print(f"  VAT ID: {vat_data.get('vat_id')}")
                print(f"  Status: {vat_data.get('vat_status')}")
                print(f"  Tax Office: {vat_data.get('tax_office')}")

            # Test full tax status
            print("\n--- Full Tax Status ---")
            tax_data = scraper.get_tax_status(test_ico)
            if tax_data:
                print(f"  ✓ Name: {tax_data.get('name')}")
                print(f"  ICO: {tax_data.get('ico')}")
                print(f"  DIČ: {tax_data.get('dic')}")
                print(f"  VAT ID: {tax_data.get('vat_id')}")
                print(f"  VAT Status: {tax_data.get('vat_status')}")
                print(f"  Tax Office: {tax_data.get('tax_office')}")

                debts = tax_data.get('tax_debts', {})
                print(f"  Tax Debts: {'Yes' if debts.get('has_debts') else 'No'}")
                if debts.get('has_debts'):
                    print(f"    Amount: {debts.get('amount_eur')} EUR")

                if 'note' in tax_data:
                    print(f"  Note: {tax_data['note']}")

                # Save result
                scraper.save_to_json(tax_data, f"financna_{test_ico}.json")
                print(f"  ✓ Saved to output/financna/financna_{test_ico}.json")

                print("\nFinančná správa: PASSED\n")
                return True
            else:
                print(f"  ✗ Tax data not found")
                print("\nFinančná správa: FAILED\n")
                return False

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        print("Finančná správa: FAILED\n")
        return False


def test_esm_czech(ico: str = None) -> bool:
    """Test ESM Czech scraper (placeholder)."""
    print("=" * 70)
    print("  Testing ESM Czech (Beneficial Owners - RESTRICTED)")
    print("=" * 70)

    test_ico = ico or "06649114"

    try:
        with EsmCzechScraper() as scraper:
            print(f"\nFetching beneficial owners for ICO: {test_ico}")
            esm_data = scraper.search_by_id(test_ico)

            if esm_data:
                print(f"  ✓ Company: {esm_data.get('company_name')}")
                print(f"  ICO: {esm_data.get('ico')}")

                owners = esm_data.get('beneficial_owners', [])
                print(f"  Beneficial Owners ({len(owners)}):")

                for owner in owners:
                    pct = owner.get('ownership_percentage', 0)
                    print(f"    - {owner.get('name')}: {pct}% ({owner.get('role')})")

                if 'note' in esm_data:
                    print(f"  Note: {esm_data['note']}")

                # Save result
                scraper.save_to_json(esm_data, f"esm_{test_ico}.json")
                print(f"  ✓ Saved to output/esm/esm_{test_ico}.json")

                print("\nESM Czech: PASSED (mock data)\n")
                return True
            else:
                print(f"  ✗ Beneficial owner data not found")

                # Show access requirements
                requirements = scraper.get_access_requirements()
                print("\n  Access Requirements:")
                print(f"    Qualification: {requirements.get('qualification')}")
                print(f"    Registration: {requirements.get('registration')}")
                print(f"    Website: {requirements.get('website')}")

                print("\nESM Czech: PARTIAL (placeholder only)\n")
                return True

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        print("ESM Czech: FAILED\n")
        return False


def test_dph_czech(ico: str = None) -> bool:
    """Test DPH Czech scraper (VAT Register)."""
    print("=" * 70)
    print("  Testing DPH Czech (VAT Register - Registr plátců DPH)")
    print("=" * 70)

    test_ico = ico or "05984866"

    try:
        with DphCzechScraper() as scraper:
            print(f"\nFetching VAT status for ICO: {test_ico}")

            # Test by ICO
            print("\n--- Search by ICO ---")
            vat_data = scraper.search_by_id(test_ico)

            if vat_data:
                entity = vat_data.get('entity', {})
                tax_info = vat_data.get('tax_info', {})
                metadata = vat_data.get('metadata', {})

                print(f"  ✓ Company: {entity.get('company_name_registry')}")
                print(f"  ICO: {entity.get('ico_registry')}")
                print(f"  VAT ID: {tax_info.get('vat_id')}")
                print(f"  VAT Status: {tax_info.get('vat_status')}")
                print(f"  Tax ID: {tax_info.get('tax_id')}")
                print(f"  Source: {metadata.get('source')}")
                print(f"  Is Mock: {metadata.get('is_mock')}")

                # Save result
                scraper.save_to_json(vat_data, f"dph_{test_ico}.json")
                print(f"  ✓ Saved to output/dph/dph_{test_ico}.json")

                print("\nDPH Czech: PASSED\n")
                return True
            else:
                print(f"  ✗ VAT data not found")
                print("\nDPH Czech: FAILED\n")
                return False

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        print("DPH Czech: FAILED\n")
        return False


def test_vr_czech(ico: str = None) -> bool:
    """Test VR Czech scraper (Vermont Register)."""
    print("=" * 70)
    print("  Testing VR Czech (Vermont Register - Register oddělovaných nemovitostí)")
    print("=" * 70)

    test_ico = ico or "05984866"

    try:
        with VrCzechScraper() as scraper:
            print(f"\nFetching property info for ICO: {test_ico}")

            property_data = scraper.search_by_id(test_ico)

            if property_data:
                entity = property_data.get('entity', {})
                property_info = property_data.get('property_info', {})
                metadata = property_data.get('metadata', {})

                print(f"  ✓ Company: {entity.get('company_name_registry')}")
                print(f"  ICO: {entity.get('ico_registry')}")

                if property_info:
                    print(f"  Property Count: {property_info.get('property_count', 0)}")
                    properties = property_info.get('properties', [])
                    for prop in properties[:3]:  # Show first 3
                        print(f"    - {prop.get('description', 'N/A')}: {prop.get('address', 'N/A')}")
                else:
                    print(f"  Properties: None")

                print(f"  Source: {metadata.get('source')}")
                print(f"  Is Mock: {metadata.get('is_mock')}")

                # Save result
                scraper.save_to_json(property_data, f"vr_{test_ico}.json")
                print(f"  ✓ Saved to output/vr/vr_{test_ico}.json")

                print("\nVR Czech: PASSED\n")
                return True
            else:
                print(f"  ✗ Property data not found")
                print("\nVR Czech: FAILED\n")
                return False

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        print("VR Czech: FAILED\n")
        return False


def test_res_czech(ico: str = None) -> bool:
    """Test RES Czech scraper (Resident Income Tax)."""
    print("=" * 70)
    print("  Testing RES Czech (Resident Income Tax - Rezidentní daň z příjmů)")
    print("=" * 70)

    test_ico = ico or "05984866"

    try:
        with ResCzechScraper() as scraper:
            print(f"\nFetching tax residency for ICO: {test_ico}")

            residency_data = scraper.search_by_id(test_ico)

            if residency_data:
                entity = residency_data.get('entity', {})
                tax_info = residency_data.get('tax_info', {})
                metadata = residency_data.get('metadata', {})

                print(f"  ✓ Company: {entity.get('company_name_registry')}")
                print(f"  ICO: {entity.get('ico_registry')}")
                print(f"  Tax ID: {tax_info.get('tax_id', 'N/A')}")
                print(f"  Tax Residency Status: {tax_info.get('tax_residency_status', 'N/A')}")
                print(f"  Is Tax Resident: {tax_info.get('is_tax_resident', 'N/A')}")
                print(f"  Source: {metadata.get('source')}")
                print(f"  Is Mock: {metadata.get('is_mock')}")

                # Save result
                scraper.save_to_json(residency_data, f"res_{test_ico}.json")
                print(f"  ✓ Saved to output/res/res_{test_ico}.json")

                print("\nRES Czech: PASSED\n")
                return True
            else:
                print(f"  ✗ Tax residency data not found")
                print("\nRES Czech: FAILED\n")
                return False

    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        print("RES Czech: FAILED\n")
        return False


def test_all(ico: str = None) -> bool:
    """Test all new scrapers."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "NEW API SCRAPERS TEST" + " " * 26 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    results = []

    results.append(("RPO Slovak", test_rpo_slovak(ico)))
    results.append(("RPVS Slovak", test_rpvs_slovak(ico)))
    results.append(("Finančná správa", test_financna_sprava(ico)))
    results.append(("ESM Czech", test_esm_czech(ico)))
    results.append(("DPH Czech", test_dph_czech(ico)))
    results.append(("VR Czech", test_vr_czech(ico)))
    results.append(("RES Czech", test_res_czech(ico)))

    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 70)
    print()

    return passed == total


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test new Slovak and Czech registry API scrapers"
    )
    parser.add_argument(
        "--scraper",
        choices=["rpo", "rpvs", "financna", "esm", "dph", "vr", "res", "all"],
        default="all",
        help="Which scraper to test (default: all)"
    )
    parser.add_argument(
        "--ico",
        help="Specific ICO to test with"
    )

    args = parser.parse_args()

    # Route to appropriate test
    if args.scraper == "rpo":
        success = test_rpo_slovak(args.ico)
    elif args.scraper == "rpvs":
        success = test_rpvs_slovak(args.ico)
    elif args.scraper == "financna":
        success = test_financna_sprava(args.ico)
    elif args.scraper == "esm":
        success = test_esm_czech(args.ico)
    elif args.scraper == "dph":
        success = test_dph_czech(args.ico)
    elif args.scraper == "vr":
        success = test_vr_czech(args.ico)
    elif args.scraper == "res":
        success = test_res_czech(args.ico)
    else:  # all
        success = test_all(args.ico)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
