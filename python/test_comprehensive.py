#!/usr/bin/env python3
"""
Comprehensive test suite for all scrapers.

Usage:
    python test_comprehensive.py                    # Run all tests
    python test_comprehensive.py --coverage         # Run with coverage report
"""

import unittest
import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import all modules to test
from config.constants import (
    ARES_BASE_URL, ORSR_BASE_URL, RPO_BASE_URL, RPVS_BASE_URL,
    FINANCNA_BASE_URL, ESM_BASE_URL, JUSTICE_BASE_URL,
    ARES_RATE_LIMIT, ORSR_RATE_LIMIT, USER_AGENT, LOG_LEVEL
)
from src.utils.logger import get_logger
from src.utils.http_client import HTTPClient
from src.utils.json_handler import JSONHandler
from src.utils.field_mapper import (
    get_retrieved_at, normalize_status, map_holder_type,
    normalize_source, build_entity_url, normalize_field_name,
    apply_field_mappings, add_retrieved_at, map_ownership_fields
)
from src.scrapers.base import BaseScraper
from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.justice_czech import JusticeCzechScraper
from src.scrapers.orsr_slovak import ORSRSlovakScraper
from src.scrapers.stats_slovak import StatsSlovakScraper
from src.scrapers.rpo_slovak import RpoSlovakScraper
from src.scrapers.rpvs_slovak import RpvsSlovakScraper
from src.scrapers.financna_sprava_slovak import FinancnaSpravaScraper
from src.scrapers.esm_czech import EsmCzechScraper


class TestConstants(unittest.TestCase):
    """Test configuration constants."""

    def test_base_urls_defined(self):
        """Test that all base URLs are defined."""
        self.assertIsNotNone(ARES_BASE_URL)
        self.assertIsNotNone(ORSR_BASE_URL)
        self.assertIsNotNone(RPO_BASE_URL)
        self.assertIsNotNone(RPVS_BASE_URL)
        self.assertIsNotNone(FINANCNA_BASE_URL)
        self.assertIsNotNone(ESM_BASE_URL)
        self.assertIsNotNone(JUSTICE_BASE_URL)

    def test_rate_limits_positive(self):
        """Test that rate limits are positive integers."""
        self.assertGreater(ARES_RATE_LIMIT, 0)
        self.assertGreater(ORSR_RATE_LIMIT, 0)

    def test_user_agent_defined(self):
        """Test that user agent is defined."""
        self.assertIsNotNone(USER_AGENT)
        self.assertIn("Mozilla", USER_AGENT)


class TestLogger(unittest.TestCase):
    """Test logger utilities."""

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        import logging
        logger = get_logger("test")
        self.assertIsInstance(logger, logging.Logger)

    def test_logger_with_custom_level(self):
        """Test logger with custom level."""
        logger = get_logger("test_debug", level="DEBUG")
        self.assertEqual(logger.level, 10)  # DEBUG = 10

    def test_logger_singleton_behavior(self):
        """Test that same name returns same logger."""
        logger1 = get_logger("singleton_test")
        logger2 = get_logger("singleton_test")
        self.assertIs(logger1, logger2)


class TestHTTPClient(unittest.TestCase):
    """Test HTTP client."""

    def test_init_default_params(self):
        """Test HTTPClient initialization with defaults."""
        client = HTTPClient()
        self.assertIsNone(client.rate_limit)
        self.assertEqual(client.timeout, 30)

    def test_init_with_rate_limit(self):
        """Test HTTPClient with rate limit."""
        client = HTTPClient(rate_limit=60)
        self.assertEqual(client.rate_limit, 60)
        self.assertGreater(client.min_request_interval, 0)

    def test_context_manager(self):
        """Test HTTPClient as context manager."""
        with HTTPClient() as client:
            self.assertIsNotNone(client.session)

    def test_close(self):
        """Test HTTPClient close method."""
        client = HTTPClient()
        client.close()
        # Should not raise error


