# SK/CZ Business Registry Scrapers

Unified scrapers for Slovak and Czech business registries with **identical output format** across both Python and C# implementations.

## Features

- **7 Registry Sources**: ARES, ORSR, RPO, RPVS, Justice.cz, ESM, Finančná správa
- **Unified Output**: Same JSON structure for both Python and C#
- **Type-Safe**: Dataclasses (Python) and classes (C#) for all data models
- **Rate Limiting**: Built-in rate limiting for all API clients
- **Mock Data**: Fallback mock data for unavailable APIs
- **UBO Support**: Ultimate Beneficial Owner data from RPVS and ESM
- **Reusable API**: Simple interface for integration into your applications

## Quick Integration

### Python
```python
from src.company_registry_api import get_api

api = get_api()
result = api.get_company_info("06649114")
print(result['entity']['company_name_registry'])
```

### C#
```csharp
using CompanyRegistry;

var service = new CompanyRegistryService();
var result = await service.GetCompanyInfoAsync("06649114", Country.CzechRepublic);
Console.WriteLine(result.Entity.CompanyNameRegistry);
```

📘 **See [API_USAGE.md](API_USAGE.md)** for complete integration guide.

## Quick Start

### Python
```bash
cd python
pip install -r requirements.txt
python -c "
from src.scrapers.ares_czech import ARESCzechScraper
with ARESCzechScraper() as scraper:
    result = scraper.search_by_id('00006947')
    print(result)
"
```

### C#
```bash
cd c_sharp
dotnet restore
dotnet run
```

---

## Installation

📘 **See [REQUIREMENTS.md](REQUIREMENTS.md)** for complete installation and system requirements.

### Quick Install

**Python:**
```bash
cd python
pip install -r requirements.txt
python3 api_example.py  # Test installation
```

**C#:**
```bash
cd c_sharp
dotnet restore
dotnet build
dotnet run --project ApiExample.csproj  # Test installation
```

### Requirements Summary

| Requirement | Python | C# |
|-------------|--------|-----|
| **Language** | Python 3.10+ | .NET 8.0+ |
| **Core Deps** | requests, beautifulsoup4, lxml | System.Text.Json |
| **OS** | Linux, macOS, Windows | Linux, macOS, Windows |

See [REQUIREMENTS.md](REQUIREMENTS.md) for detailed installation instructions.

---

## Unified Output Format

All scrapers return **identical JSON structure** in both Python and C#:

```json
{
  "entity": {
    "ico_registry": "00006947",
    "company_name_registry": "Ministerstvo financí",
    "legal_form": "Ministerstvo",
    "legal_form_code": "325",
    "status": "active",
    "status_effective_date": null,
    "incorporation_date": null,
    "registered_address": {
      "street": "Letenská",
      "city": "Praha",
      "postal_code": "11800",
      "country": "Česká republika",
      "country_code": "CZ",
      "full_address": "Letenská 525/15, 118 00 Praha"
    },
    "nace_codes": ["84.11"],
    "vat_id": "CZ00006947",
    "tax_id": "CZ00006947"
  },
  "holders": [
    {
      "holder_type": "individual",
      "role": "beneficial_owner",
      "name": "Ján Novák",
      "ico": null,
      "jurisdiction": null,
      "citizenship": "SK",
      "date_of_birth": "1970-05-15",
      "residency": "SK",
      "address": {
        "city": "Bratislava",
        "country": "Slovensko",
        "country_code": "SK"
      },
      "ownership_pct_direct": 100.0,
      "voting_rights_pct": 100.0,
      "record_effective_from": "2020-01-01",
      "record_effective_to": null
    }
  ],
  "tax_info": {
    "vat_id": "CZ00006947",
    "vat_status": "active",
    "tax_id": "CZ00006947",
    "tax_debts": {
      "has_debts": false,
      "amount_eur": 0.0,
      "details": null
    }
  },
  "metadata": {
    "source": "ARES_CZ",
    "register_name": "Register of Economic Subjects (ARES)",
    "register_url": "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/00006947",
    "retrieved_at": "2026-02-19T10:00:00.000000Z",
    "snapshot_reference": null,
    "parent_entity_ico": null,
    "level": 0,
    "is_mock": false
  }
}
```

---

## Field Reference

### Entity Fields

| Field | Type | Description |
|-------|------|-------------|
| `ico_registry` | string | Company identification number (IČO) |
| `company_name_registry` | string | Official company name |
| `legal_form` | string | Legal form description |
| `legal_form_code` | string | Legal form code |
| `status` | string | Entity status |
| `status_effective_date` | string | When current status started |
| `incorporation_date` | string | Date of registration (ISO format) |
| `registered_address` | object | Standardized address |
| `nace_codes` | array | List of NACE activity codes |
| `vat_id` | string | VAT identification number |
| `tax_id` | string | Tax identification number |

### Status Values

| Value | Czech | Slovak |
|-------|-------|--------|
| `active` | aktivní | aktívny |
| `cancelled` | zrušený | zrušený |
| `in_liquidation` | v likvidaci | v likvidácii |
| `bankruptcy` | konkurz | konkurz |
| `dissolved` | zaniklý | zaniknutý |
| `suspended` | pozastavený | pozastavený |

### Holder Fields

| Field | Type | Description |
|-------|------|-------------|
| `holder_type` | string | `individual`, `entity`, or `trust_fund` |
| `role` | string | Holder role |
| `name` | string | Holder name |
| `ico` | string | IČO (for entity holders) |
| `jurisdiction` | string | ISO 3166-1 alpha-2 (for entities) |
| `citizenship` | string | ISO 3166-1 alpha-2 (for individuals) |
| `date_of_birth` | string | Birth date (for individuals) |
| `residency` | string | ISO 3166-1 alpha-2 |
| `address` | object | Holder address |
| `ownership_pct_direct` | float | Direct ownership % (0-100) |
| `voting_rights_pct` | float | Voting rights % |
| `record_effective_from` | string | Record valid from |
| `record_effective_to` | string | Record valid to |

### Holder Roles

| Role | Description |
|------|-------------|
| `shareholder` | Shareholder / akcionár |
| `beneficial_owner` | UBO / skutočný majiteľ |
| `statutory_body` | Executive / štatutárny orgán |
| `procurist` | Prokurista |
| `liquidator` | Likvidátor |

### Tax Info Fields

| Field | Type | Description |
|-------|------|-------------|
| `vat_id` | string | VAT identification number |
| `vat_status` | string | `active` or `inactive` |
| `tax_id` | string | Tax identification number |
| `tax_debts.has_debts` | boolean | Has tax debts |
| `tax_debts.amount_eur` | float | Debt amount in EUR |
| `tax_debts.details` | string | Additional details |

### Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Source identifier (e.g., `ARES_CZ`) |
| `register_name` | string | Human-readable register name |
| `register_url` | string | Direct URL to entity |
| `retrieved_at` | string | ISO timestamp of retrieval |
| `snapshot_reference` | string | Snapshot file reference |
| `parent_entity_ico` | string | Parent IČO (for recursion) |
| `level` | integer | Depth in ownership chain |
| `is_mock` | boolean | True if mock/fallback data |

---

## Available Scrapers

### 1. ARES Czech

**Source:** `ARES_CZ` - Register of Economic Subjects

| Property | Value |
|----------|-------|
| API | REST API |
| Status | ✅ Working |
| Rate Limit | 500 req/min |
| Data | Company info, address, NACE, VAT status |

#### Python
```python
from src.scrapers.ares_czech import ARESCzechScraper

with ARESCzechScraper() as scraper:
    result = scraper.search_by_id("00006947")
    scraper.save_to_json(result, "company.json")
```

#### C#
```csharp
using Ares;
using UnifiedOutput;

using var client = new AresClient();
UnifiedOutput? result = await client.SearchByICOAsync("00006947");
Console.WriteLine(result?.ToJson());
```

**Test IČOs:** `00006947`, `00216305`, `06649114`

---

### 2. ORSR Slovak

**Source:** `ORSR_SK` - Business Register (Obchodný register SR)

| Property | Value |
|----------|-------|
| API | Web scraping |
| Status | ✅ Working |
| Rate Limit | 60 req/min |
| Data | Company info, court registration, address |

#### Python
```python
from src.scrapers.orsr_slovak import ORSRSlovakScraper

with ORSRSlovakScraper() as scraper:
    result = scraper.search_by_id("35763491")
    results = scraper.search_by_name("Slovenská sporiteľňa")
```

#### C#
```csharp
using Orsr;
using UnifiedOutput;

using var client = new OrsrClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");
List<UnifiedOutput> results = await client.SearchByNameAsync("Slovenská sporiteľňa");
```

**Test ICOs:** `35763491`, `44103755`, `31328356`

---

### 3. RPO Slovak

**Source:** `RPO_SK` - Register of Legal Entities

| Property | Value |
|----------|-------|
| API | REST API (discovery needed) |
| Status | ⚠️ Mock fallback |
| Rate Limit | 100 req/min |
| Data | Company info, legal form, status |

#### Python
```python
from src.scrapers.rpo_slovak import RpoSlovakScraper

with RpoSlovakScraper() as scraper:
    result = scraper.search_by_id("35763491")
```

#### C#
```csharp
using Rpo;
using UnifiedOutput;

using var client = new RpoClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");
```

---

### 4. RPVS Slovak (UBO)

**Source:** `RPVS_SK` - Register of Public Sector Partners

| Property | Value |
|----------|-------|
| API | REST API |
| Status | ⚠️ May require API key |
| Rate Limit | 30 req/min |
| Data | UBO information, ownership %, voting rights |

#### Python
```python
from src.scrapers.rpvs_slovak import RpvsSlovakScraper

# Without API key (mock data)
with RpvsSlovakScraper() as scraper:
    result = scraper.search_by_id("35763491")

# With API key
with RpvsSlovakScraper(api_key="your-key") as scraper:
    result = scraper.search_by_id("35763491")
```

#### C#
```csharp
using Rpvs;
using UnifiedOutput;

using var client = new RpvsClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");
```

**Holder types detected:** `individual`, `entity`

---

### 5. Justice Czech

**Source:** `JUSTICE_CZ` - Commercial Register (Obchodní rejstřík)

| Property | Value |
|----------|-------|
| API | No public API |
| Status | ⚠️ Mock only |
| Data | Court info, shareholders, board members, filings |

#### Python
```python
from src.scrapers.justice_czech import JusticeCzechScraper

with JusticeCzechScraper() as scraper:
    result = scraper.search_by_id("06649114")
```

#### C#
```csharp
using Justice;
using UnifiedOutput;

using var client = new JusticeClient();
UnifiedOutput? result = await client.SearchByICOAsync("06649114");
```

**Test IČOs:** `06649114`, `00216305`

---

### 6. ESM Czech (UBO)

**Source:** `ESM_CZ` - Register of Beneficial Owners

| Property | Value |
|----------|-------|
| API | RESTRICTED |
| Status | 🔒 Requires AML certification |
| Data | UBO information |

**Access Requirements:**
- AML obligated person (bank, notary, auditor, etc.)
- Registration at https://issm.justice.cz
- API key required

#### Python
```python
from src.scrapers.esm_czech import EsmCzechScraper

# Check requirements
with EsmCzechScraper() as scraper:
    print(scraper.get_access_requirements())
    result = scraper.search_by_id("06649114")  # Mock data

# With API key
with EsmCzechScraper(api_key="your-key") as scraper:
    result = scraper.search_by_id("06649114")
```

#### C#
```csharp
using Esm;
using UnifiedOutput;

// Check requirements
var req = EsmClient.AccessRequirements;
Console.WriteLine(req.Website);

using var client = new EsmClient();
UnifiedOutput? result = await client.SearchByICOAsync("06649114");
```

---

### 7. Finančná správa Slovak

**Source:** `FINANCNA_SK` - Financial Administration

| Property | Value |
|----------|-------|
| API | REST API (discovery needed) |
| Status | ⚠️ Mock fallback |
| Data | VAT status, tax debts |

#### Python
```python
from src.scrapers.financna_sprava_slovak import FinancnaSpravaScraper

with FinancnaSpravaScraper() as scraper:
    result = scraper.search_by_id("35763491")
    tax_info = result.get("tax_info", {})
    print(f"VAT: {tax_info.get('vat_status')}")
    print(f"Debts: {tax_info.get('tax_debts', {}).get('has_debts')}")
```

#### C#
```csharp
using FinancnaSprava;
using UnifiedOutput;

using var client = new FinancnaSpravaClient();
UnifiedOutput? result = await client.SearchByICOAsync("35763491");
Console.WriteLine(result?.TaxInfo?.VatStatus);
```

**Test ICOs:** `35763491`, `44103755`, `36246621`

---

## Usage Examples

### Combining Multiple Sources

#### Python
```python
from src.scrapers.ares_czech import ARESCzechScraper
from src.scrapers.justice_czech import JusticeCzechScraper

ico = "06649114"

# Get basic info from ARES
with ARESCzechScraper() as ares:
    ares_data = ares.search_by_id(ico)

# Get shareholder info from Justice
with JusticeCzechScraper() as justice:
    justice_data = justice.search_by_id(ico)

# Combine
combined = {
    "basic_info": ares_data.get("entity"),
    "tax_info": ares_data.get("tax_info"),
    "shareholders": [
        h for h in justice_data.get("holders", [])
        if h.get("role") == "shareholder"
    ]
}
```

### Batch Processing

#### Python
```python
from src.scrapers.ares_czech import ARESCzechScraper
import json

icos = ["00006947", "00216305", "06649114"]

with ARESCzechScraper() as scraper:
    results = []
    for ico in icos:
        result = scraper.search_by_id(ico)
        if result:
            results.append(result)

    with open("companies.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
```

#### C#
```csharp
using Ares;
using UnifiedOutput;

var icos = new[] { "00006947", "00216305", "06649114" };
var results = new List<string>();

using var client = new AresClient();
foreach (var ico in icos)
{
    var result = await client.SearchByICOAsync(ico);
    if (result != null)
        results.Add(result.ToJson());
}

File.WriteAllText("companies.json", $"[{string.Join(",", results)}]");
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RPVS_API_KEY` | API key for RPVS Slovak | None |
| `ESM_API_KEY` | API key for ESM Czech | None |
| `LOG_LEVEL` | Logging level | INFO |

---

## API Status Summary

| Source | Country | Status | Notes |
|--------|---------|--------|-------|
| ARES | CZ | ✅ Working | Official REST API |
| ORSR | SK | ✅ Working | Web scraper |
| RPO | SK | ⚠️ Mock | API format TBD |
| RPVS | SK | ⚠️ Mock | May require API key |
| Justice | CZ | ⚠️ Mock | No public API |
| ESM | CZ | 🔒 Restricted | AML certification required |
| Finančná správa | SK | ⚠️ Mock | API format TBD |

---

## Project Structure

```
sk_cz_sources_sraper/
├── README.md
│
├── python/
│   ├── requirements.txt
│   ├── src/
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Abstract base class
│   │   │   ├── ares_czech.py           # ARES Czech
│   │   │   ├── orsr_slovak.py          # ORSR Slovak
│   │   │   ├── rpo_slovak.py           # RPO Slovak
│   │   │   ├── rpvs_slovak.py          # RPVS Slovak (UBO)
│   │   │   ├── justice_czech.py        # Justice Czech
│   │   │   ├── esm_czech.py            # ESM Czech (UBO)
│   │   │   ├── financna_sprava_slovak.py
│   │   │   └── stats_slovak.py         # Stats Slovak
│   │   └── utils/
│   │       ├── output_normalizer.py    # Unified output format
│   │       ├── http_client.py          # Rate-limited HTTP client
│   │       ├── json_handler.py         # JSON file operations
│   │       ├── logger.py               # Logging utilities
│   │       └── field_mapper.py         # Field mapping utilities
│   └── config/
│       └── constants.py                # API URLs, rate limits
│
└── c_sharp/
    ├── SkCzScrapers.csproj
    ├── OutputNormalizer.cs             # Unified output format
    ├── SharedHttpClient.cs             # Shared HTTP client
    ├── AresClient.cs
    ├── OrsrClient.cs
    ├── RpoClient.cs
    ├── RpvsClient.cs
    ├── JusticeClient.cs
    ├── EsmClient.cs
    ├── FinancnaSpravaClient.cs
    ├── StatsClient.cs
    └── RecursiveClient.cs
```

---

## Test ICOs

### Slovak Entities
| ICO | Name | Notes |
|-----|------|-------|
| `35763491` | Slovenská sporiteľňa, a.s. | Majority owned by Erste Group |
| `31328356` | Všeobecná úverová banka, a.s. | Owned by Intesa Sanpaolo |
| `44103755` | Slovak Telekom, a.s. | Owned by Deutsche Telekom |
| `36246621` | Doprastav, a.s. | Construction company |

### Czech Entities
| ICO | Name | Notes |
|-----|------|-------|
| `00006947` | Ministerstvo financí | Ministry of Finance |
| `00216305` | Česká pošta, s.p. | Czech Post |
| `00554204` | Hlavní město Praha | City of Prague |
| `06649114` | Prusa Research a.s. | 3D printer manufacturer |

---

## Running Scrapers

### Python Scrapers

#### Installation
```bash
cd python
pip install -r requirements.txt
```

#### Basic Usage - ARES Czech
```bash
cd python
python3 -c "
from src.scrapers.ares_czech import ARESCzechScraper
with ARESCzechScraper() as scraper:
    result = scraper.search_by_id('06649114')
    print(result)
"
```

#### Using Individual Scrapers
```bash
# ARES Czech (Register of Economic Subjects)
python3 -c "
from src.scrapers.ares_czech import ARESCzechScraper
with ARESCzechScraper() as s:
    result = s.search_by_id('06649114')
    s.save_to_json(result, 'company.json')
"

# ORSR Slovak (Business Register)
python3 -c "
from src.scrapers.orsr_slovak import ORSRSlovakScraper
with ORSRSlovakScraper() as s:
    result = s.search_by_id('35763491')
    print(result)
"

# RPVS Slovak (UBO data)
python3 -c "
from src.scrapers.rpvs_slovak import RpvsSlovakScraper
with RpvsSlovakScraper() as s:
    result = s.search_by_id('35763491')
    print(result.get('holders'))
"

# ESM Czech (Beneficial Owners - placeholder)
python3 -c "
from src.scrapers.esm_czech import EsmCzechScraper
with EsmCzechScraper() as s:
    result = s.search_by_id('06649114')
    print(result)
"
```

#### Running Test Scripts
```bash
cd python

# Test all new scrapers (RPO, RPVS, Finančná, ESM)
python3 test_new_apis.py

# Test specific scraper
python3 test_new_apis.py --scraper rpvs

# Test with specific ICO
python3 test_new_apis.py --ico 35763491

# Test unified output format
python3 test_unified_output.py

# Test comprehensive (unit tests)
python3 test_comprehensive.py

# Test specific company (AGROFERT demo)
python3 test_agrofert_demo.py
```

### C# Scrapers

#### Installation
```bash
cd c_sharp
dotnet restore
dotnet build
```

#### Basic Usage - ARES Client
```bash
cd c_sharp
dotnet run --project Scrapers.csproj
```

#### Using Individual Clients
```csharp
// ARES Czech
using var client = new Ares.AresClient();
var result = await client.SearchByICOAsync("06649114");
Console.WriteLine(result.ToJson());

// ORSR Slovak
using var client = new Orsr.OrsrClient();
var result = await client.SearchByICOAsync("35763491");

// RPVS Slovak (UBO)
using var client = new Rpvs.RpvsClient();
var result = await client.SearchByICOAsync("35763491");
```

#### Running Test Projects
```bash
cd c_sharp

# Build all
dotnet build

# Run ARES test (with unified output demo)
dotnet run --project TestAres.csproj

# Run AGROFERT demo
dotnet run --project AgrofertTest.csproj

# Run main scrapers test
dotnet run --project Scrapers.csproj
```

#### Compile and Run Manually
```bash
cd c_sharp

# Build specific project
dotnet build TestAres.csproj

# Run the built executable
dotnet bin/Debug/net10.0/TestAres.dll
```

---

## License

MIT License

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure unified output format is maintained
4. Submit a pull request
