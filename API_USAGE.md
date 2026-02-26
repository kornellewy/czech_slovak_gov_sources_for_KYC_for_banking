# API Integration Guide

This guide shows how to integrate the SK/CZ Business Registry Scrapers into your own applications.

**Prerequisites:** See [REQUIREMENTS.md](REQUIREMENTS.md) for installation requirements.

---

## Table of Contents

1. [Python Integration](#python-integration)
2. [C# Integration](#c-integration)
3. [Usage Examples](#usage-examples)
4. [API Reference](#api-reference)
5. [Error Handling](#error-handling)
6. [Testing & Mocking](#testing--mocking)

---

## Python Integration

### Installation

Add the scrapers to your project or install as a module:

```bash
# Copy the scrapers directory to your project
cp -r sk_cz_sources_sraper/python/src your_project/

# Or add to PYTHONPATH
export PYTHONPATH="/path/to/sk_cz_sources_sraper/python/src:$PYTHONPATH"
```

### Basic Usage

```python
from src.company_registry_api import CompanyRegistryAPI, Country

# Initialize the API
api = CompanyRegistryAPI(default_country=Country.CZECH_REPUBLIC)

# Get company information
info = api.get_company_info("06649114")
if info:
    print(f"Company: {info['entity']['company_name_registry']}")
    print(f"Status: {info['entity']['status']}")
```

### Quick Start Examples

#### 1. Get Company Info

```python
from src.company_registry_api import get_api

api = get_api()

# Czech company
result = api.get_company_info("06649114")  # Prusa Research
print(result['entity']['company_name_registry'])

# Slovak company
result = api.get_company_info("35763491", Country.SLOVAKIA)
print(result['entity']['company_name_registry'])
```

#### 2. Get Owners (UBO)

```python
api = get_api()

owners = api.get_owners_summary("35763491", Country.SLOVAKIA)

print(f"Company: {owners['company_name']}")
print(f"Total Owners: {owners['total_owners']}")
print(f"Concentrated: {owners['ownership_concentrated']}")

for owner in owners['owners']:
    print(f"  {owner['name']}: {owner['ownership_pct']}%")
```

#### 3. Verify VAT Number

```python
api = get_api()

verification = api.verify_vat_number("CZ06649114")

if verification['valid']:
    print(f"Active: {verification['active']}")
    print(f"Company: {verification['company_name']}")
else:
    print("Invalid VAT number")
```

#### 4. Get Full Info

```python
api = get_api()

full_info = api.get_full_info("06649114")

# Access all sections
entity = full_info['entity']
holders = full_info['holders']
tax_info = full_info['tax_info']
metadata = full_info['metadata']

print(f"{entity['company_name_registry']}")
print(f"VAT: {tax_info['vat_status']}")
print(f"Owners: {len(holders)}")
```

---

## C# Integration

### Installation

Add the C# files to your project:

```bash
# Copy source files
cp sk_cz_sources_sraper/c_sharp/*.cs your_project/Models/
cp sk_cz_sources_sraper/c_sharp/ICompanyRegistryService.cs your_project/Services/
cp sk_cz_sources_sraper/c_sharp/CompanyRegistryService.cs your_project/Services/

# Add namespace reference to your .csproj
# <ItemGroup>
#   <Compile Include="Services\*.cs" />
#   <Compile Include="Models\*.cs" />
# </ItemGroup>
```

### Basic Usage

```csharp
using CompanyRegistry;
using UnifiedOutput;

// Initialize the service
var service = new CompanyRegistryService();

// Get company information
var info = await service.GetCompanyInfoAsync("06649114", Country.CzechRepublic);
if (info != null)
{
    Console.WriteLine(info.Entity.CompanyNameRegistry);
    Console.WriteLine(info.Entity.Status);
}
```

### Dependency Injection

```csharp
// In your Startup.cs or Program.cs
builder.Services.AddSingleton<ICompanyRegistryService>(sp =>
    new CompanyRegistryService(Country.CzechRepublic));

// In your controller/service
public class CompanyService
{
    private readonly ICompanyRegistryService _registry;

    public CompanyService(ICompanyRegistryService registry)
    {
        _registry = registry;
    }

    public async Task<CompanyDetails> GetCompanyAsync(string ico)
    {
        var data = await _registry.GetCompanyInfoAsync(ico, Country.CzechRepublic);
        return MapToCompanyDetails(data);
    }
}
```

---

## Usage Examples

### Web Application (Python Flask)

```python
from flask import Flask, jsonify
from src.company_registry_api import get_api, Country

app = Flask(__name__)
api = get_api()

@app.route('/api/company/<ico>')
def get_company(ico):
    result = api.get_company_info(ico)

    if result is None:
        return jsonify({'error': 'Company not found'}), 404

    return jsonify({
        'name': result['entity']['company_name_registry'],
        'status': result['entity']['status'],
        'address': result['entity']['registered_address'],
        'vat_status': result['tax_info']['vat_status']
    })

@app.route('/api/company/<ico>/owners')
def get_owners(ico):
    summary = api.get_owners_summary(ico)

    if summary is None:
        return jsonify({'error': 'Company not found'}), 404

    return jsonify({
        'company': summary['company_name'],
        'total_owners': summary['total_owners'],
        'owners': summary['owners']
    })
```

### ASP.NET Core Web API (C#)

```csharp
[ApiController]
[Route("api/[controller]")]
public class CompanyController : ControllerBase
{
    private readonly ICompanyRegistryService _registry;

    public CompanyController(ICompanyRegistryService registry)
    {
        _registry = registry;
    }

    [HttpGet("{ico}")]
    public async Task<IActionResult> GetCompany(string ico)
    {
        var result = await _registry.GetCompanyInfoAsync(ico, Country.CzechRepublic);

        if (result == null)
            return NotFound(new { error = "Company not found" });

        return Ok(new
        {
            name = result.Entity.CompanyNameRegistry,
            status = result.Entity.Status,
            address = result.Entity.RegisteredAddress,
            vatStatus = result.TaxInfo?.VatStatus
        });
    }

    [HttpGet("{ico}/owners")]
    public async Task<IActionResult> GetOwners(string ico)
    {
        var summary = await _registry.GetOwnersSummaryAsync(ico, Country.CzechRepublic);

        if (summary == null)
            return NotFound(new { error = "Company not found" });

        return Ok(new
        {
            company = summary.CompanyName,
            totalOwners = summary.TotalOwners,
            owners = summary.Owners
        });
    }
}
```

### Batch Processing (Python)

```python
from src.company_registry_api import CompanyRegistryAPI, Country
import csv

api = CompanyRegistryAPI()

# Process a CSV file of companies
with open('companies.csv', 'r') as f:
    reader = csv.DictReader(f)
    results = []

    for row in reader:
        ico = row['ico']
        info = api.get_full_info(ico)

        if info:
            results.append({
                'ico': ico,
                'name': info['entity']['company_name_registry'],
                'status': info['entity']['status'],
                'owners': len(info['holders'])
            })

# Save results
with open('results.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=['ico', 'name', 'status', 'owners'])
    writer.writeheader()
    writer.writerows(results)
```

---

## API Reference

### Python: CompanyRegistryAPI

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_company_info()` | `ico`, `country` | `dict` or `None` | Basic company information |
| `get_ubo_info()` | `ico`, `country` | `dict` or `None` | Beneficial owners |
| `get_tax_info()` | `ico`, `country` | `dict` or `None` | VAT/tax information |
| `get_full_info()` | `ico`, `country` | `dict` or `None` | Combined from all sources |
| `search_by_name()` | `name`, `country`, `limit` | `list` | Search companies by name |
| `verify_vat_number()` | `vat_id`, `country` | `dict` | VAT validation |
| `get_owners_summary()` | `ico`, `country`, `min_ownership` | `dict` or `None` | Ownership summary |

### C#: ICompanyRegistryService

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `GetCompanyInfoAsync()` | `ico`, `country` | `Task<UnifiedData?>` | Basic company information |
| `GetUboInfoAsync()` | `ico`, `country` | `Task<UnifiedData?>` | Beneficial owners |
| `GetTaxInfoAsync()` | `ico`, `country` | `Task<UnifiedData?>` | VAT/tax information |
| `GetFullInfoAsync()` | `ico`, `country` | `Task<UnifiedData?>` | Combined from all sources |
| `SearchByNameAsync()` | `name`, `country`, `limit` | `Task<List<UnifiedData>>` | Search by name |
| `VerifyVatNumberAsync()` | `vat_id`, `country` | `Task<VatVerificationResult>` | VAT validation |
| `GetOwnersSummaryAsync()` | `ico`, `country`, `min_ownership` | `Task<OwnershipSummary?>` | Ownership summary |

---

## Error Handling

### Python

```python
from src.company_registry_api import CompanyRegistryAPI

api = CompanyRegistryAPI()

# Always check for None
result = api.get_company_info("00000000")  # Invalid ICO

if result is None:
    print("Company not found")
else:
    # Check if data is mock
    if result['metadata']['is_mock']:
        print("Warning: Using mock/fallback data")

    # Use the data
    print(result['entity']['company_name_registry'])
```

### C#

```csharp
using CompanyRegistry;

var service = new CompanyRegistryService();

// Always check for null
var result = await service.GetCompanyInfoAsync("00000000");

if (result == null)
{
    Console.WriteLine("Company not found");
}
else
{
    // Check if data is mock
    if (result.Metadata.IsMock)
    {
        Console.WriteLine("Warning: Using mock/fallback data");
    }

    // Use the data
    Console.WriteLine(result.Entity.CompanyNameRegistry);
}
```

---

## Testing & Mocking

### Python: Create Mock API

```python
from unittest.mock import Mock
from src.company_registry_api import CompanyRegistryAPI

def test_company_lookup():
    # Create mock API
    api = CompanyRegistryAPI()

    # Mock the internal scraper
    api._query_by_source = Mock(return_value={
        'entity': {
            'ico_registry': '12345678',
            'company_name_registry': 'Test Company'
        },
        'holders': [],
        'metadata': {'is_mock': False}
    })

    result = api.get_company_info("12345678")

    assert result['entity']['company_name_registry'] == 'Test Company'
```

### C#: Create Mock Service

```csharp
using Moq;

public class MockCompanyRegistryService : ICompanyRegistryService
{
    public Task<UnifiedData?> GetCompanyInfoAsync(string ico, Country country)
    {
        return Task.FromResult<UnifiedData?>(new UnifiedData
        {
            Entity = new UnifiedEntity
            {
                IcoRegistry = ico,
                CompanyNameRegistry = "Test Company"
            }
        });
    }

    // Implement other methods...
}

// Use in tests
var mockService = new MockCompanyRegistryService();
var result = await mockService.GetCompanyInfoAsync("12345678", Country.CzechRepublic);
```

---

## Response Format

Both Python and C# return the same unified structure:

```json
{
  "entity": {
    "ico_registry": "string",
    "company_name_registry": "string",
    "legal_form": "string",
    "status": "string",
    "registered_address": { ... },
    "vat_id": "string"
  },
  "holders": [
    {
      "name": "string",
      "holder_type": "individual|entity",
      "role": "shareholder|beneficial_owner|...",
      "ownership_pct_direct": 0-100,
      "voting_rights_pct": 0-100
    }
  ],
  "tax_info": {
    "vat_id": "string",
    "vat_status": "active|inactive",
    "tax_debts": { ... }
  },
  "metadata": {
    "source": "ARES_CZ|ORSR_SK|...",
    "is_mock": false,
    "retrieved_at": "2026-02-19T..."
  }
}
```

---

## Advanced Features

### ARES Sub-Source Extraction

The ARES Czech scraper can extract data from multiple sub-registries embedded in the main ARES response. This includes data from:

| Sub-source | Registry | Description |
|------------|----------|-------------|
| **RZP** | Commercial Register | Justice.cz (Obchodní rejstřík) |
| **ROS** | RES | Resident Income Tax |
| **VR** | Vermont | Separated Real Estate |
| **RES** | RES | Resident Income Tax |
| **DPH** | DPH | VAT Register |
| **RPSH** | RPSH | Statistical Register |
| **SD** | SD | Tax Debts Register |
| **IR** | IR | Income Tax Register |

#### Python Usage

```python
from src.scrapers.ares_czech import ARESCzechScraper

scraper = ARESCzechScraper()

# Basic search (without sub-sources)
result = scraper.search_by_id('05984866')

# Search with sub-source information
result = scraper.search_by_id('05984866', include_subsource=True)

if result and 'subsource' in result:
    subsource = result['subsource']

    # Check which registries have data
    print(f"Active sub-sources: {subsource['active_count']}")

    for code, info in subsource['registrations'].items():
        if info['is_active']:
            print(f"  ✅ {code}: {info['status']}")

    # Access additional data from sub-sources
    for source, data in subsource['additional_data'].items():
        print(f"{source}: {data}")
```

#### C# Usage

```csharp
using Ares;
using UnifiedOutput;

var client = new AresClient();

// Basic search (without sub-sources)
var result = await client.SearchByICOAsync("05984866");

// Search with sub-source information
var result = await client.SearchByICOAsync("05984866", includeSubsource: true);

if (result?.Subsource is AresSubsource subsource)
{
    // Check which registries have data
    Console.WriteLine($"Active sub-sources: {subsource.ActiveCount}");

    foreach (var reg in subsource.Registrations)
    {
        if (reg.Value.IsActive)
        {
            Console.WriteLine($"  ✅ {reg.Key}: {reg.Value.Status}");
        }
    }

    // Access additional data from sub-sources
    foreach (var data in subsource.AdditionalData)
    {
        Console.WriteLine($"{data.Key}: {data.Value.CompanyName}");
    }
}
```

#### Sub-Source Response Structure

```json
{
  "subsource": {
    "registrations": {
      "RZP": {"status": "NEEXISTUJICI", "is_active": false, "name": "Rejstřík osob"},
      "Ros": {"status": "AKTIVNI", "is_active": true, "name": "RES"},
      "Vr": {"status": "AKTIVNI", "is_active": true, "name": "Vermont Register"},
      "Dph": {"status": "AKTIVNI", "is_active": true, "name": "DPH"}
    },
    "additional_data": {
      "VR": {
        "company_name": "DEVROCK a.s.",
        "address": {"street": "...", "city": "..."},
        "legal_form": "121",
        "file_reference": "B 22379/MSPH"
      }
    },
    "active_count": 3,
    "ros_legal_form": "121"
  }
}
```

#### Use Cases

1. **Check if company is in Commercial Register (RZP)** before querying justice.cz
2. **Get Vermont Register file references** for real estate records
3. **Verify VAT status** from DPH registry
4. **Identify all active registries** for a company

---

## Best Practices

1. **Always check for null/None** - Companies may not exist in the registry
2. **Check `is_mock` flag** - Indicates if data is from a fallback source
3. **Use `include_subsource=True`** for ARES to get complete registry status
4. **Handle rate limits** - Built-in rate limiting prevents blocking
5. **Cache results** - Company data doesn't change frequently
6. **Use appropriate country** - CZ and SK have different registries
7. **Check RZP status before querying justice.cz** - Not all companies are in Commercial Register

---

## Support

- Python: See `python/examples.py` for more examples
- C#: See `c_sharp/TestAres.cs` for usage examples
- Full API: See `API.md` for detailed reference
