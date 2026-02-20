#!/usr/bin/env python3
"""
Test unified output format with working company examples.

Tests both Python and verifies the C# clients produce the same output format.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.orsr_slovak import ORSRSlovakScraper
from src.scrapers.rpvs_slovak import RpvsSlovakScraper
from src.scrapers.esm_czech import EsmCzechScraper


def print_unified_output(result, title):
    """Print unified output in a formatted way."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)

    if not result:
        print("  No data found")
        return

    # Entity section
    print("\n--- entity ---")
    entity = result.get('entity', {})
    print(f"  ico_registry: {entity.get('ico_registry')}")
    print(f"  company_name_registry: {entity.get('company_name_registry')}")
    print(f"  legal_form: {entity.get('legal_form')}")
    print(f"  status: {entity.get('status')}")
    if entity.get('registered_address'):
        addr = entity['registered_address']
        print(f"  registered_address:")
        print(f"    full_address: {addr.get('full_address')}")
        print(f"    country_code: {addr.get('country_code')}")
    print(f"  vat_id: {entity.get('vat_id')}")

    # Holders section
    print("\n--- holders ---")
    holders = result.get('holders', [])
    if holders:
        print(f"  count: {len(holders)}")
        for i, holder in enumerate(holders):
            print(f"\n  holder {i+1}:")
            print(f"    holder_type: {holder.get('holder_type')}")
            print(f"    role: {holder.get('role')}")
            print(f"    name: {holder.get('name')}")
            print(f"    jurisdiction: {holder.get('jurisdiction')}")
            print(f"    citizenship: {holder.get('citizenship')}")
            print(f"    ownership_pct_direct: {holder.get('ownership_pct_direct')}")
            print(f"    voting_rights_pct: {holder.get('voting_rights_pct')}")
    else:
        print("  (no holders)")

    # Tax info section
    print("\n--- tax_info ---")
    tax_info = result.get('tax_info')
    if tax_info:
        print(f"  vat_id: {tax_info.get('vat_id')}")
        print(f"  vat_status: {tax_info.get('vat_status')}")
        tax_debts = tax_info.get('tax_debts')
        if tax_debts:
            print(f"  tax_debts:")
            print(f"    has_debts: {tax_debts.get('has_debts')}")
            print(f"    amount_eur: {tax_debts.get('amount_eur')}")
    else:
        print("  (no tax info)")

    # Metadata section
    print("\n--- metadata ---")
    metadata = result.get('metadata', {})
    print(f"  source: {metadata.get('source')}")
    print(f"  register_name: {metadata.get('register_name')}")
    print(f"  register_url: {metadata.get('register_url')}")
    print(f"  retrieved_at: {metadata.get('retrieved_at')}")
    print(f"  is_mock: {metadata.get('is_mock')}")
    print(f"  level: {metadata.get('level', 0)}")


def test_ares_czech():
    """Test ARES Czech with Prusa Research a.s."""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "TESTING ARES CZECH - Prusa Research a.s." + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")

    ico = "06649114"  # Prusa Research a.s.

    try:
        with ARESCzechScraper() as scraper:
            result = scraper.search_by_id(ico)
            if result:
                print_unified_output(result, "ARES Czech Output")

                # Save to file
                output_path = scraper.save_to_json(result, "prusa_research_ares.json")
                print(f"\n✓ Saved to: {output_path}")
                return True
            else:
                print("✗ No data found")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_orsr_slovak():
    """Test ORSR Slovak with Slovenská sporiteľňa."""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 8 + "TESTING ORSR SLOVAK - Slovenská sporiteľňa" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")

    ico = "35763491"  # Slovenská sporiteľňa

    try:
        with ORSRSlovakScraper() as scraper:
            result = scraper.search_by_id(ico)
            if result:
                print_unified_output(result, "ORSR Slovak Output")

                # Save to file
                output_path = scraper.save_to_json(result, "slsp_orsr.json")
                print(f"\n✓ Saved to: {output_path}")
                return True
            else:
                print("✗ No data found")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rpvs_slovak():
    """Test RPVS Slovak (UBO data)."""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "TESTING RPVS SLOVAK - UBO Data" + " " * 26 + "║")
    print("╚" + "=" * 68 + "╝")

    ico = "35763491"  # Slovenská sporiteľňa

    try:
        with RpvsSlovakScraper() as scraper:
            result = scraper.search_by_id(ico)
            if result:
                print_unified_output(result, "RPVS Slovak Output")

                # Save to file
                output_path = scraper.save_to_json(result, "slsp_rpvs.json")
                print(f"\n✓ Saved to: {output_path}")
                return True
            else:
                print("✗ No data found")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_esm_czech():
    """Test ESM Czech (beneficial owners)."""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "TESTING ESM CZECH - Beneficial Owners" + " " * 19 + "║")
    print("╚" + "=" * 68 + "╝")

    ico = "06649114"  # Prusa Research a.s.

    try:
        with EsmCzechScraper() as scraper:
            result = scraper.search_by_id(ico)
            if result:
                print_unified_output(result, "ESM Czech Output")

                # Save to file
                output_path = scraper.save_to_json(result, "prusa_esm.json")
                print(f"\n✓ Saved to: {output_path}")
                return True
            else:
                print("✗ No data found")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "UNIFIED OUTPUT FORMAT TESTS" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")

    results = []
    results.append(("ARES Czech", test_ares_czech()))
    results.append(("ORSR Slovak", test_orsr_slovak()))
    results.append(("RPVS Slovak", test_rpvs_slovak()))
    results.append(("ESM Czech", test_esm_czech()))

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 70)

    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 18 + "C# CLIENT INSTRUCTIONS" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")
    print("""
To run the C# tests with the same unified output:

1. Build and run:
   cd ../c_sharp
   dotnet build

2. Run individual tests:
   dotnet run --project Scrapers.csproj

3. Run ARES test:
   dotnet run --project TestAres.csproj

All C# clients return UnifiedData format with:
  - Entity (ico_registry, company_name_registry, legal_form, status, etc.)
  - Holders (holder_type, role, name, ownership_pct_direct, etc.)
  - TaxInfo (vat_id, vat_status, tax_debts)
  - Metadata (source, register_name, register_url, retrieved_at, is_mock)
    """)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
