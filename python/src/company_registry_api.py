#!/usr/bin/env python3
"""
Company Registry API - Unified Interface for SK/CZ Business Registries

This module provides a simple, reusable interface for querying
Slovak and Czech business registries. Other programs can import
and use this API without needing to know the underlying scraper details.

Usage:
    from src.company_registry_api import CompanyRegistryAPI

    api = CompanyRegistryAPI()
    result = api.get_company_info("06649114")  # Prusa Research
    print(result['entity']['company_name_registry'])
"""

from typing import Optional, Dict, List, Any
from enum import Enum

from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.orsr_slovak import ORSRSlovakScraper
from src.scrapers.rpo_slovak import RpoSlovakScraper
from src.scrapers.rpvs_slovak import RpvsSlovakScraper
from src.scrapers.justice_czech import JusticeCzechScraper
from src.scrapers.esm_czech import EsmCzechScraper
from src.scrapers.financna_sprava_slovak import FinancnaSpravaScraper
from src.scrapers.recursive_scraper import RecursiveScraper


class Country(Enum):
    """Supported countries for registry queries."""
    CZECH_REPUBLIC = "CZ"
    SLOVAKIA = "SK"


class DataSource(Enum):
    """Available data sources."""
    ARES = "ARES_CZ"           # Czech Register of Economic Subjects
    ORSR = "ORSR_SK"           # Slovak Business Register
    RPO = "RPO_SK"             # Slovak Register of Legal Entities
    RPVS = "RPVS_SK"           # Slovak Public Sector Partners (UBO)
    JUSTICE = "JUSTICE_CZ"     # Czech Commercial Register
    ESM = "ESM_CZ"             # Czech Beneficial Owners (restricted)
    FINANNA = "FINANCNA_SK"    # Slovak Tax Office


