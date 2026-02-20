# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

SK/CZ Business Registry Scrapers - Unified scrapers for Slovak and Czech business registries with **identical output format** across Python and C# implementations.

**Key principle:** All scrapers must return data in the unified format: `{entity, holders, tax_info, metadata}`. Python uses dataclasses in `output_normalizer.py`; C# uses classes in `OutputNormalizer.cs` (namespace `UnifiedOutput`).

---

## Common Commands

### Python (from `/python` directory)

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest --cov=src --cov-report=html --cov-report=term  # Target: 80% coverage

# Run specific test modules
pytest tests/test_scrapers.py -v                    # Unit tests only
pytest tests/test_e2e.py -v                         # E2E tests only
pytest tests/ -k "test_ares" -v                       # Specific scraper tests

# Run demo scripts (not tests, but useful for verification)
python3 test_comprehensive.py          # Unit tests
python3 test_unified_output.py         # Unified format demo
python3 test_new_apis.py               # New API scrapers (RPO, RPVS, ESM, Finančná)
python3 test_new_apis.py --scraper rpvs --ico 35763491

# Run API example
python3 api_example.py

# Quick verification
python3 -c "from src.company_registry_api import get_api; print(get_api().get_company_info('06649114')['entity']['company_name_registry'])"
```

### C# (from `/c_sharp` directory)

```bash
# Build
dotnet restore
dotnet build

# Run test projects
dotnet run --project TestAres.csproj       # ARES tests
dotnet run --project AgrofertTest.csproj   # AGROFERT demo
dotnet run --project ApiExample.csproj     # API usage examples

# Build specific project
dotnet build TestAres.csproj
```

---

## Architecture

### Dual Implementation Strategy

This project maintains **parallel implementations** in Python and C# with identical JSON output format. When modifying scrapers:
1. Update both Python and C# versions
2. Ensure output structure matches exactly
3. Run tests for both implementations

### Python Architecture

```
python/
├── src/scrapers/          # All scraper implementations
│   ├── base.py            # Abstract BaseScraper class
│   ├── *_czech.py         # Czech scrapers
│   └── *_slovak.py        # Slovak scrapers
├── src/utils/             # Shared utilities
│   ├── output_normalizer.py  # UNIFIED OUTPUT FORMAT (dataclasses)
│   ├── http_client.py         # Rate-limited HTTP client
│   ├── json_handler.py        # JSON file operations
│   └── logger.py              # Logging
├── src/company_registry_api.py  # PUBLIC API for external use
└── config/constants.py     # API URLs, rate limits
```

**Key pattern:** All scrapers inherit from `BaseScraper` (context manager with rate limiting, logging, snapshot support). Must implement: `search_by_id()`, `search_by_name()`, `save_to_json()`.

### C# Architecture

```
c_sharp/
├── OutputNormalizer.cs    # UNIFIED OUTPUT FORMAT (namespace: UnifiedOutput)
├── ICompanyRegistryService.cs   # Service interface
├── CompanyRegistryService.cs    # Service implementation
├── AresClient.cs           # ARES namespace, returns UnifiedData
├── OrsrClient.cs           # Orsr namespace
├── ... (one Client.cs per registry)
└── *.csproj               # Multiple test projects
```

**Key pattern:** Each registry has its own namespace with a Client class. All return `UnifiedData` (not `UnifiedOutput` - that's the namespace name). The `CompanyRegistryService` provides a unified facade.

---

## Unified Output Format

**Critical:** Both implementations must return this exact structure:

```json
{
  "entity": {
    "ico_registry": "...",
    "company_name_registry": "...",
    "legal_form": "...",
    "status": "active|cancelled|in_liquidation|...",
    "registered_address": {...},
    "vat_id": "..."
  },
  "holders": [
    {
      "holder_type": "individual|entity|trust_fund",
      "role": "shareholder|beneficial_owner|statutory_body|...",
      "name": "...",
      "ownership_pct_direct": 0-100,
      "voting_rights_pct": 0-100,
      "jurisdiction": "SK|CZ|AT|...",  // for entities
      "citizenship": "SK|CZ|..."        // for individuals
    }
  ],
  "tax_info": {
    "vat_id": "...",
    "vat_status": "active|inactive",
    "tax_debts": {"has_debts": bool, "amount_eur": float}
  },
  "metadata": {
    "source": "ARES_CZ|ORSR_SK|RPO_SK|RPVS_SK|...",
    "register_name": "...",
    "register_url": "...",
    "retrieved_at": "ISO timestamp",
    "is_mock": bool  // TRUE when API unavailable - always check this
  }
}
```

**Status normalization:** `active`, `cancelled`, `in_liquidation`, `bankruptcy`, `dissolved`, `suspended` (normalized from Czech/Slovak terms).

**Country codes:** Use ISO 3166-1 alpha-2 (SK, CZ, AT, DE, etc.).

---

## Registry API Status

| Source | Country | Type | Status | Notes |
|--------|---------|------|--------|-------|
| ARES_CZ | CZ | REST API | ✅ Working | 500 req/min limit |
| ORSR_SK | SK | Web scraper | ✅ Working | 60 req/min limit |
| RPVS_SK | SK | REST API | ⚠️ Mock | Requires API key |
| JUSTICE_CZ | CZ | None | ⚠️ Mock | No public API |
| ESM_CZ | CZ | RESTRICTED | 🔒 AML only | Requires certification |
| RPO_SK | SK | REST API | ⚠️ Mock | API format TBD |
| FINANCNA_SK | SK | REST API | ⚠️ Mock | API format TBD |

**When `is_mock: true`:** The data is fallback/mock because the API is unavailable, restricted, or the ICO wasn't found.

---

## Public API (for integration)

### Python

```python
from src.company_registry_api import CompanyRegistryAPI, Country