class TestJSONHandler(unittest.TestCase):
    """Test JSON handler."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.handler = JSONHandler(base_output_dir=Path(self.temp_dir))

    def tearDown(self):
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load(self):
        """Test save and load operations."""
        data = {"test": "value", "number": 42}
        filepath = self.handler.save(data, "test.json")
        self.assertTrue(os.path.exists(filepath))

        loaded = self.handler.load(filepath)
        self.assertEqual(loaded["test"], "value")
        self.assertEqual(loaded["number"], 42)

    def test_save_with_source(self):
        """Test save with source directory."""
        data = {"ico": "12345678"}
        filepath = self.handler.save(data, "test_ares.json", source="ares")
        self.assertIn("ares", filepath)

    def test_save_adds_timestamp(self):
        """Test that save adds timestamp if not present."""
        data = {"name": "Test"}
        filepath = self.handler.save(data, "test_timestamp.json")
        loaded = self.handler.load(filepath)
        self.assertIn("scraped_at", loaded)


class TestFieldMapper(unittest.TestCase):
    """Test field mapper utilities."""

    def test_get_retrieved_at(self):
        """Test get_retrieved_at returns ISO format."""
        timestamp = get_retrieved_at()
        self.assertIn("T", timestamp)
        self.assertTrue(timestamp.endswith("Z"))

    def test_normalize_status_active(self):
        """Test status normalization for active statuses."""
        self.assertEqual(normalize_status("aktivní"), "active")
        self.assertEqual(normalize_status("aktivni"), "active")
        self.assertEqual(normalize_status("ACTIVE"), "active")

    def test_normalize_status_cancelled(self):
        """Test status normalization for cancelled."""
        self.assertEqual(normalize_status("zrušený"), "cancelled")
        self.assertEqual(normalize_status("zrusena"), "cancelled")

    def test_normalize_status_none(self):
        """Test status normalization for None."""
        self.assertEqual(normalize_status(None), "unknown")
        self.assertEqual(normalize_status(""), "unknown")

    def test_map_holder_type(self):
        """Test holder type mapping."""
        self.assertEqual(map_holder_type("natural_person"), "individual")
        self.assertEqual(map_holder_type("legal_entity"), "entity")
        self.assertEqual(map_holder_type(None), "unknown")

    def test_normalize_source(self):
        """Test source normalization."""
        self.assertEqual(normalize_source("ARES_CZ"), "ARES")
        self.assertEqual(normalize_source("ORSR_SK"), "ORSR")
        self.assertEqual(normalize_source("SIMPLE"), "SIMPLE")

    def test_build_entity_url(self):
        """Test entity URL building."""
        url = build_entity_url("ARES_CZ", "00006947")
        self.assertIsNotNone(url)
        self.assertIn("00006947", url)
        self.assertIn("ares", url.lower())

    def test_build_entity_url_unknown_source(self):
        """Test URL building for unknown source."""
        url = build_entity_url("UNKNOWN", "123")
        self.assertIsNone(url)

    def test_normalize_field_name(self):
        """Test field name normalization."""
        self.assertEqual(normalize_field_name("obchodniJmeno"), "name")
        self.assertEqual(normalize_field_name("ico"), "ico")
        self.assertEqual(normalize_field_name("unknown_field"), "unknown_field")

    def test_apply_field_mappings(self):
        """Test apply field mappings."""
        data = {"obchodniJmeno": "Test Company", "ico": "12345678"}
        result = apply_field_mappings(data)
        self.assertEqual(result["name"], "Test Company")
        self.assertEqual(result["ico"], "12345678")

    def test_add_retrieved_at(self):
        """Test add retrieved_at timestamp."""
        data = {"name": "Test"}
        result = add_retrieved_at(data)
        self.assertIn("retrieved_at", result)

    def test_map_ownership_fields(self):
        """Test ownership field mapping."""
        data = {"ownership_percentage": 75.0, "voting_rights_percentage": 50.0}
        result = map_ownership_fields(data)
        self.assertEqual(result["ownership_pct_direct"], 75.0)
        self.assertEqual(result["voting_rights_pct"], 50.0)


class TestBaseScraper(unittest.TestCase):
    """Test base scraper."""

    def test_get_source_name(self):
        """Test source name extraction."""
        class TestScraper(BaseScraper):
            def search_by_id(self, identifier): return None
            def search_by_name(self, name): return []
            def save_to_json(self, data, filename): return ""

        scraper = TestScraper()
        self.assertEqual(scraper.get_source_name(), "TEST")

    def test_context_manager(self):
        """Test context manager."""
        class TestScraper(BaseScraper):
            def search_by_id(self, identifier): return None
            def search_by_name(self, name): return []
            def save_to_json(self, data, filename): return ""

        with TestScraper() as scraper:
            self.assertIsNotNone(scraper)

    def test_snapshot_disabled_by_default(self):
        """Test that snapshots are disabled by default."""
        class TestScraper(BaseScraper):
            def search_by_id(self, identifier): return None
            def search_by_name(self, name): return []
            def save_to_json(self, data, filename): return ""

        scraper = TestScraper()
        self.assertFalse(scraper.enable_snapshots)


class TestARESCzechScraper(unittest.TestCase):
    """Test ARES Czech scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = ARESCzechScraper()
        self.assertEqual(scraper.SOURCE_NAME, "ARES_CZ")

    def test_search_by_name_returns_empty(self):
        """Test that name search returns empty list."""
        scraper = ARESCzechScraper()
        result = scraper.search_by_name("Test")
        self.assertEqual(result, [])

    @patch('src.scrapers.ares_czech.HTTPClient')
    def test_search_by_id_live(self, mock_http):
        """Test search by ID with mocked response."""
        scraper = ARESCzechScraper()

        # This test uses live API if available
        result = scraper.search_by_id("00006947")
        # Should return data or None
        self.assertTrue(result is None or isinstance(result, dict))


