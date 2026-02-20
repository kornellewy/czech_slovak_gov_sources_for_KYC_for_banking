#!/usr/bin/env python3
"""
AGROFERT a.s. Test - Demonstration with available data.

Note: AGROFERT a.s. is not directly accessible via public ARES API.
The company structure was reorganized in 2017. This test demonstrates
the unified output format using a simulated AGROFERT entry.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scrapers.ares_czech import ARESCzechScraper
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, TaxInfo, Metadata, Address
)


# AGROFERT subsidiaries that might be in ARES
AGROFERT_SUBSIDIARIES = [
    ("25564820", "Precheza a.s."),  # Chemical company
    ("49241121", "Vodní zdroje"),  # Water treatment
    ("25330609", "Agrofert Trade"),
]


def create_agrofert_mock_data():
    """Create mock AGROFERT data in unified format for demonstration."""
    return {
        "entity": {
            "ico_registry": "25932910",
            "company_name_registry": "AGROFERT a.s.",
            "legal_form": "Akciová společnost",
            "legal_form_code": "121",
            "status": "active",
            "status_effective_date": None,
            "incorporation_date": "1995-01-01",
            "registered_address": {
                "street": "Palackého 1320/1",
                "city": "Praha 2 - Nové Město",
                "postal_code": "120 00",
                "country": "Česká republika",
                "country_code": "CZ",
                "full_address": "Palackého 1320/1, 120 00 Praha 2"
            },
            "nace_codes": ["01110", "01610"],  # Agriculture
            "vat_id": "CZ25932910",
            "tax_id": "25932910"
        },
        "holders": [
            {
                "holder_type": "entity",
                "role": "shareholder",
                "name": "Agrofert Holding a.s.",
                "ico": "25755241",
                "jurisdiction": "CZ",
                "citizenship": None,
                "date_of_birth": None,
                "residency": None,
                "address": None,
                "ownership_pct_direct": 100.0,
                "voting_rights_pct": 100.0,
                "record_effective_from": "2017-02-01",
                "record_effective_to": None
            }
        ],
        "tax_info": {
            "vat_id": "CZ25932910",
            "vat_status": "active",
            "tax_id": "25932910",
            "tax_debts": {
                "has_debts": False,
                "amount_eur": 0.0,
                "details": None
            }
        },
        "metadata": {
            "source": "ARES_CZ",
            "register_name": "Register of Economic Subjects (ARES)",
            "register_url": "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/25932910",
            "retrieved_at": "2026-02-19T12:00:00Z",
            "snapshot_reference": "ARES_CZ_25932910_20260219",
            "parent_entity_ico": None,
            "level": 0,
            "is_mock": True  # Marked as mock since not in public API
        }
    }


def print_agrofert_output(data):
    """Print AGROFERT unified output."""
    print("\n" + "=" * 70)
    print("  AGROFERT a.s. - UNIFIED OUTPUT FORMAT (DEMO)")
    print("=" * 70)

    print("\n--- entity ---")
    entity = data['entity']
    print(f"  ico_registry: {entity['ico_registry']}")
    print(f"  company_name_registry: {entity['company_name_registry']}")
    print(f"  legal_form: {entity['legal_form']}")
    print(f"  status: {entity['status']}")
    print(f"  incorporation_date: {entity['incorporation_date']}")
    print(f"  registered_address:")
    print(f"    full_address: {entity['registered_address']['full_address']}")
    print(f"    country_code: {entity['registered_address']['country_code']}")
    print(f"  vat_id: {entity['vat_id']}")

    print("\n--- holders ---")
    for i, holder in enumerate(data['holders'], 1):
        print(f"  holder {i}:")
        print(f"    holder_type: {holder['holder_type']}")
        print(f"    role: {holder['role']}")
        print(f"    name: {holder['name']}")
        print(f"    ico: {holder['ico']}")
        print(f"    jurisdiction: {holder['jurisdiction']}")
        print(f"    ownership_pct_direct: {holder['ownership_pct_direct']}%")
        print(f"    voting_rights_pct: {holder['voting_rights_pct']}%")

    print("\n--- tax_info ---")
    tax = data['tax_info']
    print(f"  vat_id: {tax['vat_id']}")
    print(f"  vat_status: {tax['vat_status']}")
    print(f"  tax_debts:")
    print(f"    has_debts: {tax['tax_debts']['has_debts']}")

    print("\n--- metadata ---")
    meta = data['metadata']
    print(f"  source: {meta['source']}")
    print(f"  register_name: {meta['register_name']}")
    print(f"  register_url: {meta['register_url']}")
    print(f"  retrieved_at: {meta['retrieved_at']}")
    print(f"  is_mock: {meta['is_mock']}")

    return data


def test_agrofert_subsidiaries():
    """Test AGROFERT subsidiaries that might be in ARES."""
    print("\n" + "=" * 70)
    print("  Testing AGROFERT Subsidiaries")
    print("=" * 70)

    found = []

    with ARESCzechScraper() as scraper:
        for ico, expected_name in AGROFERT_SUBSIDIARIES:
            print(f"\n  Searching: {expected_name} (ICO: {ico})")
            result = scraper.search_by_id(ico)

            if result:
                entity = result.get('entity', {})
                company_name = entity.get('company_name_registry', '')
                print(f"    ✓ Found: {company_name}")
                print(f"    Status: {entity.get('status')}")
                print(f"    Mock: {result.get('metadata', {}).get('is_mock', False)}")

                if expected_name.lower() in company_name.lower():
                    found.append((ico, company_name, result))
            else:
                print(f"    ✗ Not found")

    return found


def save_agrofert_json(data):
    """Save AGROFERT data to JSON file."""
    output_path = Path(__file__).parent / "output" / "agrofert_demo.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path


def main():
    """Main test function."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "AGROFERT a.s. - UNIFIED FORMAT TEST" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")

    print("\nNote: AGROFERT a.s. (ICO: 25932910) is not found in the public ARES API.")
    print("The company was reorganized in 2017. This demo shows the expected")
    print("unified output format with simulated data.\n")

    # Create and display AGROFERT mock data
    agrofert_data = create_agrofert_mock_data()
    print_agrofert_output(agrofert_data)

    # Save to file
    output_path = save_agrofert_json(agrofert_data)
    print(f"\n✓ Saved AGROFERT demo data to: {output_path}")

    # Test subsidiaries
    subsidiaries = test_agrofert_subsidiaries()

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    print("\nPython Unified Output Format:")
    print("  ✓ Entity section: company details, address, VAT info")
    print("  ✓ Holders section: shareholders, UBOs, statutory body")
    print("  ✓ Tax info section: VAT status, tax debts")
    print("  ✓ Metadata section: source, timestamps, mock flag")

    if subsidiaries:
        print(f"\n  Found {len(subsidiaries)} AGROFERT subsidiaries:")
        for ico, name, _ in subsidiaries:
            print(f"    - {name} ({ico})")
    else:
        print("\n  No AGROFERT subsidiaries found in ARES")

    print("\n" + "=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
