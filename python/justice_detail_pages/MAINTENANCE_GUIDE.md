# API Maintenance Windows - Documentation

## Overview

Several Czech and Slovak government registries have periodic maintenance windows. This document describes the maintenance schedules and how the scrapers handle them.

---

## Czech Republic (CZ)

### Justice.cz (Obchodní rejstřík / Commercial Register)

**Maintenance Schedule:**
- **Typical:** Sunday nights 02:00-06:00 CET
- **Variation:** Can occur at any time with advance notice
- **Duration:** Usually 2-4 hours

**Detection:**
The scraper detects maintenance by checking for:
- Czech text: "Momentálně probíhá údržba" (Maintenance is in progress)
- "Právě probíhá údržba systému" (System maintenance is in progress)
- Maintenance page background image

**Maintenance Response Format:**
```json
{
  "entity": {
    "ico_registry": null,
    "company_name_registry": null,
    "status": "maintenance"
  },
  "holders": [],
  "tax_info": {
    "vat_id": null,
    "vat_status": null
  },
  "metadata": {
    "source": "JUSTICE_CZ",
    "register_name": "Commercial Register (Obchodní rejstřík)",
    "register_url": "https://or.justice.cz",
    "retrieved_at": "2026-02-21T10:00:00+01:00",
    "is_mock": false,
    "maintenance": true,
    "maintenance_message": "Justice.cz is under maintenance (Momentálně probíhá údržba)",
    "note": "Please try again later. Typical maintenance: Sunday nights 02:00-06:00 CET"
  }
}
```

**How to Check if Result is Maintenance:**
```python
from src.scrapers.justice_czech import JusticeCzechScraper

scraper = JusticeCzechScraper()
result = scraper.search_by_id('05984866')

# Check for maintenance
if result and result.get('metadata', {}).get('maintenance'):
    print("Justice.cz is under maintenance")
    print(f"Message: {result['metadata']['maintenance_message']}")
```

### ESM (Evidence skutečných majitelů / UBO Register)

**Status:** 🔒 RESTRICTED - Requires AML certification

**Maintenance Schedule:**
- Follows Justice.cz schedule (same infrastructure)
- Sunday nights 02:00-06:00 CET when accessible

**Access Requirements:**
- AML certification from Czech Ministry of Finance
- Registration at https://issm.justice.cz/
- API key for authenticated access

**Contact:**
- Email: ufo@mfcr.cz
- Website: https://issm.justice.cz/

### ARES (Register of Economic Subjects)

**Maintenance Schedule:**
- **Typical:** Sundays 02:00-06:00 CET (occasional)
- **Status:** Generally available 24/7
- **Downtime:** Rare

---

## Slovakia (SK)

### RPVS (Register of Public Sector Partners)

**Maintenance Schedule:**
- No fixed schedule reported
- Generally available 24/7

### ORSR (Business Register)

**Maintenance Schedule:**
- No fixed schedule reported
- Generally available 24/7

---

## Handling Maintenance in Your Code

### Python

```python
from src.scrapers.justice_czech import JusticeCzechScraper

scraper = JusticeCzechScraper()
result = scraper.search_by_id('05984866')

# Option 1: Check maintenance flag
if result and result.get('metadata', {}).get('maintenance'):
    # Handle maintenance
    print("Site under maintenance, retry later")
    return None

# Option 2: Check status field
if result and result['entity'].get('status') == 'maintenance':
    # Handle maintenance
    print("Site under maintenance, retry later")
    return None

# Option 3: Use ARES as fallback
if not result or result.get('metadata', {}).get('maintenance'):
    from src.scrapers.ares_czech import ARESCzechScraper
    ares = ARESCzechScraper()
    result = ares.search_by_id('05984866')
```

### C#

```csharp
using Justice;

var client = new JusticeClient();
var result = await client.SearchByICOAsync("05984866");

// Check for maintenance
if (result?.Entity?.Status == "maintenance")
{
    Console.WriteLine("Justice.cz is under maintenance");
    // Retry later or use alternative source
}

// Or use ARES as fallback
if (result == null || result.Entity.Status == "maintenance")
{
    var aresClient = new Ares.AresClient();
    result = await aresClient.SearchByICOAsync("05984866");
}
```

---

## Testing for Maintenance

### Command Line Check

```bash
# Check if justice.cz is in maintenance
curl -s "https://or.justice.cz/ias/ui/rejstrik-firma?ico=05984866" | grep -i "momentálně"

# If empty = site is working
# If contains "momentálně" = maintenance
```

### Python Check

```python
import requests

def check_justice_maintenance():
    response = requests.get("https://or.justice.cz/ias/ui/rejstrik-firma?ico=05984866")

    if "Momentálně probíhá údržba" in response.text:
        return True
    if "Právě probíhá údržba" in response.text:
        return True
    return False

if check_justice_maintenance():
    print("Justice.cz is under maintenance")
```

---

## Recommendations

1. **Always check the `maintenance` flag** in metadata before using results
2. **Have fallback sources ready** (ARES for Czech entities)
3. **Implement retry logic** with exponential backoff for maintenance responses
4. **Monitor status** before critical batch operations
5. **Schedule around maintenance windows** if possible (avoid Sunday mornings CET)

---

## Related Files

- `python/config/constants.py` - Maintenance indicators and URLs
- `python/src/scrapers/justice_czech.py` - Maintenance detection logic
- `c_sharp/JusticeClient.cs` - C# maintenance detection

---

## Last Updated

2026-02-21 - Detected ongoing maintenance at Justice.cz
