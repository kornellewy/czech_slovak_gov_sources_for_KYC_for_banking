# API Reference

This document provides detailed API reference for all scrapers.

## Table of Contents

- [Python API](#python-api)
  - [BaseScraper](#basescraper)
  - [ARES Czech](#ares-czech)
  - [ORSR Slovak](#orsr-slovak)
  - [RPO Slovak](#rpo-slovak)
  - [RPVS Slovak](#rpvs-slovak)
  - [Justice Czech](#justice-czech)
  - [ESM Czech](#esm-czech)
  - [Finančná správa](#finančná-správa)
- [C# API](#c-api)
  - [UnifiedOutput](#unifiedoutput)
  - [OutputNormalizer](#outputnormalizer)
  - [Clients](#clients)

---

## Python API

### BaseScraper

Abstract base class for all scrapers.

```python
from src.scrapers.base import BaseScraper

class MyScraper(BaseScraper):
    def search_by_id(self, identifier: str) -> Optional[Dict[str, Any]]:
        # Implementation
        pass

    def search_by_name(self, name: str) -> List[Dict[str, Any]]:
        # Implementation
        pass

    def save_to_json(self, data: Dict[str, Any], filename: str) -> str:
        # Implementation
        pass
```

**Methods:**

| Method | Description |
|--------|-------------|
| `search_by_id(identifier)` | Search by IČO/ICO |
| `search_by_name(name)` | Search by company name |
| `save_to_json(data, filename)` | Save result to JSON file |
| `get_source_name()` | Return source identifier |
| `close()` | Clean up resources |
| `save_snapshot(data, identifier, source)` | Save raw data snapshot |

**Context Manager:**
```python
with ARESCzechScraper() as scraper:
    result = scraper.search_by_id("00006947")
# Automatically calls close()
```

---

### ARES Czech

```python
from src.scrapers.ares_czech import ARESCzechScraper

scraper = ARESCzechScraper(enable_snapshots=True)
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_snapshots` | bool | True | Save raw API responses |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `search_by_id(ico)` | `Dict` | Search by IČO (8 digits) |
| `search_by_name(name)` | `List[Dict]` | Not supported (returns []) |
| `save_to_json(data, filename)` | `str` | Save to output/ares/ |

**Example:**
```python
with ARESCzechScraper() as scraper:
    result = scraper.search_by_id("00006947")

    # Access unified output
    entity = result["entity"]
    tax_info = result.get("tax_info")
    metadata = result["metadata"]

    print(f"Company: {entity['company_name_registry']}")
    print(f"Status: {entity['status']}")
    print(f"VAT: {tax_info.get('vat_status') if tax_info else 'N/A'}")
```

---

### ORSR Slovak

```python
from src.scrapers.orsr_slovak import ORSRSlovakScraper

scraper = ORSRSlovakScraper(enable_snapshots=True)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `search_by_id(ico)` | `Dict` | Search by ICO |
| `search_by_name(name)` | `List[Dict]` | Search by company name |
| `get_company_detail(url)` | `Dict` | Get detailed info from detail page |

**Example:**
```python
with ORSRSlovakScraper() as scraper:
    # Search by ICO
    result = scraper.search_by_id("35763491")

    # Search by name
    results = scraper.search_by_name("Slovenská sporiteľňa")
    for r in results:
        print(f"{r['entity']['company_name_registry']} - {r['entity']['ico_registry']}")
```

---

### RPO Slovak

```python
from src.scrapers.rpo_slovak import RpoSlovakScraper

scraper = RpoSlovakScraper(enable_snapshots=True)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `search_by_id(ico)` | `Dict` | Search by ICO (uses mock data) |
| `search_by_name(name)` | `List[Dict]` | Search by name (uses mock data) |

**Example:**
```python
with RpoSlovakScraper() as scraper:
    result = scraper.search_by_id("35763491")
    entity = result["entity"]
    print(f"Company: {entity['company_name_registry']}")
    print(f"Legal Form: {entity.get('legal_form')}")
```

---

### RPVS Slovak

```python
from src.scrapers.rpvs_slovak import RpvsSlovakScraper

# Without API key
scraper = RpvsSlovakScraper(enable_snapshots=True)

# With API key
scraper = RpvsSlovakScraper(enable_snapshots=True, api_key="your-key")
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_snapshots` | bool | True | Save raw API responses |
| `api_key` | str | None | RPVS API key |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `search_by_id(ico)` | `Dict` | Get UBO data |
| `search_by_name(name)` | `List[Dict]` | Search by name |

**Example:**
```python
with RpvsSlovakScraper() as scraper:
    result = scraper.search_by_id("35763491")

    # Access holders/UBOs
    for holder in result.get("holders", []):
        print(f"Name: {holder['name']}")
        print(f"Type: {holder['holder_type']}")
        print(f"Ownership: {holder['ownership_pct_direct']}%")
```

---

### Justice Czech

```python
from src.scrapers.justice_czech import JusticeCzechScraper

scraper = JusticeCzechScraper(enable_snapshots=True)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `search_by_id(ico)` | `Dict` | Get OR data |
| `search_by_name(name)` | `List[Dict]` | Not supported (returns []) |
| `get_shareholders(ico)` | `List` | Get shareholder list |
| `get_board_members(ico)` | `List` | Get board members |

**Example:**
```python
with JusticeCzechScraper() as scraper:
    result = scraper.search_by_id("06649114")

    # Get shareholders
    shareholders = [
        h for h in result.get("holders", [])
        if h.get("role") == "shareholder"
    ]

    # Get board members
    board = [
        h for h in result.get("holders", [])
        if h.get("role") == "statutory_body"
    ]
```

---

### ESM Czech

```python
from src.scrapers.esm_czech import EsmCzechScraper

# Without API key (mock data only)
scraper = EsmCzechScraper(enable_snapshots=True)

# With API key (requires AML certification)
scraper = EsmCzechScraper(enable_snapshots=True, api_key="your-key")
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `search_by_id(ico)` | `Dict` | Get UBO data |
| `get_access_requirements()` | `Dict` | Get access requirements |
| `check_compliance(ico)` | `Dict` | Check filing compliance |

**Access Requirements:**
```python
with EsmCzechScraper() as scraper:
    req = scraper.get_access_requirements()
    print(req)
    # {
    #     "qualification": "AML obligated person...",
    #     "registration": "Required at issm.justice.cz",
    #     "api_key": "API key required",
    #     "website": "https://issm.justice.cz",
    #     "legal_basis": "Zákon o evidenci skutečných majitelů"
    # }
```

---

### Finančná správa

```python
from src.scrapers.financna_sprava_slovak import FinancnaSpravaScraper

scraper = FinancnaSpravaScraper(enable_snapshots=True)
```

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `search_by_id(ico)` | `Dict` | Get tax status |
| `get_tax_status(ico)` | `Dict` | Get full tax status |
| `get_vat_status(ico)` | `Dict` | Get VAT status only |

**Example:**
```python
with FinancnaSpravaScraper() as scraper:
    result = scraper.search_by_id("35763491")
    tax_info = result.get("tax_info", {})

    print(f"VAT ID: {tax_info.get('vat_id')}")
    print(f"VAT Status: {tax_info.get('vat_status')}")

    debts = tax_info.get("tax_debts", {})
    print(f"Has Debts: {debts.get('has_debts')}")
    print(f"Amount: {debts.get('amount_eur')} EUR")
```

---

## C# API

### UnifiedOutput

Main output class for all scrapers.

```csharp
using UnifiedOutput;

var output = new UnifiedOutput
{
    Entity = new UnifiedEntity
    {
        IcoRegistry = "00006947",
        CompanyNameRegistry = "Company Name"
    },
    Holders = new List<UnifiedHolder>(),
    TaxInfo = new UnifiedTaxInfo { VatStatus = "active" },
    Metadata = new UnifiedMetadata
    {
        Source = "ARES_CZ",
        IsMock = false
    }
};

// Convert to JSON
string json = output.ToJson(indent: true);
```

**Classes:**

| Class | Description |
|-------|-------------|
| `UnifiedOutput` | Complete output structure |
| `UnifiedEntity` | Company information |
| `UnifiedHolder` | Holder/owner information |
| `UnifiedAddress` | Address structure |
| `UnifiedTaxInfo` | Tax information |
| `TaxDebts` | Tax debt details |
| `UnifiedMetadata` | Source metadata |

---

### OutputNormalizer

Helper class for data normalization.

```csharp
using UnifiedOutput;

// Normalize country code
string? code = OutputNormalizer.NormalizeCountryCode("Slovensko"); // "SK"
string? code = OutputNormalizer.NormalizeCountryCode("Česká republika"); // "CZ"

// Normalize status
string? status = OutputNormalizer.NormalizeStatus("aktivní"); // "active"
string? status = OutputNormalizer.NormalizeStatus("zrušený"); // "cancelled"

// Get register name
string name = OutputNormalizer.GetRegisterName("ARES_CZ"); // "Register of Economic Subjects (ARES)"

// Detect holder type
var holderData = new Dictionary<string, object?> { ["name"] = "Bank AG" };
string type = OutputNormalizer.DetectHolderType(holderData); // "entity"

// Build register URL
string? url = OutputNormalizer.BuildRegisterUrl("ARES_CZ", "00006947");
```

---

### Clients

All clients follow the same pattern:

```csharp
// ARES
using var client = new Ares.AresClient();
UnifiedOutput? result = await client.SearchByICOAsync("00006947");

// ORSR
using var client = new Orsr.OrsrClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");

// RPO
using var client = new Rpo.RpoClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");

// RPVS
using var client = new Rpvs.RpvsClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");

// Justice
using var client = new Justice.JusticeClient();
UnifiedOutput? result = await client.SearchByICOAsync("06649114");

// ESM
using var client = new Esm.EsmClient();
UnifiedOutput? result = await client.SearchByICOAsync("06649114");

// Finančná správa
using var client = new FinancnaSprava.FinancnaSpravaClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");
```

---

## Output Normalizer (Python)

```python
from src.utils.output_normalizer import (
    UnifiedOutput, Entity, Holder, Address, TaxInfo, TaxDebts, Metadata,
    normalize_country_code, normalize_status, detect_holder_type,
    get_register_name, get_retrieved_at
)

# Normalize country code
code = normalize_country_code("Slovensko")  # "SK"
code = normalize_country_code("Česká republika")  # "CZ"

# Normalize status
status = normalize_status("aktivní")  # "active"
status = normalize_status("zrušený")  # "cancelled"

# Detect holder type
holder_type = detect_holder_type({"name": "Bank AG", "type": "entity"})  # "entity"

# Get register name
name = get_register_name("ARES_CZ")  # "Register of Economic Subjects (ARES)"

# Build unified output
output = UnifiedOutput(
    entity=Entity(
        ico_registry="00006947",
        company_name_registry="Company Name",
        status="active"
    ),
    holders=[
        Holder(
            holder_type="individual",
            role="beneficial_owner",
            name="John Doe",
            ownership_pct_direct=100.0
        )
    ],
    tax_info=TaxInfo(
        vat_id="CZ00006947",
        vat_status="active"
    ),
    metadata=Metadata(
        source="ARES_CZ",
        register_name=get_register_name("ARES_CZ"),
        retrieved_at=get_retrieved_at(),
        is_mock=False
    )
)

# Convert to dict/json
data = output.to_dict()
json_str = output.to_json()
```
