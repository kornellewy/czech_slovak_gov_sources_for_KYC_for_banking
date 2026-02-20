# Quick Start Guide

## Prerequisites

Before starting, ensure you have:

**Python:**
- Python 3.10 or higher
- pip (Python package manager)

**C#:**
- .NET 8.0 SDK or higher

📘 **Full requirements:** See [REQUIREMENTS.md](REQUIREMENTS.md)

---

## 5-Minute Setup

### Python

```bash
# 1. Navigate to Python directory
cd python

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run example script
python3 examples.py

# 4. Run tests
python3 test_unified_output.py
```

### C#

```bash
# 1. Navigate to C# directory
cd c_sharp

# 2. Restore and build
dotnet restore
dotnet build

# 3. Run ARES test
dotnet run --project TestAres.csproj

# 4. Run unified output demo
dotnet run --project AgrofertTest.csproj
```

---

## Basic Usage

### Python

```python
from src.scrapers.ares_czech import ARESCzechScraper

# Use as context manager (auto-cleanup)
with ARESCzechScraper() as scraper:
    result = scraper.search_by_id("00006947")

    # Access data
    print(result["entity"]["company_name_registry"])
    print(result["entity"]["status"])
    print(result.get("tax_info", {}).get("vat_status"))

    # Save to file
    scraper.save_to_json(result, "company.json")
```

### C#

```csharp
using Ares;
using UnifiedOutput;

using var client = new AresClient();
UnifiedOutput? result = await client.SearchByICOAsync("00006947");

if (result != null)
{
    Console.WriteLine(result.Entity.CompanyNameRegistry);
    Console.WriteLine(result.Entity.Status);
    Console.WriteLine(result.TaxInfo?.VatStatus);

    // Save to file
    File.WriteAllText("company.json", result.ToJson());
}
```

---

## All Scrapers at a Glance

| Scraper | Python Import | C# Class | Main Method |
|---------|---------------|----------|-------------|
| ARES | `from src.scrapers.ares_czech import ARESCzechScraper` | `AresClient` | `search_by_id()` / `SearchByICOAsync()` |
| ORSR | `from src.scrapers.orsr_slovak import ORSRSlovakScraper` | `OrsrClient` | `search_by_id()` / `SearchByICOAsync()` |
| RPO | `from src.scrapers.rpo_slovak import RpoSlovakScraper` | `RpoClient` | `search_by_id()` / `SearchByICOAsync()` |
| RPVS | `from src.scrapers.rpvs_slovak import RpvsSlovakScraper` | `RpvsClient` | `search_by_id()` / `SearchByICOAsync()` |
| Justice | `from src.scrapers.justice_czech import JusticeCzechScraper` | `JusticeClient` | `search_by_id()` / `SearchByICOAsync()` |
| ESM | `from src.scrapers.esm_czech import EsmCzechScraper` | `EsmClient` | `search_by_id()` / `SearchByICOAsync()` |
| Finančná | `from src.scrapers.financna_sprava_slovak import FinancnaSpravaScraper` | `FinancnaSpravaClient` | `search_by_id()` / `SearchByICOAsync()` |

---

## Output Structure

Every scraper returns the same structure:

```
{
  "entity": { ... },      # Company information
  "holders": [ ... ],     # Owners, shareholders, board members
  "tax_info": { ... },    # VAT status, tax debts
  "metadata": { ... }     # Source, timestamp, is_mock flag
}
```

### Quick Access

```python
# Python
entity = result["entity"]
holders = result.get("holders", [])
tax = result.get("tax_info", {})
meta = result["metadata"]

# Check if mock data
if meta["is_mock"]:
    print("Using mock/fallback data")
```

```csharp
// C#
var entity = result.Entity;
var holders = result.Holders;
var tax = result.TaxInfo;
var meta = result.Metadata;

// Check if mock data
if (meta.IsMock)
{
    Console.WriteLine("Using mock/fallback data");
}
```

---

## Test ICOs

### Slovak
- `35763491` - Slovenská sporiteľňa
- `44103755` - Slovak Telekom
- `31328356` - VÚB

### Czech
- `00006947` - Ministerstvo financí
- `00216305` - Česká pošta
- `06649114` - Prusa Research

---

## Common Patterns

### Combine Multiple Sources

```python
from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.rpvs_slovak import RpvsSlovakScraper

ico = "35763491"

# Get basic info
with ARESCzechScraper() as scraper:
    ares = scraper.search_by_id(ico)

# Get UBO info
with RpvsSlovakScraper() as scraper:
    rpvs = scraper.search_by_id(ico)

# Combine
company = {
    "name": ares["entity"]["company_name_registry"],
    "owners": rpvs.get("holders", [])
}
```

### Batch Processing

```python
from src.scrapers.ares_czech import ARESCzechScraper

icos = ["00006947", "00216305", "06649114"]

with ARESCzechScraper() as scraper:
    for ico in icos:
        result = scraper.search_by_id(ico)
        if result:
            print(f"{ico}: {result['entity']['company_name_registry']}")
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run from `python/` directory |
| `No entity found` | ICO may not exist in registry |
| `is_mock: true` | API unavailable, using fallback data |
| Rate limit errors | Wait and retry (built-in rate limiting) |

---

## Running Individual Scrapers

### Python Commands

```bash
cd python

# ARES Czech - Search by ICO
python3 -c "from src.scrapers.ares_czech import ARESCzechScraper; \
    s = ARESCzechScraper(); \
    r = s.search_by_id('06649114'); \
    print(r['entity']['company_name_registry'])"

# ORSR Slovak - Search by ICO
python3 -c "from src.scrapers.orsr_slovak import ORSRSlovakScraper; \
    s = ORSRSlovakScraper(); \
    r = s.search_by_id('35763491'); \
    print(r.get('entity', {}).get('name'))"

# RPVS Slovak - Get UBO data
python3 -c "from src.scrapers.rpvs_slovak import RpvsSlovakScraper; \
    s = RpvsSlovakScraper(); \
    r = s.search_by_id('35763491'); \
    print(r.get('holders', []))"

# Run all new API tests
python3 test_new_apis.py

# Run specific scraper test
python3 test_new_apis.py --scraper rpvs

# Run with specific ICO
python3 test_new_apis.py --ico 35763491
```

### C# Commands

```bash
cd c_sharp

# Build all projects
dotnet build

# Run ARES test (shows unified output)
dotnet run --project TestAres.csproj

# Run AGROFERT demo
dotnet run --project AgrofertTest.csproj

# Run main scrapers program
dotnet run --project Scrapers.csproj
```

### Available Test Projects (C#)

| Project | Description |
|---------|-------------|
| `TestAres.csproj` | Tests ARES client with multiple companies |
| `AgrofertTest.csproj` | Demo showing AGROFERT unified output |
| `Scrapers.csproj` | Main scrapers test program |

---

## Next Steps

- Read full [README.md](README.md) for complete documentation
- See [API.md](API.md) for detailed API reference
- Check [CHANGELOG.md](CHANGELOG.md) for version history