class CompanyRegistryAPI:
    """
    Unified API for querying SK/CZ business registries.

    This class provides a simple interface for other programs to query
    company information without dealing with scraper details directly.
    """

    def __init__(self, default_country: Country = Country.CZECH_REPUBLIC):
        """
        Initialize the API with a default country.

        Args:
            default_country: Default country for queries (CZ or SK)
        """
        self.default_country = default_country
        self._recursive_scraper = None  # Lazy initialization

    def get_company_info(self, ico: str, country: Optional[Country] = None) -> Optional[Dict[str, Any]]:
        """
        Get basic company information by ICO.

        Args:
            ico: Company identification number (8 digits for CZ/SK)
            country: Country code (uses default if not specified)

        Returns:
            Dictionary with entity, holders, tax_info, metadata sections
            or None if company not found

        Example:
            api = CompanyRegistryAPI()
            info = api.get_company_info("06649114")
            print(info['entity']['company_name_registry'])
        """
        country = country or self.default_country
        source = DataSource.ARES if country == Country.CZECH_REPUBLIC else DataSource.ORSR

        return self._query_by_source(source, ico)

    def get_ubo_info(self, ico: str, country: Optional[Country] = None) -> Optional[Dict[str, Any]]:
        """
        Get Ultimate Beneficial Owner (UBO) information.

        Args:
            ico: Company identification number
            country: Country code (uses default if not specified)

        Returns:
            Dictionary with holders containing UBO data

        Example:
            api = CompanyRegistryAPI()
            ubo = api.get_ubo_info("35763491")
            for owner in ubo['holders']:
                print(f"{owner['name']}: {owner['ownership_pct_direct']}%")
        """
        country = country or self.default_country
        source = DataSource.ESM if country == Country.CZECH_REPUBLIC else DataSource.RPVS

        return self._query_by_source(source, ico)

    def get_tax_info(self, ico: str, country: Optional[Country] = None) -> Optional[Dict[str, Any]]:
        """
        Get tax information (VAT status, tax debts).

        Args:
            ico: Company identification number
            country: Country code (uses default if not specified)

        Returns:
            Dictionary with tax_info section

        Example:
            api = CompanyRegistryAPI()
            tax = api.get_tax_info("06649114")
            print(f"VAT Status: {tax['tax_info']['vat_status']}")
        """
        country = country or self.default_country
        source = DataSource.ARES if country == Country.CZECH_REPUBLIC else DataSource.FINANNA

        return self._query_by_source(source, ico)

    def get_full_info(self, ico: str, country: Optional[Country] = None) -> Optional[Dict[str, Any]]:
        """
        Get complete company information from all available sources.

        Queries multiple sources and combines the results:
        - Basic company info (ARES/ORSR)
        - UBO/beneficial owners (ESM/RPVS)
        - Tax information (ARES/Finančná správa)
        - Commercial register data (Justice)

        Args:
            ico: Company identification number
            country: Country code (uses default if not specified)

        Returns:
            Combined dictionary with all available information

        Example:
            api = CompanyRegistryAPI()
            full = api.get_full_info("06649114")
            print(f"Company: {full['entity']['company_name_registry']}")
            print(f"Owners: {len(full['holders'])}")
            print(f"VAT: {full['tax_info']['vat_status']}")
        """
        country = country or self.default_country

        # Start with basic info
        result = self.get_company_info(ico, country)
        if not result:
            return None

        # Add UBO info
        ubo_result = self.get_ubo_info(ico, country)
        if ubo_result:
            result['holders'].extend(ubo_result.get('holders', []))

        # Add commercial register info for Czech
        if country == Country.CZECH_REPUBLIC:
            justice_result = self._query_by_source(DataSource.JUSTICE, ico)
            if justice_result:
                result['holders'].extend(justice_result.get('holders', []))

        return result

    def search_by_name(self, name: str, country: Optional[Country] = None,
                       limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for companies by name.

        Note: Only ORSR Slovak supports name search. For Czech,
        this returns empty list (ARES doesn't have name search API).

        Args:
            name: Company name to search for
            country: Country code (uses default if not specified)
            limit: Maximum number of results

        Returns:
            List of company information dictionaries

        Example:
            api = CompanyRegistryAPI()
            results = api.search_by_name("Slovenská sporiteľňa", Country.SLOVAKIA)
            for company in results:
                print(f"{company['entity']['company_name_registry']} - {company['entity']['ico_registry']}")
        """
        country = country or self.default_country

        if country != Country.SLOVAKIA:
            return []  # ARES doesn't support name search

        with ORSRSlovakScraper() as scraper:
            results = scraper.search_by_name(name)
            return results[:limit] if results else []

    def verify_vat_number(self, vat_id: str, country: Optional[Country] = None) -> Dict[str, Any]:
        """
        Verify if a VAT number is valid and active.

        Args:
            vat_id: VAT identification number (e.g., "CZ12345678" or "SK1234567890")
            country: Country code (auto-detected from VAT ID prefix if not specified)

        Returns:
            Dictionary with verification result:
            {
                "valid": bool,
                "active": bool,
                "company_name": str,
                "ico": str
            }

        Example:
            api = CompanyRegistryAPI()
            result = api.verify_vat_number("CZ06649114")
            if result['valid']:
                print(f"Active: {result['active']}")
                print(f"Company: {result['company_name']}")
        """
        # Detect country from VAT ID prefix
        if country is None:
            if vat_id.upper().startswith("CZ"):
                country = Country.CZECH_REPUBLIC
            elif vat_id.upper().startswith("SK"):
                country = Country.SLOVAKIA
            else:
                country = self.default_country

        # Extract ICO from VAT ID (remove country prefix)
        ico = vat_id[2:] if vat_id[:2].upper() in ["CZ", "SK"] else vat_id

        result = self.get_company_info(ico, country)

        if not result:
            return {"valid": False, "active": False, "company_name": None, "ico": ico}

        entity = result.get('entity', {})
        tax_info = result.get('tax_info', {})

        return {
            "valid": True,
            "active": tax_info.get('vat_status') == 'active',
            "company_name": entity.get('company_name_registry'),
            "ico": entity.get('ico_registry'),
            "vat_id": tax_info.get('vat_id'),
            "is_mock": result.get('metadata', {}).get('is_mock', False)
        }

    def get_owners_summary(self, ico: str, country: Optional[Country] = None,
                          min_ownership: float = 0.0) -> Dict[str, Any]:
        """
        Get a summary of company ownership structure.

        Args:
            ico: Company identification number
            country: Country code
            min_ownership: Minimum ownership percentage to include (0-100)

        Returns:
            Dictionary with ownership summary:
            {
                "company_name": str,
                "ico": str,
                "total_owners": int,
                "owners": [
                    {
                        "name": str,
                        "type": str,  # "individual" or "entity"
                        "ownership_pct": float,
                        "voting_rights_pct": float,
                        "jurisdiction": str  # for entities
                    }
                ],
                "ownership_concentrated": bool  # true if one owner > 50%
            }

        Example:
            api = CompanyRegistryAPI()
            summary = api.get_owners_summary("35763491", Country.SLOVAKIA)
            print(f"Owners: {summary['total_owners']}")
            for owner in summary['owners']:
                print(f"  {owner['name']}: {owner['ownership_pct']}%")
        """
        result = self.get_full_info(ico, country)
        if not result:
            return None

        holders = result.get('holders', [])
        entity = result.get('entity', {})

        # Filter by minimum ownership
        owners = [
            h for h in holders
            if h.get('ownership_pct_direct', 0) >= min_ownership
        ]

        # Sort by ownership percentage (descending)
        owners.sort(key=lambda x: x.get('ownership_pct_direct', 0), reverse=True)

        return {
            "company_name": entity.get('company_name_registry'),
            "ico": entity.get('ico_registry'),
            "total_owners": len(owners),
            "owners": [
                {
                    "name": o.get('name'),
                    "type": o.get('holder_type'),
                    "ownership_pct": o.get('ownership_pct_direct', 0),
                    "voting_rights_pct": o.get('voting_rights_pct'),
                    "jurisdiction": o.get('jurisdiction'),
                    "role": o.get('role')
                }
                for o in owners
            ],
            "ownership_concentrated": any(
                o.get('ownership_pct_direct', 0) > 50
                for o in owners
            ),
            "is_mock": result.get('metadata', {}).get('is_mock', False)
        }

    # ========== Recursive Ownership Methods ==========

    def get_recursive_ubo(self, ico: str, max_depth: int = 5, country: Optional[Country] = None) -> Optional[Dict[str, Any]]:
        """
        Get complete UBO (Ultimate Beneficial Owner) tree to specified depth.

        This method traces ownership chains through parent companies to identify
        the ultimate beneficial owners - individuals or entities that ultimately
        control the company.

        Args:
            ico: Company identification number
            max_depth: Maximum recursion depth (default: 5)
            country: Country code (auto-detected if not specified)

        Returns:
            Dictionary with:
                - entity: Basic company information
                - holders: All holders with chain tracking
                - metadata: Extended with ultimate_beneficial_owners, ownership_tree
            or None if company not found

        Example:
            api = CompanyRegistryAPI()
            result = api.get_recursive_ubo("06649114", max_depth=3)
            ubos = result['metadata']['ultimate_beneficial_owners']
            for ubo in ubos:
                print(f"{ubo['name']}: {ubo['ownership_percentage']}%")
        """
        country = country or self.default_country
        country_code = country.value

        # Lazy initialize recursive scraper
        if self._recursive_scraper is None:
            self._recursive_scraper = RecursiveScraper(max_depth=max_depth)
        else:
            self._recursive_scraper.max_depth = max_depth

        # Build ownership tree
        tree = self._recursive_scraper.build_ownership_tree(ico, country_code)

        if not tree:
            return None

        # Convert to unified output format
        return self._recursive_scraper.to_unified_output(tree, ico, country_code)

    def get_ibo_summary(self, ico: str, max_depth: int = 5, country: Optional[Country] = None) -> Optional[Dict[str, Any]]:
        """
        Get Indirect Beneficial Owner (IBO) summary.

        IBOs are individuals who own indirectly through corporate chains.
        Ownership percentages are calculated by multiplying along the chain.

        Example:
            Company A owns 50% of Company B
            Person X owns 100% of Company A
            Person X's indirect ownership of Company B = 50% * 100% = 50%

        Args:
            ico: Company identification number
            max_depth: Maximum recursion depth (default: 5)
            country: Country code (auto-detected if not specified)

        Returns:
            Dictionary with:
                - company_name: Name of the queried company
                - ico: Company ICO
                - indirect_beneficial_owners: List of IBOs with calculated ownership
                - total_indirect_ownership: Sum of all indirect ownership
                - ownership_depth: Maximum depth reached
            or None if company not found

        Example:
            api = CompanyRegistryAPI()
            result = api.get_ibo_summary("35763491", max_depth=5)
            for ibo in result['indirect_beneficial_owners']:
                print(f"{ibo['name']}: {ibo['indirect_ownership_pct']}% (via {ibo['path']})")
        """
        country = country or self.default_country
        country_code = country.value

        # Lazy initialize recursive scraper
        if self._recursive_scraper is None:
            self._recursive_scraper = RecursiveScraper(max_depth=max_depth)
        else:
            self._recursive_scraper.max_depth = max_depth

        # Build ownership tree
        tree = self._recursive_scraper.build_ownership_tree(ico, country_code)

        if not tree:
            return None

        # Calculate IBOs
        ibos = self._recursive_scraper.calculate_indirect_owners(tree)

        # Get basic company info
        company_data = self.get_company_info(ico, country)
        entity = company_data.get('entity', {}) if company_data else {}

        return {
            "company_name": entity.get('company_name_registry', tree.name),
            "ico": ico,
            "country": country_code,
            "indirect_beneficial_owners": ibos,
            "total_indirect_ownership": sum(ibo['indirect_ownership_pct'] for ibo in ibos),
            "ownership_depth": self._recursive_scraper.get_ownership_depth_reached(tree),
            "is_mock": company_data.get('metadata', {}).get('is_mock', False) if company_data else False
        }

    def get_ownership_tree(self, ico: str, max_depth: int = 5, country: Optional[Country] = None) -> Optional[Dict[str, Any]]:
        """
        Get full ownership tree structure.

        Args:
            ico: Company identification number
            max_depth: Maximum recursion depth (default: 5)
            country: Country code (auto-detected if not specified)

        Returns:
            Dictionary with:
                - company_name: Name of the queried company
                - ico: Company ICO
                - tree: Nested tree structure showing ownership chains
                - summary: Statistics about the ownership structure
                - concentration_risk: Analysis of ownership concentration
                - cross_border_exposure: List of cross-border ownership links
            or None if company not found

        Example:
            api = CompanyRegistryAPI()
            result = api.get_ownership_tree("35763491")

            # Print the tree
            print(result['tree'])

            # Check concentration risk
            if result['concentration_risk']['has_concentration_risk']:
                print(f"Concentration: {result['concentration_risk']['dominant_owner']}")
        """
        country = country or self.default_country
        country_code = country.value

        # Lazy initialize recursive scraper
        if self._recursive_scraper is None:
            self._recursive_scraper = RecursiveScraper(max_depth=max_depth)
        else:
            self._recursive_scraper.max_depth = max_depth

        # Build ownership tree
        tree = self._recursive_scraper.build_ownership_tree(ico, country_code)

        if not tree:
            return None

        # Get basic company info
        company_data = self.get_company_info(ico, country)
        entity = company_data.get('entity', {}) if company_data else {}

        return {
            "company_name": entity.get('company_name_registry', tree.name),
            "ico": ico,
            "country": country_code,
            "tree": self._recursive_scraper._tree_to_dict(tree),
            "summary": {
                "max_depth_reached": self._recursive_scraper.get_ownership_depth_reached(tree),
                "entity_counts": self._recursive_scraper.get_entity_count(tree),
                "ownership_summary": self._recursive_scraper.get_ownership_summary(tree)
            },
            "concentration_risk": self._recursive_scraper.find_concentration_risk(tree),
            "cross_border_exposure": self._recursive_scraper.get_cross_border_exposure(tree),
            "is_mock": company_data.get('metadata', {}).get('is_mock', False) if company_data else False
        }

    def print_ownership_tree(self, ico: str, max_depth: int = 5, country: Optional[Country] = None) -> None:
        """
        Print ownership tree to console (for debugging/visualization).

        Args:
            ico: Company identification number
            max_depth: Maximum recursion depth (default: 5)
            country: Country code (auto-detected if not specified)

        Example:
            api = CompanyRegistryAPI()
            api.print_ownership_tree("35763491", max_depth=3)
        """
        country = country or self.default_country
        country_code = country.value

        # Lazy initialize recursive scraper
        if self._recursive_scraper is None:
            self._recursive_scraper = RecursiveScraper(max_depth=max_depth)
        else:
            self._recursive_scraper.max_depth = max_depth

        tree = self._recursive_scraper.build_ownership_tree(ico, country_code)

        if tree:
            self._recursive_scraper.print_tree(tree)
        else:
            print(f"No ownership tree found for ICO: {ico}")

    def _query_by_source(self, source: DataSource, ico: str) -> Optional[Dict[str, Any]]:
        """Internal method to query a specific data source."""
        scraper_map = {
            DataSource.ARES: ARESCzechScraper,
            DataSource.ORSR: ORSRSlovakScraper,
            DataSource.RPO: RpoSlovakScraper,
            DataSource.RPVS: RpvsSlovakScraper,
            DataSource.JUSTICE: JusticeCzechScraper,
            DataSource.ESM: EsmCzechScraper,
            DataSource.FINANNA: FinancnaSpravaScraper,
        }

        scraper_class = scraper_map.get(source)
        if not scraper_class:
            return None

        try:
            with scraper_class() as scraper:
                return scraper.search_by_id(ico)
        except Exception:
            return None


# Convenience singleton instance
_default_api = None


def get_api(country: Country = Country.CZECH_REPUBLIC) -> CompanyRegistryAPI:
    """
    Get a singleton instance of the Company Registry API.

    Args:
        country: Default country for queries

    Returns:
        CompanyRegistryAPI instance

    Example:
        from src.company_registry_api import get_api

        api = get_api()
        info = api.get_company_info("06649114")
    """
    global _default_api
    if _default_api is None:
        _default_api = CompanyRegistryAPI(country)
    return _default_api