class TestJusticeCzechScraper(unittest.TestCase):
    """Test Justice Czech scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = JusticeCzechScraper()
        self.assertEqual(scraper.SOURCE_NAME, "JUSTICE_CZ")

    def test_get_or_data_mock(self):
        """Test get OR data with mock."""
        scraper = JusticeCzechScraper()
        result = scraper.get_or_data("06649114")
        self.assertIsNotNone(result)
        self.assertEqual(result["ico"], "06649114")

    def test_get_filing_history(self):
        """Test get filing history."""
        scraper = JusticeCzechScraper()
        history = scraper.get_filing_history("06649114")
        self.assertIsInstance(history, list)

    def test_get_shareholders(self):
        """Test get shareholders."""
        scraper = JusticeCzechScraper()
        shareholders = scraper.get_shareholders("06649114")
        self.assertIsInstance(shareholders, list)

    def test_get_board_members(self):
        """Test get board members."""
        scraper = JusticeCzechScraper()
        members = scraper.get_board_members("06649114")
        self.assertIsInstance(members, list)

    def test_supplement_ares_data(self):
        """Test supplement ARES data."""
        scraper = JusticeCzechScraper()
        ares_data = {"ico": "06649114", "name": "Test"}
        result = scraper.supplement_ares_data(ares_data)
        self.assertIn("commercial_register", result)


class TestORSRSlovakScraper(unittest.TestCase):
    """Test ORSR Slovak scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = ORSRSlovakScraper()
        self.assertEqual(scraper.SOURCE_NAME, "ORSR_SK")

    def test_court_codes_defined(self):
        """Test court codes are defined."""
        self.assertIn("Obchodný register Okresného súdu Bratislava I", ORSRSlovakScraper.COURT_CODES)


class TestStatsSlovakScraper(unittest.TestCase):
    """Test Stats Slovak scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = StatsSlovakScraper()
        self.assertEqual(scraper.SOURCE_NAME, "STATS_SK")

    def test_list_datasets(self):
        """Test list datasets returns list."""
        scraper = StatsSlovakScraper()
        datasets = scraper.list_datasets()
        self.assertIsInstance(datasets, list)
        self.assertGreater(len(datasets), 0)

    def test_search_datasets(self):
        """Test search datasets."""
        scraper = StatsSlovakScraper()
        results = scraper.search_datasets("podniky")
        self.assertIsInstance(results, list)

    def test_get_dataset(self):
        """Test get dataset."""
        scraper = StatsSlovakScraper()
        data = scraper.get_dataset("test_dataset")
        self.assertIsNotNone(data)
        self.assertEqual(data["dataset_id"], "test_dataset")


class TestRpoSlovakScraper(unittest.TestCase):
    """Test RPO Slovak scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = RpoSlovakScraper()
        self.assertEqual(scraper.SOURCE_NAME, "RPO_SK")

    def test_search_by_id_mock(self):
        """Test search by ID returns mock data."""
        scraper = RpoSlovakScraper()
        result = scraper.search_by_id("35763491")
        self.assertIsNotNone(result)
        self.assertEqual(result["ico"], "35763491")
        self.assertIn("Slovenská sporiteľňa", result["name"])

    def test_search_by_id_unknown(self):
        """Test search by ID for unknown entity."""
        scraper = RpoSlovakScraper()
        result = scraper.search_by_id("99999999")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("mock", False))


