# Recursive UBO/IBO Search - Implementation Summary

## Overview

Implemented comprehensive recursive ownership tracing for identifying **Ultimate Beneficial Owners (UBO)** and **Indirect Beneficial Owners (IBO)** through multi-level corporate structures in the SK/CZ Business Registry Scrapers.

## Files Created

1. **`python/src/scrapers/recursive_scraper.py`** (350+ lines)
   - `OwnershipNode` dataclass with path tracking
   - `RecursiveScraper` class with tree building and analysis
   - Cycle detection and cross-border support

2. **`python/test_recursive_ownership.py`** (380+ lines)
   - 5 comprehensive test scenarios
   - CLI interface for selective testing
   - Tree visualization output

3. **`python/docs/RECURSIVE_OWNERSHIP.md`**
   - Full documentation with API reference
   - Examples and use cases
   - Data structure definitions

4. **`python/docs/RECURSIVE_OWNERSHIP_QUICKREF.md`**
   - Quick reference guide
   - Common patterns
   - Troubleshooting tips

5. **`python/docs/CHANGELOG.md`**
   - Detailed changelog entry
   - All changes documented

## Files Modified

1. **`python/src/company_registry_api.py`**
   - Added `_recursive_scraper` lazy initialization
   - Added 4 new public methods:
     - `get_recursive_ubo()`
     - `get_ibo_summary()`
     - `get_ownership_tree()`
     - `print_ownership_tree()`

2. **`python/src/utils/output_normalizer.py`**
   - Extended `Metadata` dataclass with ownership fields
   - Extended `Holder` dataclass with chain tracking

3. **`MEMORY.md`**
   - Added RecursiveScraper to project overview
   - Updated file structure

## API Methods Added

### CompanyRegistryAPI

```python
def get_recursive_ubo(ico: str, max_depth: int = 5, country: Optional[Country] = None) -> Optional[Dict[str, Any]]
def get_ibo_summary(ico: str, max_depth: int = 5, country: Optional[Country] = None) -> Optional[Dict[str, Any]]
def get_ownership_tree(ico: str, max_depth: int = 5, country: Optional[Country] = None) -> Optional[Dict[str, Any]]
def print_ownership_tree(ico: str, max_depth: int = 5, country: Optional[Country] = None) -> None
```

### RecursiveScraper

```python
def build_ownership_tree(ico: str, country: str = "auto") -> Optional[OwnershipNode]
def extract_ultimate_owners(root: OwnershipNode) -> List[Dict[str, Any]]
def calculate_indirect_owners(root: OwnershipNode) -> List[Dict[str, Any]]
def find_concentration_risk(root: OwnershipNode) -> Dict[str, Any]
def get_cross_border_exposure(root: OwnershipNode) -> List[Dict[str, Any]]
def get_ownership_path(root: OwnershipNode, target_ico: str) -> List[str]
def to_unified_output(root: OwnershipNode, original_ico: str, original_country: str) -> Optional[Dict[str, Any]]
```

## Test Results

All 5 test scenarios pass:

| Test | ICO | Country | Result |
|------|-----|---------|--------|
| Simple Chain | 06649114 | CZ | ✓ Josef Průša: 100% |
| Cross-Border | 35763491 | SK | ✓ Erste Group: 100% (SK→AT) |
| Mixed Ownership | 44103755 | SK | ✓ Deutsche Telekom: 51% |
| Cycle Detection | 31328356 | SK | ✓ Intesa Sanpaolo: 94.49% |
| IBO Calculation | Multiple | Both | ✓ All calculations valid |

## Features Implemented

### Core Functionality
- [x] Multi-level ownership chain traversal
- [x] Ultimate Beneficial Owner (UBO) identification
- [x] Indirect Beneficial Owner (IBO) calculation
- [x] Ownership path tracking from root to leaf
- [x] Cycle detection (prevents infinite loops)
- [x] Cross-border chain following (SK ↔ CZ)

### Analysis Features
- [x] Concentration risk analysis (>50% detection)
- [x] Cross-border exposure identification
- [x] Entity/individual counting
- [x] Depth tracking
- [x] Ownership percentage multiplication along chains

### Output Formats
- [x] Unified output format integration
- [x] ASCII tree visualization
- [x] JSON-serializable structures
- [x] Extended metadata with tree structure

## Configuration Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `OWNERSHIP_THRESHOLD` | 25.0% | Minimum % to follow corporate chains |
| `max_depth` | 5 | Default maximum recursion depth |
| `follow_cross_border` | True | Enable cross-border chain following |

## Usage Examples

