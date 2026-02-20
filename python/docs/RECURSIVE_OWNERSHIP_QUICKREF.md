# Recursive Ownership Quick Reference

## Quick Start

```python
from src.company_registry_api import CompanyRegistryAPI, Country

api = CompanyRegistryAPI()

# Get UBOs (Ultimate Beneficial Owners)
result = api.get_recursive_ubo("06649114", max_depth=3)

# Get IBOs (Indirect Beneficial Owners)
ibo = api.get_ibo_summary("35763491", max_depth=5, country=Country.SLOVAKIA)

# Get full tree analysis
tree = api.get_ownership_tree("35763491", max_depth=5, country=Country.SLOVAKIA)

# Print visualization
api.print_ownership_tree("06649114")
```

## Methods Summary

| Method | Returns | Use Case |
|--------|---------|----------|
| `get_recursive_ubo()` | UBOs with paths | Identify ultimate owners |
| `get_ibo_summary()` | Indirect owners | Calculate indirect ownership |
| `get_ownership_tree()` | Full analysis | Complete picture with risk metrics |
| `print_ownership_tree()` | ASCII visualization | Debugging/overview |

## Output Structure

### `get_recursive_ubo()`

```python
{
    "entity": {...},
    "holders": [...],
    "metadata": {
        "ultimate_beneficial_owners": [
            {
                "name": "Owner Name",
                "ownership_percentage": 100.0,
                "country": "CZ",
                "is_individual": true,
                "path": "Company -> Owner"
            }
        ],
        "ownership_tree": {...}
    }
}
```

### `get_ibo_summary()`

```python
{
    "company_name": "Company Name",
    "ico": "12345678",
    "indirect_beneficial_owners": [
        {
            "name": "Owner Name",
            "indirect_ownership_pct": 75.0,
            "path": "Co A -> Co B -> Owner",
            "depth": 3
        }
    ],
    "total_indirect_ownership": 75.0
}
```

### `get_ownership_tree()`

```python
{
    "company_name": "Company Name",
    "tree": {...},
    "summary": {
        "max_depth_reached": 2,
        "entity_counts": {...}
    },
    "concentration_risk": {
        "has_concentration_risk": true,
        "dominant_owner": "Entity Name",
        "dominant_ownership_pct": 100.0
    },
    "cross_border_exposure": [
        {
            "from_country": "SK",
            "to_country": "AT",
            "entity_name": "Bank Name",
            "ownership_percentage": 100.0
        }
    ]
}
```

## Common Patterns

### 1. Simple UBO Lookup

```python
api = CompanyRegistryAPI()
result = api.get_recursive_ubo("06649114")

for ubo in result['metadata']['ultimate_beneficial_owners']:
    print(f"{ubo['name']}: {ubo['ownership_percentage']}%")
```

### 2. Cross-Border Analysis

```python
tree = api.get_ownership_tree("35763491", country=Country.SLOVAKIA)

for link in tree['cross_border_exposure']:
    print(f"{link['from_country']} → {link['to_country']}: {link['entity_name']}")
```

### 3. Concentration Risk Check

```python
tree = api.get_ownership_tree("06649114")

if tree['concentration_risk']['has_concentration_risk']:
    owner = tree['concentration_risk']['dominant_owner']
    pct = tree['concentration_risk']['dominant_ownership_pct']
    print(f"Concentration risk: {owner} owns {pct}%")
```

### 4. Indirect Ownership Calculation

```python
ibo = api.get_ibo_summary("35763491", max_depth=5)

for owner in ibo['indirect_beneficial_owners']:
    print(f"{owner['name']}: {owner['indirect_ownership_pct']}%")
    print(f"  Chain: {' -> '.join(owner['path'].split(' -> '))}")
```

### 5. Filter by Ownership Threshold

```python
result = api.get_recursive_ubo("06649114")

# Get owners with >25% ownership
major_owners = [
    ubo for ubo in result['metadata']['ultimate_beneficial_owners']
    if ubo['ownership_percentage'] > 25
]
```

## Test ICOs

| ICO | Country | Description | Expected Result |
|-----|---------|-------------|-----------------|
| 06649114 | CZ | Prusa Research | Josef Průša (100%) |
| 35763491 | SK | Slovenská sporiteľňa | Erste Group (100%, cross-border) |
| 44103755 | SK | Slovak Telekom | Deutsche Telekom (51%, cross-border) |
| 31328356 | SK | Všeobecná úverová banka | Intesa Sanpaolo (94%) |

## Configuration

```python
from src.scrapers.recursive_scraper import RecursiveScraper

scraper = RecursiveScraper(
    max_depth=5,              # Maximum recursion depth
    follow_cross_border=True, # Follow cross-border chains
    enable_snapshots=False    # Save raw responses
)
```

## Running Tests

```bash
cd python

# All tests
python3 test_recursive_ownership.py

# Specific scenario
python3 test_recursive_ownership.py --scenario simple
python3 test_recursive_ownership.py --scenario cross_border
python3 test_recursive_ownership.py --scenario mixed

# Tree visualization
python3 test_recursive_ownership.py --tree --ico 06649114
```

## Key Concepts

| Concept | Definition |
|---------|------------|
| **UBO** | Ultimate Beneficial Owner - individual/entity at the top of ownership chain |
| **IBO** | Indirect Beneficial Owner - owns through corporate intermediaries |
| **Cross-Border** | Ownership spanning multiple countries (e.g., SK → AT) |
| **Concentration Risk** | Single entity controls >50% |
| **Depth** | Number of levels in ownership chain |

## Troubleshooting

### No UBOs Found

- May be using mock data (ESM is restricted)
- Check `is_mock` field in metadata
- Try different `max_depth` value

### Cross-Border Not Working

- Ensure `country` parameter is correct
- Slovak entities need `country=Country.SLOVAKIA`
- Czech entities need `country=Country.CZECH_REPUBLIC`

### Infinite Loop Warning

- Cycle detection is active
- Check ownership path for circular references
- Reduce `max_depth` if needed

## See Also

- [Full Documentation](RECURSIVE_OWNERSHIP.md)
- [API Reference](../README.md)
- [Test Suite](../test_recursive_ownership.py)