class TestRpvsSlovakScraper(unittest.TestCase):
    """Test RPVS Slovak scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = RpvsSlovakScraper()
        self.assertEqual(scraper.SOURCE_NAME, "RPVS_SK")

    def test_search_by_id_mock(self):
        """Test search by ID returns mock UBO data."""
        scraper = RpvsSlovakScraper()
        result = scraper.search_by_id("35763491")
        self.assertIsNotNone(result)
        self.assertIn("ubos", result)
        self.assertGreater(len(result["ubos"]), 0)

    def test_ubo_data_structure(self):
        """Test UBO data structure."""
        scraper = RpvsSlovakScraper()
        result = scraper.search_by_id("35763491")
        ubo = result["ubos"][0]
        self.assertIn("name", ubo)
        self.assertIn("ownership_percentage", ubo)


class TestFinancnaSpravaScraper(unittest.TestCase):
    """Test Finančná správa scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = FinancnaSpravaScraper()
        self.assertEqual(scraper.SOURCE_NAME, "FINANCNA_SK")

    def test_get_tax_status_mock(self):
        """Test get tax status returns mock data."""
        scraper = FinancnaSpravaScraper()
        result = scraper.get_tax_status("35763491")
        self.assertIsNotNone(result)
        self.assertEqual(result["ico"], "35763491")
        self.assertIn("vat_status", result)

    def test_get_vat_status(self):
        """Test get VAT status."""
        scraper = FinancnaSpravaScraper()
        result = scraper.get_vat_status("35763491")
        self.assertIsNotNone(result)
        self.assertIn("vat_id", result)
        self.assertIn("vat_status", result)


class TestEsmCzechScraper(unittest.TestCase):
    """Test ESM Czech scraper."""

    def test_source_name(self):
        """Test source name."""
        scraper = EsmCzechScraper()
        self.assertEqual(scraper.SOURCE_NAME, "ESM_CZ")

    def test_search_by_id_mock(self):
        """Test search by ID returns mock data."""
        scraper = EsmCzechScraper()
        result = scraper.search_by_id("06649114")
        self.assertIsNotNone(result)
        self.assertEqual(result["ico"], "06649114")
        self.assertIn("beneficial_owners", result)

    def test_get_access_requirements(self):
        """Test get access requirements."""
        scraper = EsmCzechScraper()
        reqs = scraper.get_access_requirements()
        self.assertIn("qualification", reqs)
        self.assertIn("registration", reqs)
        self.assertIn("website", reqs)

    def test_check_compliance(self):
        """Test check compliance."""
        scraper = EsmCzechScraper()
        result = scraper.check_compliance("06649114")
        self.assertIsNotNone(result)
        self.assertIn("has_filed", result)
        self.assertIn("compliance_status", result)


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def test_full_workflow_python(self):
        """Test full workflow with Python scrapers."""
        # Test RPO
        with RpoSlovakScraper() as scraper:
            result = scraper.search_by_id("35763491")
            self.assertIsNotNone(result)

        # Test RPVS
        with RpvsSlovakScraper() as scraper:
            result = scraper.search_by_id("35763491")
            self.assertIsNotNone(result)

        # Test ESM
        with EsmCzechScraper() as scraper:
            result = scraper.search_by_id("06649114")
            self.assertIsNotNone(result)

    def test_data_format_consistency(self):
        """Test that all scrapers return consistent data format."""
        scrapers_and_icos = [
            (RpoSlovakScraper(), "35763491"),
            (RpvsSlovakScraper(), "35763491"),
            (FinancnaSpravaScraper(), "35763491"),
            (EsmCzechScraper(), "06649114"),
        ]

        for scraper, ico in scrapers_and_icos:
            result = scraper.search_by_id(ico)
            self.assertIsNotNone(result, f"No result from {scraper.SOURCE_NAME}")
            self.assertIn("source", result)
            self.assertIn("ico", result)
            self.assertIn("retrieved_at", result)
            scraper.close()


def run_tests(with_coverage=False):
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)

    if with_coverage:
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
            result = runner.run(suite)
            cov.stop()
            cov.save()
            print("\n" + "=" * 70)
            print("COVERAGE REPORT")
            print("=" * 70)
            cov.report()
            cov.html_report(directory="htmlcov")
        except ImportError:
            print("Coverage package not installed. Run: pip install coverage")
            result = runner.run(suite)
    else:
        result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run comprehensive tests")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    args = parser.parse_args()

    sys.exit(run_tests(with_coverage=args.coverage))
