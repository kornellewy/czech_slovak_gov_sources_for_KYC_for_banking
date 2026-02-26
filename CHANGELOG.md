# Changelog

All notable changes to this project will be documented in this file.

## [1.4.0] - 2026-02-23

### Added

#### RPO Slovak Real API Integration
- **Python**: `rpo_slovak.py` - Complete rewrite with real RPO API integration
- **C#**: `RpoClient.cs` - Complete rewrite with real RPO API integration
- Two-step API process: Search by ICO → Get entity details by internal ID
- Holder extraction: statutory bodies (Konateľ) and stakeholders (Spoločník)
- Address parsing with RPO-specific country code mapping (e.g., "703" → "SK")
- Role normalization for RPO-specific stakeholder types

#### API Details
- **Endpoint**: `https://api.statistics.sk/rpo/v1`
- **Search**: `GET /search?identifier={ico}` - Returns internal RPO ID
- **Entity**: `GET /entity/{id}` - Returns full entity details
- **Provider**: Statistical Office of Slovak Republic (Štatistický úrad SR)
- **License**: Creative Commons Attribution 4.0 (CC-BY 4.0)
- **Rate Limit**: 100 requests/minute

#### Updated Files
- `python/src/scrapers/rpo_slovak.py` - Real API implementation
- `python/config/constants.py` - Updated RPO URL templates
- `python/src/utils/output_normalizer.py` - Added RPO-specific role mappings
- `python/test_new_apis.py` - Updated test ICOs for RPO
- `c_sharp/RpoClient.cs` - Real API implementation with response models