api = CompanyRegistryAPI()
result = api.get_company_info("06649114")
owners = api.get_owners_summary("35763491", Country.SLOVAKIA)
vat = api.verify_vat_number("CZ06649114")
```

### C#

```csharp
using CompanyRegistry;

var service = new CompanyRegistryService();
var result = await service.GetCompanyInfoAsync("06649114");
var owners = await service.GetOwnersSummaryAsync("35763491", Country.Slovakia);
var vat = await service.VerifyVatNumberAsync("CZ06649114");
```

---

## Test ICOs (always return real data)

**Czech:** `00006947` (Ministerstvo financí), `00216305` (Česká pošta), `06649114` (Prusa Research)

**Slovak:** `35763491` (Slovenská sporiteľňa), `44103755` (Slovak Telekom), `31328356` (VÚB bank)

**Note:** AGROFERT a.s. (25932910) is NOT in ARES - returns 404.

---

## Testing Requirements

### Coverage Target: 80%

All code changes must maintain **minimum 80% test coverage**. Run coverage before committing:

```bash
# Python - check coverage
pytest --cov=src --cov-report=term-missing --cov-report=html
# View htmlcov/index.html for detailed report
```

### Test Structure

```
tests/
├── test_scrapers/          # Unit tests for individual scrapers
│   ├── test_ares_czech.py
│   ├── test_orsr_slovak.py
│   └── ...
├── test_utils/             # Utilities tests
│   ├── test_output_normalizer.py
│   └── test_http_client.py
├── test_e2e/               # End-to-end tests
│   ├── test_full_workflow.py    # Test complete user journeys
│   ├── test_cross_border.py     # Test CZ+SK combined queries
│   └── test_api_integration.py  # Test public API surface
└── conftest.py             # Shared pytest fixtures
```

### E2E Tests (End-to-End)

E2E tests verify complete workflows using real API calls where possible:

**Test scenarios:**
1. **Full workflow:** Query company info → Get UBO → Get tax info → Combine results
2. **Cross-border:** Same entity queried from both CZ and SK registries
3. **Batch processing:** Process multiple ICOs, verify all return unified format
4. **API integration:** Test `CompanyRegistryAPI` / `CompanyRegistryService` facade
5. **Mock fallback:** Verify mock data returns when APIs are unavailable

**Running E2E:**
```bash
# Python E2E only
pytest tests/test_e2e/ -v --tb=short

# Single E2E scenario
pytest tests/test_e2e/test_full_workflow.py::test_complete_company_lookup -v
```

**Writing new E2E test:**
- Use real test ICOs (00006947, 06649114, 35763491)
- Test the full user journey, not individual functions
- Verify unified output format structure
- Check `is_mock` flag behavior
- Test error handling (404, timeout, invalid ICO)

### C# Testing

```bash
# Run all tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Run specific test
dotnet test --filter "FullyQualifiedName~TestAres"
```

---

## File Naming Conventions

- **Python scrapers:** `<source>_<country>.py` (e.g., `ares_czech.py`, `orsr_slovak.py`)
- **C# clients:** `<Source>Client.cs` (e.g., `AresClient.cs`, `OrsrClient.cs`)
- **Source names:** Uppercase with country suffix: `ARES_CZ`, `ORSR_SK`, `RPVS_SK`, etc.

---

## Adding a New Scraper

1. **Python:** Inherit from `BaseScraper`, implement the 3 abstract methods, return unified format via `output_normalizer.py` dataclasses
2. **C#:** Create namespace with Client class, implement async methods, return `UnifiedData` with `UnifiedOutput` classes
3. **Both:** Add to `company_registry_api.py` / `CompanyRegistryService.cs`, update README
4. **Test:** Create mock data fallback if API is unavailable
