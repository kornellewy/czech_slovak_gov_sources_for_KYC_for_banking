# Changelog

All notable changes to this project will be documented in this file.

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
