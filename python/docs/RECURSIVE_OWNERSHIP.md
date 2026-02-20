# Recursive UBO/IBO Search Implementation

## Overview

This document describes the recursive ownership tracing functionality for identifying **Ultimate Beneficial Owners (UBO)** and **Indirect Beneficial Owners (IBO)** through multi-level corporate structures.

## Concepts

### UBO (Ultimate Beneficial Owner)
An individual or entity that ultimately owns or controls a company, regardless of intermediate corporate layers.

### IBO (Indirect Beneficial Owner)
An individual who owns a company indirectly through corporate chains. Ownership percentage is calculated by multiplying percentages along the ownership chain.

**Example:**
```
Company A owns 50% of Company B
Person X owns 100% of Company A
Person X's indirect ownership of Company B = 50% * 100% = 50%
```

### Cross-Border Ownership
Ownership chains that span multiple countries (e.g., SK → AT). The system follows these chains when enabled.

## Architecture

### Components

```
python/src/scrapers/recursive_scraper.py
    ├── OwnershipNode          # Tree node representing an entity/individual
    └── RecursiveScraper       # Main recursive search class

python/src/company_registry_api.py
    └── CompanyRegistryAPI     # Public API facade with recursive methods

python/src/utils/output_normalizer.py
    ├── Metadata               # Extended with ownership fields
    └── Holder                 # Extended with chain tracking
```

### Data Flow

```
┌─────────────────┐
│   API Call      │
│  (ICO, depth)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   RecursiveScraper                 │
│                                    │
│  1. build_ownership_tree()         │
│     ├── Detect country             │
│     ├── Get UBO data (RPVS/ESM)    │
│     ├── Process owners             │
│     └── Recurse for corporate      │
│        owners > 25%                │
│                                    │
│  2. to_unified_output()            │
│     ├── Extract UBOs               │
│     ├── Calculate IBOs             │
│     └── Build metadata             │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│   Unified Output                   │
│                                    │
│  {                                 │
│    entity: {...},                  │
│    holders: [...],                 │
│    metadata: {                     │
│      ultimate_beneficial_owners,   │
│      indirect_beneficial_owners,   │
│      ownership_tree,               │
│      ownership_depth               │
│    }                              │
│  }                                │
└─────────────────────────────────────┘
```

## API Reference

### CompanyRegistryAPI Methods

#### `get_recursive_ubo(ico, max_depth=5, country=None)`

Get complete UBO tree to specified depth.

**Parameters:**
- `ico` (str): Company identification number
- `max_depth` (int): Maximum recursion depth (default: 5)
- `country` (Country): Country code (auto-detected if not specified)

**Returns:**
```python
{
    "entity": {
        "ico_registry": "06649114",
        "company_name_registry": "Prusa Research a.s.",
        "status": "active"
    },
    "holders": [
        {
            "name": "Josef Průša",
            "holder_type": "individual",
            "role": "beneficial_owner",
            "ownership_pct_direct": 100.0,
            "chain_depth": 1,
            "is_ultimate": true,
            "ownership_path": ["Prusa Research a.s.", "Josef Průša"]
        }
    ],
    "metadata": {
        "source": "RECURSIVE",
        "ownership_depth": 3,
        "ultimate_beneficial_owners": [
            {
                "name": "Josef Průša",
                "ownership_percentage": 100.0,
                "is_individual": true,
                "country": "CZ",
                "path": "Prusa Research a.s. -> Josef Průša"
            }
        ],
        "indirect_beneficial_owners": [],
        "ownership_tree": {...}
    }
}
```

#### `get_ibo_summary(ico, max_depth=5, country=None)`

Get Indirect Beneficial Owner summary.

**Returns:**
```python
{
    "company_name": "Slovenská sporiteľňa, a.s.",
    "ico": "35763491",
    "country": "SK",
    "indirect_beneficial_owners": [
        {
            "name": "Individual Name",
            "indirect_ownership_pct": 75.0,
            "path": "Company A -> Company B -> Individual",
            "depth": 3
        }
    ],
    "total_indirect_ownership": 75.0,
    "ownership_depth": 3
}
```

#### `get_ownership_tree(ico, max_depth=5, country=None)`

Get full ownership tree with analysis.

**Returns:**
```python
{
    "company_name": "Slovenská sporiteľňa, a.s.",
    "ico": "35763491",
    "tree": {
        "ico": "35763491",
        "name": "Slovenská sporiteľňa, a.s.",
        "children": [...]
    },
    "summary": {
        "max_depth_reached": 2,
        "entity_counts": {"total_entities": 2, "total_individuals": 1}
    },
    "concentration_risk": {
        "has_concentration_risk": true,
        "dominant_owner": "Erste Group Bank AG",
        "dominant_ownership_pct": 100.0
    },
    "cross_border_exposure": [
        {
            "from_country": "SK",
            "to_country": "AT",
            "entity_name": "Erste Group Bank AG",
            "ownership_percentage": 100.0
        }
    ]
}
```

#### `print_ownership_tree(ico, max_depth=5, country=None)`

Print tree visualization to console.

**Output:**
```
Slovenská sporiteľňa, a.s. (SK) - 100.0% [Company]
  └── Erste Group Bank AG (AT) - 100.0% [Entity]
```

## RecursiveScraper Class

