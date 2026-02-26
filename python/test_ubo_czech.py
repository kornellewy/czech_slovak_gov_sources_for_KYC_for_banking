#!/usr/bin/env python3
"""
Czech UBO/Ownership Test
Tests Czech scrapers with focus on ownership/UBO data.

Results saved to: tmp/
"""

import json
import os
from datetime import datetime

# Import Czech scrapers
from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.justice_czech import JusticeCzechScraper
from src.scrapers.esm_czech import EsmCzechScraper

# Companies with known ownership/UBO information
CZECH_COMPANIES = [
    {"ico": "26185610", "name": "Agrofert, a.s.", "type": "Private a.s.", "known_owner": "Andrej Babiš (via trust funds AB private trust I & II)"},
    {"ico": "26168685", "name": "Seznam.cz, a.s.", "type": "Private a.s.", "known_owner": "Ivo Lukačovič"},
    {"ico": "27082440", "name": "Alza.cz a.s.", "type": "Private a.s.", "known_owner": "Aleš Zavoral (via L.S. Investments Limited)"},
    {"ico": "27433722", "name": "Livesport s.r.o.", "type": "s.r.o. (LLC)", "known_owner": "Martin Hájek"},
    {"ico": "03024130", "name": "Velká pecka s.r.o. (Rohlik.cz)", "type": "s.r.o. (LLC)", "known_owner": "Tomáš Čupr"},
    {"ico": "08649197", "name": "EP Corporate Group, a.s.", "type": "Private a.s.", "known_owner": "Daniel Křetínský"},
    {"ico": "26173239", "name": "Lidl Česká republika v.o.s.", "type": "v.o.s. (Partnership)", "known_owner": "Dieter Schwarz"},
    {"ico": "25938002", "name": "FOXCONN CZ s.r.o.", "type": "s.r.o. (LLC)", "known_owner": "Young-Way Gou (Terry Gou)"},
    {"ico": "27592502", "name": "J&T Finance Group SE", "type": "SE (European Co.)", "known_owner": "Jozef Tkáč & Ivan Jakabovič"},
    {"ico": "28645065", "name": "Accolade Holding, a.s.", "type": "Private a.s.", "known_owner": "Milan Kratina & Zdeněk Šoustal"},
]


