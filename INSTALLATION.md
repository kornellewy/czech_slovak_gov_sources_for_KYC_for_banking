# Installation and Setup Guide

## SK/CZ Business Registry Scrapers

This document provides complete installation instructions for both Python and C# implementations of the SK/CZ Business Registry Scrapers.

---

## Table of Contents

1. [Python Installation](#python-installation)
2. [C# Installation](#c-installation)
3. [Playwright Browser Setup](#playwright-browser-setup)
4. [Verification](#verification)
5. [Troubleshooting](#troubleshooting)

---

## Python Installation

### Requirements

- **Python:** 3.10 or higher (3.12 recommended)
- **Operating System:** Linux, macOS, or Windows

### Step 1: Install Python Dependencies

```bash
cd python
pip install -r requirements.txt
```

### Step 2: Install Playwright (Optional, for Dynamic Sites)

If you need to scrape dynamic websites like justice.cz with browser automation:

```bash
# Install Playwright Python package
pip install playwright>=1.40.0

# Install browser binaries
playwright install chromium
```

### Step 3: Verify Installation

```bash
# Test ARES scraper (works without Playwright)
python3 -c "from src.scrapers.ares_czech import ARESCzechScraper; s = ARESCzechScraper(); print(s.search_by_id('06649114'))"

# Test Justice scraper (uses static HTTP with proper headers)
python3 -c "from src.scrapers.justice_czech import JusticeCzechScraper; s = JusticeCzechScraper(); print(s.search_by_id('05984866'))"
```

---

## C# Installation

### Requirements

- **.NET:** .NET 8.0 SDK or higher
- **Operating System:** Linux, macOS, or Windows

### Step 1: Install .NET SDK

**Ubuntu/Debian:**
```bash
wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install -y dotnet-sdk-8.0
```

**macOS (using Homebrew):**
```bash
brew install dotnet-sdk
```

**Windows:**
Download from https://dotnet.microsoft.com/download

### Step 2: Restore NuGet Packages

```bash
cd c_sharp
dotnet restore
```

### Step 3: Build the Projects

```bash
dotnet build
```

### Step 4: Install Playwright (Optional, for Dynamic Sites)

If you need to use PlaywrightBrowserClient:

```bash
# Add Playwright package to your project
dotnet add package Microsoft.Playwright

# Install browser binaries
dotnet tool install --global Microsoft.Playwright.CLI
playwright install chromium
```

### Step 5: Verify Installation

```bash
# Run ARES test
dotnet run --project TestAres.csproj

# Run API example
dotnet run --project ApiExample.csproj

# Run Playwright test (if installed)
dotnet run --project TestPlaywright.csproj
```

---

## Playwright Browser Setup

Playwright is used for scraping dynamic websites that require JavaScript rendering or have anti-bot protection.

### Python Playwright Setup

```bash
# Install Playwright
pip install playwright

# Install Chromium browser
playwright install chromium

# Verify
python3 -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"
```

### C# Playwright Setup

```bash
# Install Playwright .NET package
dotnet add package Microsoft.Playwright

# Install browser CLI
dotnet tool install --global Microsoft.Playwright.CLI

# Install Chromium browser
playwright install chromium

# Verify
dotnet run --project TestPlaywright.csproj
```

### Playwright Configuration

Environment variables (optional):

```bash
# Run browser in headed mode (show window)
export PLAYWRIGHT_HEADLESS=false

# Increase timeout (milliseconds)
export PLAYWRIGHT_TIMEOUT=60000
```

---

## Complete Requirements File

### Python (requirements.txt)

```
# Core Dependencies
requests>=2.28.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
python-dateutil>=2.8.0

# Browser Automation (optional)
playwright>=1.40.0

# Development Dependencies (optional)
pytest>=7.0.0
pytest-cov>=4.0.0
```

### C# (.csproj files)

Required NuGet packages:

```xml
<ItemGroup>
  <PackageReference Include="System.Text.Json" Version="8.0.0" />
</ItemGroup>

<!-- For Playwright support (optional) -->
<ItemGroup>
  <PackageReference Include="Microsoft.Playwright" Version="1.40.0" />
</ItemGroup>
```

---

## Verification

### Python Verification

```bash
cd python

# Test all scrapers
python3 test_comprehensive.py

# Run tests with coverage
pytest --cov=src --cov-report=term

# Test specific scraper
python3 -c "from src.scrapers.justice_czech import JusticeCzechScraper; \
  scraper = JusticeCzechScraper(); \
  result = scraper.search_by_id('05984866'); \
  print(result['entity']['company_name_registry'] if result else 'Not found')"
```

### C# Verification

```bash
cd c_sharp

# Test ARES
dotnet run --project TestAres.csproj

# Test API
dotnet run --project ApiExample.csproj

# Test Playwright (if installed)
dotnet run --project TestPlaywright.csproj

# Build all projects
dotnet build
```

---

## Troubleshooting

### Python Issues

**Issue: ModuleNotFoundError: No module named 'playwright'**
```bash
pip install playwright
playwright install chromium
```

**Issue: Executable doesn't exist at /home/user/.cache/ms-playwright**
```bash
playwright install
# Or for specific browser
playwright install chromium
```

**Issue: Permission denied with pip**
```bash
# Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### C# Issues

**Issue: Browser not installed**
```bash
dotnet tool install --global Microsoft.Playwright.CLI
playwright install chromium
```

**Issue: Missing .NET SDK**
```bash
# Install .NET SDK 8.0
# See https://dotnet.microsoft.com/download for your platform
```

**Issue: Build errors**
```bash
dotnet clean
dotnet restore
dotnet build
```

### Justice.cz Specific Issues

**Issue: 404 Not Found from justice.cz**
- Ensure you're using the correct URL: `rejstrik-$firma` (with dollar sign)
- Verify proper browser headers are set (Accept: text/html, not application/json)

**Issue: Blocked by justice.cz**
- Verify User-Agent header is set to a browser string
- Check that Accept header is for HTML content
- Consider using Playwright for full browser automation

---

## Quick Start Examples

### Python Quick Start

```python
from src.company_registry_api import CompanyRegistryAPI

api = CompanyRegistryAPI()

# Get company info
result = api.get_company_info("05984866")
print(result['entity']['company_name_registry'])

# Get owners
owners = api.get_owners_summary("05984866")
print(owners)
```

### C# Quick Start

```csharp
using Justice;

var client = new JusticeClient();

// Search by ICO
var result = await client.SearchByICOAsync("05984866");
Console.WriteLine(result.Entity.CompanyName);

// Get as JSON
var json = result.ToJson();
Console.WriteLine(json);
```

---

## File Locations After Installation

```
project/
├── python/
│   ├── src/scrapers/
│   │   ├── base_playwright.py      # Playwright base class
│   │   ├── justice_czech.py         # Updated with proper headers
│   │   └── ...
│   ├── requirements.txt
│   └── snapshots/screenshots/       # Playwright screenshots
│
├── c_sharp/
│   ├── PlaywrightBrowserClient.cs   # Playwright browser automation
│   ├── JusticeClient.cs             # Updated with proper headers
│   ├── TestPlaywright.cs            # Playwright test program
│   └── ...
│
└── INSTALLATION.md                  # This file
```

---

## Additional Resources

- **Python Playwright Docs:** https://playwright.dev/python/
- **.NET Playwright Docs:** https://playwright.dev/dotnet/
- **Justice.cz:** https://or.justice.cz
- **ARES API:** https://ares.gov.cz

---

## Security Notes

1. **API Keys:** Never commit API keys to version control
2. **Rate Limiting:** Respect rate limits to avoid being blocked
3. **User Data:** Be careful with personal data from registries (GDPR compliance)
4. **Browser Automation:** Use headless mode for production; only use headed for debugging

---

## Support

For issues or questions:
- Check the troubleshooting section above
- Review test files for usage examples
- Check project MEMORY.md for implementation notes
