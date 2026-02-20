"""Central configuration for all scrapers."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"

# ARES Czech Configuration
ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"
ARES_RATE_LIMIT = 500  # requests per minute

# Justice Czech (Commercial Register / Obchodní rejstřík) Configuration
# URL pattern: https://or.justice.cz/ias/ui/rejstrik-$firma?ico={ICO}
JUSTICE_BASE_URL = "https://or.justice.cz"
JUSTICE_SEARCH_URL = f"{JUSTICE_BASE_URL}/ias/ui/rejstrik-$firma"
JUSTICE_RATE_LIMIT = 30  # Conservative limit for web scraping

# ORSR Slovak Configuration
ORSR_BASE_URL = "https://www.orsr.sk"
ORSR_SEARCH_URL = f"{ORSR_BASE_URL}/hladaj_ico.asp"
ORSR_NAME_SEARCH_URL = f"{ORSR_BASE_URL}/search_subjekt.asp"
ORSR_RATE_LIMIT = 60  # Conservative limit for scraping

# Slovak Statistics Configuration
STATS_BASE_URL = "https://statdat.statistics.sk/"
STATS_API_URL = f"{STATS_BASE_URL}/api"

# RPO Slovak Configuration (Register of Legal Entities)
RPO_BASE_URL = "https://api.statistics.sk/rpo/v1"
RPO_SEARCH_URL = f"{RPO_BASE_URL}/search"
RPO_RATE_LIMIT = 100

# RPVS Slovak Configuration (Register of Public Sector Partners - UBO)
# OData API: https://rpvs.gov.sk/opendatav2/PartneriVerejnehoSektora?$filter=Ico eq '{ICO}'
RPVS_BASE_URL = "https://rpvs.gov.sk/opendatav2"
RPVS_ODATA_ENDPOINT = f"{RPVS_BASE_URL}/PartneriVerejnehoSektora"
RPVS_API_KEY = os.getenv("RPVS_API_KEY")  # Optional (not required for OData public endpoint)
RPVS_RATE_LIMIT = 30

# Finančná správa Configuration (Tax Office - VAT, Debts)
FINANCNA_BASE_URL = "https://opendata.financnasprava.sk/api"
FINANCNA_RATE_LIMIT = 50

# ESM Czech Configuration (Register of Beneficial Owners - RESTRICTED)
ESM_BASE_URL = "https://issm.justice.cz"
ESM_API_KEY = os.getenv("ESM_API_KEY")  # Required for access
ESM_RATE_LIMIT = 20

# DPH Czech Configuration (VAT Register - Daň z přidané hodnoty)
DPH_BASE_URL = "https://adisepo.financnispraha.cz"
DPH_SEARCH_URL = f"{DPH_BASE_URL}/actorz/nodes"
DPH_RATE_LIMIT = 30

# VR Czech Configuration (Vermont Register - Register oddělovaných nemovitostí)
VR_BASE_URL = "https://rpvs.gov.cz"
VR_ODATA_ENDPOINT = f"{VR_BASE_URL}/openapi/v2/DssvzdyOvlastenaPodleJmeno"
VR_RATE_LIMIT = 30

# RES Czech Configuration (Resident Income Tax - Rezidentní poplatk daně z příjmů)
RES_BASE_URL = "https://adisepo.financnispraha.cz"
RES_SEARCH_URL = f"{RES_BASE_URL}/dpf/z/zoznam"
RES_RATE_LIMIT = 30

# RUZ Slovak Configuration (Register of Financial Statements)
RUZ_BASE_URL = "https://registeruz.sk"
RUZ_API_BASE = f"{RUZ_BASE_URL}/cruz-public/api"
RUZ_SEARCH_URL = f"{RUZ_BASE_URL}/cruz-public/domain/accountingentity/simplesearch"
RUZ_RATE_LIMIT = 60

# NBS Slovak Configuration (National Bank - Financial Entities)
NBS_BASE_URL = "https://subjekty.nbs.sk"
NBS_SEARCH_URL = f"{NBS_BASE_URL}/sutor/api/v1/subjects"
NBS_RATE_LIMIT = 30

# Smlouvy Czech Configuration (Public Contracts Register)
SMLOUVY_BASE_URL = "https://smlouvy.gov.cz"
SMLOUVY_SEARCH_URL = f"{SMLOUVY_BASE_URL}/api/v1/hledat"
SMLOUVY_RATE_LIMIT = 30

# CNB Czech Configuration (Czech National Bank - Financial Entities)
CNB_BASE_URL = "https://www.cnb.cz"
CNB_REGISTERS_URL = f"{CNB_BASE_URL}/en/supervision-financial-market/lists-registers"
CNB_RATE_LIMIT = 30

# IVES Slovak Configuration (NGO Register)
IVES_BASE_URL = "https://ives.minv.sk"
IVES_SEARCH_URL = f"{IVES_BASE_URL}/register/uzivatelske-vyhledavani"
IVES_RATE_LIMIT = 30

# Output directories
ARES_OUTPUT_DIR = OUTPUT_DIR / "ares"
ORSR_OUTPUT_DIR = OUTPUT_DIR / "orsr"
STATS_OUTPUT_DIR = OUTPUT_DIR / "stats"
JUSTICE_OUTPUT_DIR = OUTPUT_DIR / "justice"
RPO_OUTPUT_DIR = OUTPUT_DIR / "rpo"
RPVS_OUTPUT_DIR = OUTPUT_DIR / "rpvs"
FINANCNA_OUTPUT_DIR = OUTPUT_DIR / "financna"
ESM_OUTPUT_DIR = OUTPUT_DIR / "esm"
RUZ_OUTPUT_DIR = OUTPUT_DIR / "ruz"
NBS_OUTPUT_DIR = OUTPUT_DIR / "nbs"
SMLOUVY_OUTPUT_DIR = OUTPUT_DIR / "smlouvy"
CNB_OUTPUT_DIR = OUTPUT_DIR / "cnb"
IVES_OUTPUT_DIR = OUTPUT_DIR / "ives"
DPH_OUTPUT_DIR = OUTPUT_DIR / "dph"
VR_OUTPUT_DIR = OUTPUT_DIR / "vr"
RES_OUTPUT_DIR = OUTPUT_DIR / "res"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "scraper.log"

# Snapshots directory
SNAPSHOTS_DIR = BASE_DIR / "snapshots"

# ============================================================================
# Playwright Configuration
# ============================================================================

# Playwright browser mode
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"

# Default timeout for Playwright operations (milliseconds)
PLAYWRIGHT_TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))

# Screenshot directory for debugging
PLAYWRIGHT_SCREENSHOT_DIR = SNAPSHOTS_DIR / "screenshots"

# User Agent for requests - using realistic browser User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Register URL templates for constructing direct links to entity entries
ARES_ENTITY_URL_TEMPLATE = f"{ARES_BASE_URL}/{{ico}}"
ORSR_ENTITY_URL_TEMPLATE = f"{ORSR_BASE_URL}/vypis.asp?lan=en&ID={{detail_id}}&SID={{court_id}}"
ORSR_SEARCH_URL_TEMPLATE = f"{ORSR_BASE_URL}/hladaj_ico.asp?ICO={{ico}}&lan=en"
RPO_ENTITY_URL_TEMPLATE = f"{RPO_BASE_URL}/entity/{{ico}}"
RPVS_ENTITY_URL_TEMPLATE = f"{RPVS_BASE_URL}/PartneriVerejnehoSektora?$filter=Ico eq '{{ico}}'"
FINANCNA_ENTITY_URL_TEMPLATE = f"{FINANCNA_BASE_URL}/tax/{{ico}}"
ESM_ENTITY_URL_TEMPLATE = f"{ESM_BASE_URL}/ubo/{{ico}}"
JUSTICE_ENTITY_URL_TEMPLATE = f"{JUSTICE_SEARCH_URL}?ico={{ico}}"
RUZ_ENTITY_URL_TEMPLATE = f"{RUZ_SEARCH_URL}?ico={{ico}}"
NBS_ENTITY_URL_TEMPLATE = f"{NBS_BASE_URL}/subject/{{ico}}"
SMLOUVY_ENTITY_URL_TEMPLATE = f"{SMLOUVY_BASE_URL}/smlouva/{{id}}"
CNB_ENTITY_URL_TEMPLATE = f"{CNB_BASE_URL}/subject/{{ico}}"
IVES_ENTITY_URL_TEMPLATE = f"{IVES_BASE_URL}/zaznam/{{id}}"
DPH_ENTITY_URL_TEMPLATE = f"{DPH_BASE_URL}/dpf/hledani/dic/{{ico}}"
VR_ENTITY_URL_TEMPLATE = f"{VR_BASE_URL}/openapi/v2/DssvzdyOvlastenaPodleJmeno?meno={{name}}"
RES_ENTITY_URL_TEMPLATE = f"{RES_BASE_URL}/dpf/z/osoba/{{ico}}"