def test_ubo_sources() -> dict:
    """Test Czech sources with focus on UBO/ownership data."""

    results = {
        "test_date": datetime.utcnow().isoformat(),
        "companies_tested": len(CZECH_COMPANIES),
        "results": {}
    }

    output_dir = "/home/kornellewy-laptop/Desktop/sk_cz_sources_sraper/tmp"

    print("=" * 80)
    print("CZECH OWNERSHIP/UBO TEST")
    print("=" * 80)
    print(f"Companies: {len(CZECH_COMPANIES)}")
    print(f"Output: {output_dir}/")
    print("=" * 80)

    for company in CZECH_COMPANIES:
        ico = company["ico"]
        name = company["name"]
        company_type = company["type"]
        known_owner = company["known_owner"]

        print(f"\n### Testing: {name} ({ico}) - {company_type} ###")
        print(f"    Known Owner: {known_owner}")

        company_results = {
            "ico": ico,
            "name": name,
            "type": company_type,
            "known_owner": known_owner,
            "scrapers": {}
        }

        # Test ARES with sub-source info
        print(f"\n  [ARES_CZ with sub-sources] ", end="", flush=True)
        try:
            ares = ARESCzechScraper()
            result = ares.search_by_id(ico, include_subsource=True)

            if result:
                entity = result.get("entity", {})
                subsource = result.get("subsource", {})
                active_count = subsource.get("active_count", 0)

                print(f"✓ OK - {entity.get('company_name_registry')}")
                print(f"    → Sub-sources: {active_count} active registries")

                # Show sub-source details
                if subsource.get("registrations"):
                    print(f"    → Active registrations:")
                    for reg_code, reg_data in subsource.get("registrations", {}).items():
                        if reg_data.get("is_active"):
                            name = reg_data.get("name", reg_code)
                            print(f"       - {reg_code}: {name}")

                company_results["scrapers"]["ARES_CZ"] = {
                    "status": "OK",
                    "company_name": entity.get("company_name_registry"),
                    "subsource": subsource,
                    "full_result": result
                }

                # Save with sub-source data
                filename = f"ares_cz_subsource_{ico}.json"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"    → Saved: {filename}")

            else:
                print(f"✗ NOT FOUND")
                company_results["scrapers"]["ARES_CZ"] = {"status": "NOT_FOUND"}

        except Exception as e:
            print(f"✗ ERROR: {e}")
            company_results["scrapers"]["ARES_CZ"] = {"status": "ERROR", "error": str(e)}

        # Test Justice.cz (may have shareholders)
        print(f"  [JUSTICE_CZ] ", end="", flush=True)
        try:
            justice = JusticeCzechScraper()
            result = justice.search_by_id(ico)

            if result:
                is_maintenance = result.get("metadata", {}).get("maintenance", False)
                if is_maintenance:
                    print(f"⚠ MAINTENANCE")
                else:
                    entity = result.get("entity", {})
                    has_holders = len(result.get("holders", [])) > 0
                    print(f"✓ OK - {entity.get('company_name_registry')} ({'with holders' if has_holders else 'no holders'})")

                company_results["scrapers"]["JUSTICE_CZ"] = {
                    "status": "OK",
                    "maintenance": is_maintenance,
                    "holders_count": len(result.get("holders", [])),
                    "full_result": result
                }

                # Save Justice result
                filename = f"justice_cz_{ico}.json"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            else:
                print(f"✗ NOT FOUND")

        except Exception as e:
            print(f"✗ ERROR: {e}")

        # Test ESM (UBO register) - will show restricted status
        print(f"  [ESM_CZ (UBO Register)] ", end="", flush=True)
        try:
            esm = EsmCzechScraper()
            result = esm.search_by_id(ico)

            if result:
                is_mock = result.get("metadata", {}).get("is_mock", False)
                entity = result.get("entity", {})
                holders = result.get("holders", [])

                if is_mock:
                    print(f"⚠ MOCK/RESTRICTED - Placeholder mode")
                else:
                    print(f"✓ OK - {entity.get('company_name_registry')} ({len(holders)} UBOs)")

                company_results["scrapers"]["ESM_CZ"] = {
                    "status": "MOCK" if is_mock else "OK",
                    "holders_count": len(holders),
                    "full_result": result
                }

                # Save ESM result
                filename = f"esm_cz_{ico}.json"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            else:
                print(f"✗ NOT FOUND")

        except Exception as e:
            print(f"✗ ERROR: {e}")

        results["results"][ico] = company_results

        # Save per-company summary
        company_file = os.path.join(output_dir, f"ubo_company_{ico}_summary.json")
        with open(company_file, 'w', encoding='utf-8') as f:
            json.dump(company_results, f, indent=2, ensure_ascii=False)

    # Save overall summary
    summary_file = os.path.join(output_dir, "ubo_test_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"Test complete! Results saved to: {output_dir}/")
    print("=" * 80)

    return results


def print_ubo_summary(results: dict) -> None:
    """Print a summary focused on UBO/ownership data."""

    print("\n" + "=" * 80)
    print("UBO/OWNERSHIP DATA SUMMARY")
    print("=" * 80)

    for ico, company_data in results["results"].items():
        name = company_data["name"]
        known_owner = company_data["known_owner"]

        print(f"\n{name} ({ico})")
        print(f"  Known Owner: {known_owner}")

        ares_result = company_data["scrapers"].get("ARES_CZ", {})
        if ares_result.get("status") == "OK":
            subsource = ares_result.get("subsource", {})
            active_count = subsource.get("active_count", 0)
            print(f"  ARES Sub-sources: {active_count} active registries")

            # Show key sub-sources related to ownership
            reg = subsource.get("registrations", {})
            if reg.get("RZP", {}).get("is_active"):
                print(f"    ✓ RZP (Commercial Register): Active")
            if reg.get("SD", {}).get("is_active"):
                print(f"    ✓ SD (Tax Debts): Active")
            if reg.get("RED", {}).get("is_active"):
                print(f"    ✓ RED (Register of Entrepreneurs): Active")

        justice_result = company_data["scrapers"].get("JUSTICE_CZ", {})
        if justice_result.get("status") == "OK":
            is_maintenance = justice_result.get("maintenance", False)
            holders_count = justice_result.get("holders_count", 0)
            if is_maintenance:
                print(f"  Justice.cz: Maintenance mode")
            elif holders_count > 0:
                print(f"  Justice.cz: {holders_count} shareholders/holders found")

        esm_result = company_data["scrapers"].get("ESM_CZ", {})
        if esm_result.get("status") == "OK":
            holders_count = esm_result.get("holders_count", 0)
            print(f"  ESM (UBO): {holders_count} beneficial owners")


if __name__ == "__main__":
    results = test_ubo_sources()
    print_ubo_summary(results)
