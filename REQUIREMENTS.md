# Requirements & Installation

This document describes the requirements for both Python and C# implementations of the SK/CZ Business Registry Scrapers.

---

## Table of Contents

1. [Python Requirements](#python-requirements)
2. [C# Requirements](#c-requirements)
3. [System Requirements](#system-requirements)
4. [Installation Guide](#installation-guide)
5. [Verification](#verification)

---

## Python Requirements

### Python Version

| Version | Status | Notes |
|---------|--------|-------|
| 3.10+ | ✅ Recommended | Fully tested |
| 3.9 | ✅ Supported | Should work |
| 3.8 | ✅ Supported | Minimum version |
| 3.7 and below | ❌ Not supported | Uses modern features |

### Python Dependencies

Install from `python/requirements.txt`:

```bash
cd python
pip install -r requirements.txt
```

#### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | ≥2.28.0 | HTTP client for API calls |
| `beautifulsoup4` | ≥4.12.0 | HTML parsing for web scrapers |
| `lxml` | ≥4.9.0 | XML/HTML parser backend |
| `python-dateutil` | ≥2.8.0 | Date parsing utilities |

#### Optional Dependencies

```bash
# For better JSON performance
pip install ujson

# For async support (future)
pip install httpx aiohttp

# Development tools
pip install pytest pytest-cov black flake8 mypy
```

### Virtual Environment Setup (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## C# Requirements

### .NET Version

| Version | Status | Notes |
|---------|--------|-------|
| .NET 10.0 | ✅ Latest | Recommended |
| .NET 8.0 | ✅ Supported | Stable LTS |
| .NET 7.0 | ✅ Supported | Still supported |
| .NET 6.0 | ✅ Supported | Minimum recommended |
| .NET Framework 4.x | ❌ Not supported | Use .NET Core/5+ |
| .NET Core 3.1 | ⚠️ Deprecated | Upgrade to .NET 8+ |

### C# Dependencies

All projects use SDK-style project files with minimal dependencies:

#### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `System.Text.Json` | 8.0.4 | JSON serialization |

#### Optional Dependencies

```xml
<!-- HTML parsing -->
<PackageReference Include="HtmlAgilityPack" Version="1.11.57" />

<!-- HTTP improvements -->
<PackageReference Include="Microsoft.Extensions.Http" Version="8.0.0" />

<!-- Dependency injection -->
<PackageReference Include="Microsoft.Extensions.DependencyInjection" Version="8.0.0" />

<!-- Logging -->
<PackageReference Include="Microsoft.Extensions.Logging" Version="8.0.0" />

<!-- Testing -->
<PackageReference Include="xunit" Version="2.6.2" />
<PackageReference Include="Moq" Version="4.20.70" />
```

### SDK Installation

**Linux (Ubuntu/Debian):**
```bash
# Install .NET SDK
wget https://dot.net/v1/dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh --channel 10.0

# Add to PATH
export DOTNET_ROOT=$HOME/.dotnet
export PATH=$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools
```

**macOS:**
```bash
# Using Homebrew
brew install dotnet-sdk

# Or using official installer
# Download from https://dotnet.microsoft.com/download
```

**Windows:**
```powershell
# Using winget
winget install Microsoft.DotNet.SDK.10

# Or download installer from
# https://dotnet.microsoft.com/download
```

---

## System Requirements

### Minimum System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 1 core | 2+ cores |
| RAM | 512 MB | 2 GB |
| Disk | 50 MB | 200 MB |
| Network | Internet connection | Stable connection |

### Operating Systems

**Python:**
- Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- macOS 11+ (Big Sur)
- Windows 10/11 with WSL or native Python

**C#:**
- Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+)
- macOS 11+ (Big Sur)
- Windows 10/11

---

## Installation Guide

### Python Installation

#### 1. Install Python

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# RHEL/CentOS/Fedora
sudo dnf install python3 python3-pip
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.11
```

**Windows:**
- Download from https://python.org/downloads/
- Check "Add Python to PATH" during installation

#### 2. Clone and Setup

```bash
# Clone repository
git clone <repository-url>
cd sk_cz_sources_sraper/python

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 -c "import requests; import bs4; print('OK')"
```

### C# Installation

#### 1. Install .NET SDK

Follow the instructions in [C# Requirements](#c-requirements) above.

#### 2. Clone and Build

```bash
# Clone repository
git clone <repository-url>
cd sk_cz_sources_sraper/c_sharp

# Restore dependencies
dotnet restore

# Build all projects
dotnet build

# Verify installation
dotnet run --project TestAres.csproj
```

---

## Verification

### Python Verification

```bash
cd python

# Run quick test
python3 -c "
from src.company_registry_api import get_api
api = get_api()
result = api.get_company_info('06649114')
print(f'Company: {result[\"entity\"][\"company_name_registry\"]}')
print('Python setup: OK')
"
```

Expected output:
```
Company: Prusa Research a.s.
Python setup: OK
```

### C# Verification

```bash
cd c_sharp

# Run quick test
dotnet run --project TestAres.csproj
```

Expected output includes:
```
✓ Found: Prusa Research a.s.
  Status: active
```

---

## Docker Setup (Optional)

### Python Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY python/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY python/src /app/src
COPY python/config /app/config

CMD ["python3", "-c", "from src.company_registry_api import get_api; print('Ready')"]
```

### C# Dockerfile

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY c_sharp/*.csproj .
RUN dotnet restore
COPY c_sharp/*.cs .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/runtime:10.0
WORKDIR /app
COPY --from=build /app .
ENTRYPOINT ["dotnet", "SkCzScrapers.dll"]
```

---

## Troubleshooting

### Python Issues

**Issue: `ModuleNotFoundError: No module named 'requests'`**
```bash
# Solution: Install dependencies
pip install -r requirements.txt
```

**Issue: `lxml` installation fails on Linux**
```bash
# Solution: Install system dependencies first
sudo apt install libxml2-dev libxslt-dev python3-dev
pip install -r requirements.txt
```

**Issue: Python version too old**
```bash
# Solution: Install Python 3.10+
python3 --version  # Should be 3.10 or higher
```

### C# Issues

**Issue: `dotnet: command not found`**
```bash
# Solution: Install .NET SDK
# See C# Requirements section above
```

**Issue: Build fails with framework version mismatch**
```bash
# Solution: Update target framework in .csproj
# Change <TargetFramework>net8.0</TargetFramework>
# To <TargetFramework>net10.0</TargetFramework>
```

**Issue: `System.Text.Json` version conflict**
```bash
# Solution: Clean and restore
dotnet clean
dotnet restore --no-cache
```

---

## Version Compatibility Matrix

| Component | Python 3.10 | Python 3.11 | Python 3.12 | .NET 8 | .NET 10 |
|-----------|-------------|-------------|-------------|--------|---------|
| ARES Czech | ✅ | ✅ | ✅ | ✅ | ✅ |
| ORSR Slovak | ✅ | ✅ | ✅ | ✅ | ✅ |
| RPVS Slovak | ✅ | ✅ | ✅ | ✅ | ✅ |
| ESM Czech | ✅ | ✅ | ✅ | ✅ | ✅ |
| Justice Czech | ✅ | ✅ | ✅ | ✅ | ✅ |
| RPO Slovak | ✅ | ✅ | ✅ | ✅ | ✅ |
| Finančná správa | ✅ | ✅ | ✅ | ✅ | ✅ |
| API Interface | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Next Steps

After installation:

1. **Read the Quick Start:** [QUICKSTART.md](QUICKSTART.md)
2. **API Integration Guide:** [API_USAGE.md](API_USAGE.md)
3. **Run Examples:**
   - Python: `python python/api_example.py`
   - C#: `dotnet run --project c_sharp/ApiExample.csproj`
4. **Check Documentation:** [README.md](README.md)

---

## Support

For issues with installation:

1. Check the [Troubleshooting](#troubleshooting) section
2. Verify your versions match requirements
3. Check existing issues in the repository
4. Create a new issue with:
   - Your OS and version
   - Python/.NET version (`python3 --version` or `dotnet --version`)
   - Error message and full output