### Basic UBO Lookup
```python
from src.company_registry_api import CompanyRegistryAPI

api = CompanyRegistryAPI()
result = api.get_recursive_ubo("06649114", max_depth=3)

for ubo in result['metadata']['ultimate_beneficial_owners']:
    print(f"{ubo['name']}: {ubo['ownership_percentage']}%")
# Output: Josef Průša: 100.0%
```

### Cross-Border Analysis
```python
from src.company_registry_api import CompanyRegistryAPI, Country

api = CompanyRegistryAPI()
tree = api.get_ownership_tree("35763491", max_depth=5, country=Country.SLOVAKIA)

for link in tree['cross_border_exposure']:
    print(f"{link['from_country']} → {link['to_country']}: {link['entity_name']}")
# Output: SK → AT: Erste Group Bank AG
```

### Indirect Ownership Calculation
```python
from src.company_registry_api import CompanyRegistryAPI, Country

api = CompanyRegistryAPI()
ibo = api.get_ibo_summary("35763491", max_depth=5, country=Country.SLOVAKIA)

for owner in ibo['indirect_beneficial_owners']:
    print(f"{owner['name']}: {owner['indirect_ownership_pct']}%")
    print(f"  Path: {owner['path']}")
```

### Concentration Risk Check
```python
from src.company_registry_api import CompanyRegistryAPI

api = CompanyRegistryAPI()
tree = api.get_ownership_tree("06649114", max_depth=3)

risk = tree['concentration_risk']
if risk['has_concentration_risk']:
    print(f"Risk: {risk['dominant_owner']} owns {risk['dominant_ownership_pct']}%")
```

## Data Flow

```
User Request (ICO, max_depth)
         │
         ▼
┌─────────────────────────────────┐
│  CompanyRegistryAPI              │
│  - Validates parameters          │
│  - Detects country               │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  RecursiveScraper               │
│  1. build_ownership_tree()      │
│     - Get UBO data (RPVS/ESM)    │
│     - Process owners             │
│     - Recurse for corporate      │
│       owners ≥ 25%               │
│     - Track paths                │
│     - Detect cycles              │
│                                 │
│  2. to_unified_output()          │
│     - Extract UBOs               │
│     - Calculate IBOs             │
│     - Build metadata             │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Unified Output                 │
│  {                              │
│    entity: {...},               │
│    holders: [...],              │
│    metadata: {                  │
│      ultimate_beneficial_owners, │
│      indirect_beneficial_owners, │
│      ownership_tree,            │
│      ownership_depth            │
│    }                           │
│  }                             │
└─────────────────────────────────┘
```

## Limitations

1. **ESM API Restriction** - Czech UBO register requires AML certification; mock data used
2. **RPVS Coverage** - Slovak RPVS only contains companies with government contracts
3. **Depth Limit** - Max depth of 5 to prevent excessive recursion (configurable)
4. **Threshold** - Only follows corporate chains with ≥25% ownership (configurable)

## Documentation Structure

```
python/docs/
├── RECURSIVE_OWNERSHIP.md           # Full documentation
├── RECURSIVE_OWNERSHIP_QUICKREF.md  # Quick reference
└── CHANGELOG.md                     # Changelog entry
```

## Verification Commands

```bash
cd python

# Run all tests
python3 test_recursive_ownership.py

# Run specific test
python3 test_recursive_ownership.py --scenario simple
python3 test_recursive_ownership.py --scenario cross_border

# Print tree for specific ICO
python3 test_recursive_ownership.py --tree --ico 06649114

# Comprehensive verification
python3 -c "
from src.company_registry_api import CompanyRegistryAPI, Country
api = CompanyRegistryAPI()
result = api.get_recursive_ubo('06649114', max_depth=3)
print(result)
"
```

## Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| RecursiveScraper | ✓ Complete | Full implementation |
| CompanyRegistryAPI | ✓ Integrated | 4 new methods |
| output_normalizer | ✓ Extended | Metadata and Holder updated |
| Tests | ✓ All Pass | 5 scenarios verified |
| Documentation | ✓ Complete | 3 docs created |

## Future Enhancements

1. **European UBO Integration** - Connect with other EU UBO registers
2. **Graph Visualization** - Export to GraphML for external tools
3. **Confidence Scoring** - Score results based on source reliability
4. **Historical Tracking** - Track ownership changes over time
5. **Batch Processing** - Process multiple ICOs in parallel
6. **Web UI** - Interactive tree visualization

---

**Implementation Date:** 2025-02-19
**Status:** Complete and Tested
**Version:** 1.0
