#!/usr/bin/env python3
"""
Comprehensive Czech Sources Test
Tests all Czech scrapers against major Czech companies.

Results saved to: tmp/
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

# Import Czech scrapers
from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.justice_czech import JusticeCzechScraper
from src.scrapers.dph_czech import DphCzechScraper
from src.scrapers.vr_czech import VrCzechScraper
from src.scrapers.res_czech import ResCzechScraper
from src.scrapers.smlouvy_czech import SmlouvyCzechScraper
from src.scrapers.cnb_czech import CnbCzechScraper
from src.scrapers.esm_czech import EsmCzechScraper


# Major Czech companies to test
CZECH_COMPANIES = [
    {"ico": "00177041", "name": "Škoda Auto a.s.", "sector": "Automotive Manufacturing"},
    {"ico": "45274649", "name": "ČEZ, a. s.", "sector": "Energy & Utilities"},
    {"ico": "28356250", "name": "Energetický a průmyslový holding, a.s. (EPH)", "sector": "Energy Infrastructure"},
    {"ico": "26185610", "name": "Agrofert, a.s.", "sector": "Agriculture, Food & Chemicals"},
    {"ico": "61672190", "name": "ORLEN Unipetrol a.s.", "sector": "Refining & Petrochemicals"},
    {"ico": "25938002", "name": "FOXCONN CZ s.r.o.", "sector": "Electronics Manufacturing"},
    {"ico": "27773035", "name": "Hyundai Motor Manufacturing Czech s.r.o.", "sector": "Automotive Manufacturing"},
    {"ico": "45317054", "name": "Komerční banka, a.s.", "sector": "Banking & Finance"},
    {"ico": "45244782", "name": "Česká spořitelna, a.s.", "sector": "Banking & Finance"},
    {"ico": "00014915", "name": "Metrostav a.s.", "sector": "Construction"},
]

# Czech scrapers to test
CZECH_SCRAPERS = [
    ("ARES_CZ", ARESCzechScraper),
    ("JUSTICE_CZ", JusticeCzechScraper),
    ("DPH_CZ", DphCzechScraper),
    ("VR_CZ", VrCzechScraper),
    ("RES_CZ", ResCzechScraper),
    ("SMLOUVY_CZ", SmlouvyCzechScraper),
    ("CNB_CZ", CnbCzechScraper),
    ("ESM_CZ", EsmCzechScraper),
]


def test_all_scrapers() -> Dict[str, Any]:
    """Test all Czech scrapers against all test companies."""

    results = {
        "test_date": datetime.utcnow().isoformat(),
        "companies_tested": len(CZECH_COMPANIES),
        "scrapers_tested": len(CZECH_SCRAPERS),
        "results": {}
    }

    output_dir = "/home/kornellewy-laptop/Desktop/sk_cz_sources_sraper/tmp"

    print("=" * 80)
    print("COMPREHENSIVE CZECH SOURCES TEST")
    print("=" * 80)
    print(f"Companies: {len(CZECH_COMPANIES)}")
    print(f"Scrapers: {len(CZECH_SCRAPERS)}")
    print(f"Output: {output_dir}/")
    print("=" * 80)

    for company in CZECH_COMPANIES:
        ico = company["ico"]
        name = company["name"]
        sector = company["sector"]

        print(f"\n### Testing: {name} ({ico}) - {sector} ###")

        company_results = {
            "ico": ico,
            "name": name,
            "sector": sector,
            "scrapers": {}
        }

        for scraper_name, scraper_class in CZECH_SCRAPERS:
            print(f"\n  [{scraper_name}] ", end="", flush=True)

            try:
                scraper = scraper_class()
                result = scraper.search_by_id(ico)

                if result:
                    is_mock = result.get("metadata", {}).get("is_mock", False)
                    status = "MOCK" if is_mock else "OK"

                    # Extract key info
                    entity = result.get("entity", {})
                    company_name = entity.get("company_name_registry")
                    holders_count = len(result.get("holders", []))
                    has_tax_info = result.get("tax_info") is not None

                    print(f"✓ {status} - {company_name or 'N/A'}")

                    scraper_result = {
                        "status": status,
                        "company_name": company_name,
                        "holders_count": holders_count,
                        "has_tax_info": has_tax_info,
                        "is_mock": is_mock,
                        "full_result": result
                    }

                    # Save individual result
                    filename = f"{scraper_name.lower()}_{ico}.json"
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"    → Saved: {filename}")

                else:
                    print(f"✗ NOT FOUND")
                    scraper_result = {
                        "status": "NOT_FOUND",
                        "full_result": None
                    }

            except Exception as e:
                print(f"✗ ERROR: {e}")
                scraper_result = {
                    "status": "ERROR",
                    "error": str(e),
                    "full_result": None
                }

            company_results["scrapers"][scraper_name] = scraper_result

        results["results"][ico] = company_results

        # Save per-company summary
        company_file = os.path.join(output_dir, f"company_{ico}_summary.json")
        with open(company_file, 'w', encoding='utf-8') as f:
            json.dump(company_results, f, indent=2, ensure_ascii=False)

    # Save summary report
    summary_file = os.path.join(output_dir, "test_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"Test complete! Results saved to: {output_dir}/")
    print("=" * 80)

    return results


def print_summary(results: Dict[str, Any]) -> None:
    """Print a summary of test results."""

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for ico, company_data in results["results"].items():
        name = company_data["name"]
        print(f"\n{name} ({ico}):")

        for scraper_name, scraper_result in company_data["scrapers"].items():
            status = scraper_result.get("status", "UNKNOWN")
            if status == "OK":
                print(f"  {scraper_name}: ✓ OK (real data)")
            elif status == "MOCK":
                print(f"  {scraper_name}: ⚠ MOCK (fallback data)")
            elif status == "NOT_FOUND":
                print(f"  {scraper_name}: ✗ Not found")
            elif status == "ERROR":
                print(f"  {scraper_name}: ✗ Error - {scraper_result.get('error', 'Unknown')}")


if __name__ == "__main__":
    results = test_all_scrapers()
    print_summary(results)