#### Notes
- Banks and financial institutions are NOT in RPO (they're in NBS register)
- Use ICOs `31348262` (Wolters Kluwer SR) or `47559870` (ZELEX) for testing
- Mock fallback only used for genuine network errors, not for "not found" cases

## [1.3.0] - 2026-02-21

### Added

#### Comprehensive Logging System
- **Python**: Enhanced logger with structured logging support
- **C#: ScraperLogger class with colored console output
- Custom `MAINTENANCE` log level (between WARNING and INFO)
- Automatic logging for all operations: requests, responses, parsing, rate limiting
- Operation timing with automatic duration tracking
- Context-aware logging with ICO, URL, operation metadata

#### Python Files
- `src/utils/logger_enhanced.py` - ScraperLogger with structured JSON logging
- `src/scrapers/base.py` - Enhanced logging methods (log_request, log_response, log_parse_start, etc.)
- `src/scrapers/ares_czech.py` - Updated to use enhanced logging throughout
- `src/scrapers/justice_czech.py` - Updated to use enhanced logging with timing
- `src/scrapers/orsr_slovak.py` - Updated to use enhanced logging
- `src/scrapers/rpvs_slovak.py` - Updated to use enhanced logging

#### C# Files
- `ScraperLogger.cs` - New logger with colored output and operation timing
- `AresClient.cs` - Updated to use ScraperLogger
- `JusticeClient.cs` - Updated to use ScraperLogger
- `OrsrClient.cs` - Updated to use ScraperLogger
- `RpvsClient.cs` - Updated to use ScraperLogger

#### Documentation
- `LOGGING.md` - Complete logging system documentation

#### Log Format
**Console:**
```
[HH:mm:ss.fff] SOURCENAME | LEVEL  | Message
```

**File (JSON):**
```json
{
  "timestamp": "2026-02-21T10:30:45.123456",
  "level": "INFO",
  "logger": "src.scrapers.ares_czech.ARESCzechScraper",
  "message": "Search started: by_id = 00006947",
  "scraper": "ARES_CZ",
  "extra": {"identifier": "00006947"}
}
```

#### Available Log Methods

**Python & C#:**
- `log_request(method, url)` - Log HTTP request
- `log_response(url, status_code, duration_ms)` - Log HTTP response with timing
- `log_parse_start(source)` - Log parse operation start
- `log_parse_complete(source, items_found)` - Log parse completion
- `log_maintenance(source)` - Log maintenance detection
- `log_rate_limit(delay)` - Log rate limit delay
- `log_mock_fallback(reason)` - Log mock data usage
- `log_search_start(identifier, search_type)` - Log search start
- `log_search_complete(results_count, identifier)` - Log search complete
- `log_error(operation, exception, context)` - Log error with context
- `log_operation_start(operation, context)` - Context manager for operation timing

## [1.2.0] - 2026-02-21

### Added

#### Maintenance Detection
- **Python**: `justice_czech.py` - Added maintenance detection for Justice.cz
- **C#**: `JusticeClient.cs` - Added `CheckMaintenance()` method
- **Constants**: Added `JUSTICE_MAINTENANCE_INDICATORS`, maintenance URLs
- Returns standardized maintenance response when site is under maintenance
- Detects HTTP 503 errors and maintenance page content
- Documentation: `MAINTENANCE_GUIDE.md` - Complete maintenance window documentation

#### Maintenance Response Format
```json
{
  "entity": {"status": "maintenance"},
  "metadata": {
    "maintenance": true,
    "maintenance_message": "Justice.cz is under maintenance...",
    "note": "Typical maintenance: Sunday nights 02:00-06:00 CET"
  }
}
```

#### Updated Documentation
- `README.md` - Added maintenance notes to API Status Summary
- `constants.py` - Added maintenance indicators and URLs for Justice.cz and ESM
- `MAINTENANCE_GUIDE.md` - Complete guide for handling maintenance windows

### Changed
- Justice.cz scraper now returns maintenance response instead of None during maintenance
- ESM scraper updated with maintenance schedule information
- README.md API Status Summary now includes maintenance column

## [1.1.0] - 2026-02-21

### Added

#### ARES Sub-Source Extraction
- **Python**: `ares_czech.py` - Added `include_subsource` parameter to `search_by_id()`
- **C#**: `AresClient.cs` - Added `includeSubsource` parameter to `SearchByICOAsync()`
- Extracts data from 10+ Czech sub-registries embedded in ARES response:
  - **RZP** (Commercial Register / Justice.cz)
  - **ROS** (RES - Resident Income Tax)
  - **VR** (Vermont Register - Real Estate)
  - **RES** (Resident Income Tax)
  - **DPH** (VAT Register)
  - **RPSH** (Statistical Register)
  - **SD** (Tax Debts Register)
  - **IR** (Income Tax Register)
  - **RS** (Synonyms Register)
  - **RED** (Register of Entrepreneurs)
- Returns `subsource` object with:
  - `registrations` - Status of each sub-source (AKTIVNI/NEEXISTUJICI)
  - `additional_data` - Detailed data from active sub-sources
  - `active_count` - Number of active sub-sources
  - `ros_legal_form` - Legal form from ROS registry

#### Python Classes
- `ARESSubsource` - Sub-source information container
- `ARESRegistrationStatus` - Status for each sub-source
- `ARESAdditionalData` - Detailed data from sub-sources

#### C# Classes
- `AresSubsource` - Sub-source information container
- `AresRegistrationStatus` - Status for each sub-source
- `AresAdditionalData` - Detailed data from sub-sources
- `AresDalsiUdaje`, `AresObchodniJmenoEntry`, `AresSidloEntry` - Raw ARES data models

#### Documentation
- Updated `API_USAGE.md` with ARES sub-source extraction examples
- Updated `README.md` with sub-source feature description
- Added sub-source response structure documentation

### Changed
- `OutputNormalizer.cs` - Added `Subsource` property to `UnifiedData`

### Fixed
- VAT status detection in ARES client now uses `stavZdrojeDph` instead of `dph`

## [1.0.0] - 2026-02-19

### Added

#### Unified Output Format
- **BREAKING**: All scrapers now return unified output format with `entity`, `holders`, `tax_info`, `metadata` sections
- Removed `raw` field from all outputs for cleaner format
- Standardized field names across all scrapers

#### Python Implementation
- Created `output_normalizer.py` with dataclasses for unified output
- `UnifiedOutput` - Complete output structure
- `UnifiedEntity` - Company information
- `UnifiedHolder` - Holder/owner with `holder_type`, `role`, `ownership_pct_direct`
- `UnifiedAddress` - Standardized address with `country_code` (ISO 3166-1 alpha-2)
- `UnifiedTaxInfo` - Tax information with `tax_debts`
- `UnifiedMetadata` - Source metadata with `register_url`, `is_mock`

#### C# Implementation
- Created `OutputNormalizer.cs` with classes matching Python dataclasses
- `UnifiedOutput`, `UnifiedEntity`, `UnifiedHolder`, `UnifiedAddress`, `UnifiedTaxInfo`, `UnifiedMetadata`
- `OutputNormalizer` helper class with normalization methods

#### Scrapers Updated

##### Python
- `ares_czech.py` - Returns unified format with entity and tax_info
- `orsr_slovak.py` - Returns unified format with entity
- `rpo_slovak.py` - Returns unified format with entity
- `rpvs_slovak.py` - Returns unified format with holders (UBO data)
- `justice_czech.py` - Returns unified format with holders (shareholders + board)
- `esm_czech.py` - Returns unified format with holders (UBO data)
- `financna_sprava_slovak.py` - Returns unified format with tax_info

##### C#
- `AresClient.cs` - Returns `UnifiedOutput`
- `OrsrClient.cs` - Returns `UnifiedOutput`
- `RpoClient.cs` - Returns `UnifiedOutput`
- `RpvsClient.cs` - Returns `UnifiedOutput`
- `JusticeClient.cs` - Returns `UnifiedOutput`
- `EsmClient.cs` - Returns `UnifiedOutput`
- `FinancnaSpravaClient.cs` - Returns `UnifiedOutput`

#### Field Normalization
- Country codes normalized to ISO 3166-1 alpha-2 format (`SK`, `CZ`, `AT`, `DE`, etc.)
- Status values normalized (`active`, `cancelled`, `in_liquidation`, `bankruptcy`, `dissolved`, `suspended`)
- Holder types detected automatically (`individual`, `entity`, `trust_fund`)
- Holder roles normalized (`shareholder`, `beneficial_owner`, `statutory_body`, `procurist`, `liquidator`)

#### Documentation
- Created comprehensive `README.md` with usage examples
- Created `API.md` with detailed API reference
- Created `requirements.txt` for Python dependencies
- Created `SkCzScrapers.csproj` for C# project

### Changed

#### Field Name Changes
| Old Field | New Field | Location |
|-----------|-----------|----------|
| `ico` | `entity.ico_registry` | All scrapers |
| `name` | `entity.company_name_registry` | All scrapers |
| `ubos` | `holders` | RPVS, ESM |
| `dic` | `tax_info.tax_id` | ARES, Finančná |
| `vat_status` | `tax_info.vat_status` | Finančná |
| `source` | `metadata.source` | All scrapers |
| `retrieved_at` | `metadata.retrieved_at` | All scrapers |
| `mock` | `metadata.is_mock` | All scrapers |

#### Holder Field Changes
| Old Field | New Field |
|-----------|-----------|
| `ownership_percentage` | `ownership_pct_direct` |
| `voting_rights` | `voting_rights_pct` |

### Fixed
- Dataclass ordering issues in `output_normalizer.py`
- Proper handling of null values in output

---

## [0.1.0] - Initial Implementation

### Added
- Python scraper implementations for ARES, ORSR, RPO, RPVS, Justice, ESM, Finančná správa
- C# client implementations for all sources
- Base scraper class with common functionality
- HTTP client with rate limiting
- JSON handler for file operations
- Logger utilities
- Field mapper for normalization
- Mock data fallbacks for unavailable APIs
