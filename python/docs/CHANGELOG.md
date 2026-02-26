# Changelog

All notable changes to the SK/CZ Business Registry Scrapers project.

## [1.1.0] - 2026-02-21

### Added - ARES Sub-Source Extraction

#### Modified Files
- `python/src/scrapers/ares_czech.py` - Added sub-source extraction functionality

#### New Methods

**`ARESCzechScraper.search_by_id(ico, include_subsource=False)`**
- Added `include_subsource` parameter
- Returns `subsource` object in result when enabled

**`ARESCzechScraper._extract_subsource(data)`**
- Extracts sub-source registration information from ARES response
- Returns dictionary with:
  - `registrations` - Status of each sub-source (AKTIVNI/NEEXISTUJICI/HISTORICKY)
  - `additional_data` - Detailed data from active sub-sources (dalsiUdaje)
  - `active_count` - Number of active sub-sources
  - `ros_legal_form` - Legal form from ROS registry

#### Sub-Sources Supported
| Code | Registry | Description |
|------|----------|-------------|
| RZP | Rejstřík osob | Commercial Register (Justice.cz) |
| ROS | RES | Resident Income Tax |
| VR | VR | Vermont Register (Real Estate) |
| RES | RES | Resident Income Tax |
| DPH | DPH | VAT Register |
| RPSH | RPSH | Statistical Register |
| SD | SD | Tax Debts Register |
| IR | IR | Income Tax Register |
| RS | RS | Synonyms Register |
| RED | RED | Register of Entrepreneurs |

#### Usage Example
```python
from src.scrapers.ares_czech import ARESCzechScraper

scraper = ARESCzechScraper()
result = scraper.search_by_id('05984866', include_subsource=True)

# Check sub-source status
subsource = result['subsource']
print(f"Active sub-sources: {subsource['active_count']}")

# Check if company is in Commercial Register
if subsource['registrations']['RZP']['is_active']:
    print("Company is in Commercial Register")
```

## [Unreleased] - 2025-02-19

### Added - Recursive UBO/IBO Search

#### New Files
- `python/src/scrapers/recursive_scraper.py` - Multi-level ownership chain traversal
- `python/test_recursive_ownership.py` - Comprehensive test suite for recursive ownership
- `python/docs/RECURSIVE_OWNERSHIP.md` - Full documentation

#### Modified Files
- `python/src/company_registry_api.py` - Added recursive ownership methods
- `python/src/utils/output_normalizer.py` - Extended Metadata and Holder dataclasses

#### New API Methods (CompanyRegistryAPI)

**`get_recursive_ubo(ico, max_depth=5, country=None)`**
- Returns complete UBO tree to specified depth
- Includes ownership paths and cross-border detection

**`get_ibo_summary(ico, max_depth=5, country=None)`**
- Returns Indirect Beneficial Owner summary
- Calculates indirect ownership percentages

**`get_ownership_tree(ico, max_depth=5, country=None)`**
- Returns full ownership tree with analysis
- Includes concentration risk assessment
- Lists all cross-border ownership links

**`print_ownership_tree(ico, max_depth=5, country=None)`**
- Prints tree visualization to console

#### New RecursiveScraper Methods

**Tree Building**
- `build_ownership_tree(ico, country="auto")` - Build ownership tree with cycle detection
- `to_unified_output(root, ico, country)` - Convert tree to unified output format

**Analysis Methods**
- `extract_ultimate_owners(root)` - Extract UBOs from tree
- `calculate_indirect_owners(root)` - Calculate IBOs with percentage multiplication
- `find_concentration_risk(root)` - Analyze ownership concentration
- `get_cross_border_exposure(root)` - Identify cross-border links
- `get_ownership_path(root, target_ico)` - Get path to specific entity
- `get_ownership_depth_reached(root)` - Get maximum depth
- `get_entity_count(root)` - Count entities and individuals

#### Data Structure Changes

**Metadata (output_normalizer.py)**
```python
# New fields:
ownership_depth: int
ultimate_beneficial_owners: List[Dict[str, Any]]
indirect_beneficial_owners: List[Dict[str, Any]]
ownership_tree: Dict[str, Any]
```

**Holder (output_normalizer.py)**
```python
# New fields:
chain_depth: int
is_ultimate: bool
direct_ownership_pct: float
indirect_ownership_pct: float
ownership_path: List[str]
```

**OwnershipNode (recursive_scraper.py)**
```python
@dataclass
class OwnershipNode:
    ico: str
    name: str
    country: str
    ownership_percentage: float
    is_individual: bool
    children: List[OwnershipNode]
    source: str
    depth: int
    parent: Optional[OwnershipNode]
    path_from_root: List[str]
```

#### Features

- **Multi-level ownership tracing** - Follow corporate chains to identify ultimate owners
- **Cycle detection** - Prevents infinite loops in circular ownership structures
- **Cross-border support** - Follows ownership across SK/CZ border
- **IBO calculation** - Multiplies ownership percentages along chains
- **Concentration risk analysis** - Identifies entities with >50% control
- **Tree visualization** - ASCII tree output for debugging

#### Configuration

- `OWNERSHIP_THRESHOLD = 25.0` - Minimum % to follow corporate chains
- `max_depth = 5` - Default maximum recursion depth
- `follow_cross_border = True` - Enable cross-border chain following

#### Usage Examples

```python
from src.company_registry_api import CompanyRegistryAPI, Country

api = CompanyRegistryAPI()

# Get recursive UBOs
result = api.get_recursive_ubo("06649114", max_depth=3)
for ubo in result['metadata']['ultimate_beneficial_owners']:
    print(f"{ubo['name']}: {ubo['ownership_percentage']}%")

# Get IBO summary
ibo = api.get_ibo_summary("35763491", max_depth=5, country=Country.SLOVAKIA)
print(f"Total indirect ownership: {ibo['total_indirect_ownership']}%")

# Get full tree with analysis
tree = api.get_ownership_tree("35763491", max_depth=5, country=Country.SLOVAKIA)
print(f"Concentration risk: {tree['concentration_risk']['has_concentration_risk']}")

# Print visualization
api.print_ownership_tree("06649114")
```

---

## [Previous Releases]

### Initial Implementation
- ARES Czech scraper (REST API)
- ORSR Slovak scraper (HTML scraping)
- RPVS Slovak scraper (OData API)
- ESM Czech scraper (placeholder - AML restricted)
- Justice Czech scraper (HTML scraping)
- Additional scrapers: DPH, VR, RES, Smlouvy, CNB, RPO, RUZ, NBS, IVES, Finančná správa, Stats