### Core Methods

#### `build_ownership_tree(ico, country="auto")`

Builds complete ownership tree with cycle detection.

**Features:**
- Auto-detects country from ICO format
- Prevents infinite loops with visited set
- Follows corporate owners with ≥25% ownership
- Supports cross-border chain following

#### `extract_ultimate_owners(root)`

Extracts all leaf nodes (UBOs) from the tree.

#### `calculate_indirect_owners(root)`

Calculates indirect ownership percentages.

**Algorithm:**
```
For each node in tree:
  IF node is individual AND has corporate ancestors:
    indirect_ownership = product of all ownership percentages along path
    ADD to IBO list
```

#### `find_concentration_risk(root)`

Analyzes ownership concentration.

**Returns:**
```python
{
    "has_concentration_risk": bool,
    "dominant_owner": str | None,
    "dominant_ownership_pct": float,
    "total_traced_ownership": float
}
```

#### `get_cross_border_exposure(root)`

Identifies all cross-border ownership links.

## Configuration

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `OWNERSHIP_THRESHOLD` | 25.0 | Minimum % to follow corporate chains |
| `max_depth` | 5 | Maximum recursion depth |
| `follow_cross_border` | True | Enable cross-border chain following |

## Testing

### Test Script

```bash
cd python
python3 test_recursive_ownership.py
```

### Test Scenarios

1. **Simple Chain** - Direct individual owner
2. **Cross-Border** - SK → AT ownership
3. **Mixed Ownership** - Direct + indirect owners
4. **Cycle Detection** - Detects circular ownership
5. **IBO Calculation** - Verifies percentage multiplication

### Individual Tests

```bash
# Simple chain
python3 test_recursive_ownership.py --scenario simple

# Cross-border
python3 test_recursive_ownership.py --scenario cross_border

# Print tree for specific ICO
python3 test_recursive_ownership.py --tree --ico 06649114
```

## Examples

### Example 1: Simple Czech Company

```python
from src.company_registry_api import CompanyRegistryAPI

api = CompanyRegistryAPI()

# Get UBOs for Prusa Research
result = api.get_recursive_ubo("06649114", max_depth=3)

print(f"Company: {result['entity']['company_name_registry']}")
for ubo in result['metadata']['ultimate_beneficial_owners']:
    print(f"  UBO: {ubo['name']} - {ubo['ownership_percentage']}%")
```

**Output:**
```
Company: Prusa Research a.s.
  UBO: Josef Průša - 100.0%
```

### Example 2: Slovak Bank with Cross-Border Ownership

```python
from src.company_registry_api import CompanyRegistryAPI, Country

api = CompanyRegistryAPI()

# Get ownership tree for Slovak bank
tree = api.get_ownership_tree("35763491", max_depth=5, country=Country.SLOVAKIA)

print(f"Company: {tree['company_name']}")
print(f"Concentration Risk: {tree['concentration_risk']['has_concentration_risk']}")

for link in tree['cross_border_exposure']:
    print(f"  {link['from_country']} → {link['to_country']}: {link['entity_name']}")
```

**Output:**
```
Company: Slovenská sporiteľňa, a.s.
Concentration Risk: True
  SK → AT: Erste Group Bank AG
```

### Example 3: Indirect Ownership Calculation

```python
from src.company_registry_api import CompanyRegistryAPI, Country

api = CompanyRegistryAPI()

# Get IBO summary
ibo = api.get_ibo_summary("35763491", max_depth=5, country=Country.SLOVAKIA)

print(f"Total Indirect Ownership: {ibo['total_indirect_ownership']}%")

for owner in ibo['indirect_beneficial_owners']:
    print(f"  {owner['name']}: {owner['indirect_ownership_pct']}%")
    print(f"    Path: {owner['path']}")
```

## Data Structures

### OwnershipNode

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

### Extended Metadata

```python
@dataclass
class Metadata:
    # ... existing fields ...
    ownership_depth: int
    ultimate_beneficial_owners: List[Dict[str, Any]]
    indirect_beneficial_owners: List[Dict[str, Any]]
    ownership_tree: Dict[str, Any]
```

### Extended Holder

```python
@dataclass
class Holder:
    # ... existing fields ...
    chain_depth: int
    is_ultimate: bool
    direct_ownership_pct: float
    indirect_ownership_pct: float
    ownership_path: List[str]
```

## Limitations

1. **Mock Data Dependency** - ESM (Czech UBO register) requires AML certification; mock data is used
2. **RPVS Coverage** - Slovak RPVS only contains companies with government contracts
3. **Depth Limit** - Default max depth of 5 to prevent excessive recursion
4. **Threshold** - Only follows corporate chains with ≥25% ownership

## Future Enhancements

1. **True Cross-Border URCL** - Integrate with Ultimate Beneficial Owner registers across EU
2. **Confidence Scoring** - Add scoring based on data source reliability
3. **Graph Visualization** - Export to GraphML/JSON for visualization tools
4. **Historical Tracking** - Track ownership changes over time
5. **Batch Processing** - Process multiple ICOs in parallel

## See Also

- `python/test_recursive_ownership.py` - Test suite
- `python/src/scrapers/recursive_scraper.py` - Implementation
- `python/src/company_registry_api.py` - Public API
- `CLAUDE.md` - Project documentation
