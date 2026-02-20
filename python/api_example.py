#!/usr/bin/env python3
"""
Example program demonstrating how to use the Company Registry API
in your own applications.

This shows the simplest way to integrate the scrapers into your code.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.company_registry_api import CompanyRegistryAPI, Country, get_api


def example_1_basic_lookup():
    """Example 1: Basic company lookup."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Company Lookup")
    print("=" * 60)

    # Get API instance
    api = get_api()

    # Look up Prusa Research
    result = api.get_company_info("06649114")

    if result:
        entity = result['entity']
        print(f"Company: {entity['company_name_registry']}")
        print(f"Status: {entity['status']}")
        print(f"Legal Form: {entity['legal_form']}")
        print(f"Address: {entity['registered_address']['full_address']}")
    else:
        print("Company not found")


def example_2_ownership_structure():
    """Example 2: Get ownership structure."""
    print("\n" + "=" * 60)
    print("Example 2: Ownership Structure")
    print("=" * 60)

    api = get_api()

    # Get Slovenská sporiteľňa ownership
    summary = api.get_owners_summary("35763491", Country.SLOVAKIA)

    if summary:
        print(f"Company: {summary['company_name']}")
        print(f"Total Owners: {summary['total_owners']}")
        print(f"Ownership Concentrated: {summary['ownership_concentrated']}")
        print("\nOwners:")

        for owner in summary['owners']:
            print(f"  - {owner['name']}")
            print(f"    Type: {owner['type']}")
            print(f"    Ownership: {owner['ownership_pct']}%")
            print(f"    Voting Rights: {owner['voting_rights_pct']}%")
            if owner['jurisdiction']:
                print(f"    Jurisdiction: {owner['jurisdiction']}")


def example_3_vat_verification():
    """Example 3: Verify VAT number."""
    print("\n" + "=" * 60)
    print("Example 3: VAT Number Verification")
    print("=" * 60)

    api = get_api()

    # Verify Czech VAT number
    result = api.verify_vat_number("CZ06649114")

    print(f"VAT ID: CZ06649114")
    print(f"Valid: {result['valid']}")
    print(f"Active: {result['active']}")

    if result['valid']:
        print(f"Company: {result['company_name']}")
        print(f"ICO: {result['ico']}")
        print(f"Is Mock: {result['is_mock']}")


def example_4_full_info():
    """Example 4: Get complete company information."""
    print("\n" + "=" * 60)
    print("Example 4: Complete Company Information")
    print("=" * 60)

    api = get_api()

    # Get all available information
    full = api.get_full_info("06649114")

    if full:
        entity = full['entity']
        holders = full['holders']
        tax_info = full['tax_info']
        metadata = full['metadata']

        print(f"\n--- Entity ---")
        print(f"Name: {entity['company_name_registry']}")
        print(f"Status: {entity['status']}")
        print(f"VAT ID: {entity['vat_id']}")

        print(f"\n--- Holders ({len(holders)}) ---")
        for holder in holders:
            print(f"  - {holder['name']} ({holder['role']})")

        print(f"\n--- Tax Info ---")
        print(f"VAT Status: {tax_info['vat_status'] if tax_info else 'N/A'}")

        print(f"\n--- Metadata ---")
        print(f"Source: {metadata['source']}")
        print(f"Retrieved: {metadata['retrieved_at']}")
        print(f"Is Mock: {metadata['is_mock']}")


def example_5_search_by_name():
    """Example 5: Search companies by name."""
    print("\n" + "=" * 60)
    print("Example 5: Search by Name (Slovakia only)")
    print("=" * 60)

    api = CompanyRegistryAPI(default_country=Country.SLOVAKIA)

    # Search for Slovak companies
    results = api.search_by_name("Slovenská sporiteľňa", Country.SLOVAKIA)

    print(f"Found {len(results)} companies:")
    for company in results[:3]:  # Show first 3
        entity = company['entity']
        print(f"  - {entity['company_name_registry']}")
        print(f"    ICO: {entity['ico_registry']}")


def example_6_batch_processing():
    """Example 6: Process multiple companies."""
    print("\n" + "=" * 60)
    print("Example 6: Batch Processing")
    print("=" * 60)

    api = get_api()

    # List of ICOs to process
    icos = ["00006947", "00216305", "06649114"]

    print("Processing companies...")
    results = []

    for ico in icos:
        result = api.get_company_info(ico)
        if result:
            results.append({
                'ico': ico,
                'name': result['entity']['company_name_registry'],
                'status': result['entity']['status']
            })

    print(f"\nProcessed {len(results)} companies:")
    for r in results:
        print(f"  [{r['ico']}] {r['name']} - {r['status']}")


def example_7_cross_border():
    """Example 7: Query both Czech and Slovak registries."""
    print("\n" + "=" * 60)
    print("Example 7: Cross-Border Queries")
    print("=" * 60)

    api = get_api()

    companies = [
        ("06649114", Country.CZECH_REPUBLIC, "Prusa Research"),
        ("35763491", Country.SLOVAKIA, "Slovenská sporiteľňa"),
    ]

    for ico, country, expected_name in companies:
        result = api.get_company_info(ico, country)
        if result:
            name = result['entity']['company_name_registry']
            print(f"[{country.name}] {name} ({ico})")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print(" COMPANY REGISTRY API - USAGE EXAMPLES")
    print("=" * 60)

    example_1_basic_lookup()
    example_2_ownership_structure()
    example_3_vat_verification()
    example_4_full_info()
    example_5_search_by_name()
    example_6_batch_processing()
    example_7_cross_border()

    print("\n" + "=" * 60)
    print(" All examples completed!")
    print("=" * 60)
    print("\nTo use in your code:")
    print("  from src.company_registry_api import get_api")
    print("  api = get_api()")
    print("  result = api.get_company_info('06649114')")
    print()


if __name__ == "__main__":
    main()
