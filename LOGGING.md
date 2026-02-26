# Logging System Documentation

## Overview

All scrapers now have **comprehensive logging** for debugging, monitoring, and audit trails.

## Features

- **Structured Logging**: JSON format for file logs with timestamps, context, and metadata
- **Colored Console Output**: Easy-to-read colored console logs
- **Custom Log Levels**: Including `MAINTENANCE` level for site downtime
- **Context-Aware Logging**: Automatic logging of requests, responses, parsing, rate limiting
- **Operation Timing**: Automatic timing of HTTP requests

---

## Python Logging

### Enhanced Logger Usage

```python
from src.scrapers.ares_czech import ARESCzechScraper

scraper = ARESCzechScraper()

# Standard log methods
scraper.log_info("Info message", key="value")
scraper.log_warning("Warning message")
scraper.log_error("Error message", exc=exception)
scraper.log_debug("Debug message", context={"key": "value"})
scraper.log_maintenance("Maintenance detected")

# Context-specific logging
scraper.log_request("GET", "https://api.example.com")
scraper.log_response("https://api.example.com", 200, 150.5)
scraper.log_parse_start("HTML")
scraper.log_parse_complete("HTML", items_found=5)
scraper.log_rate_limit(5.0)
scraper.log_mock_fallback("API unavailable")

# Operation timing context
with scraper.log_operation_start("complex_operation"):
    # Your operation code here
    pass
```

### Log Levels

| Level | Value | Usage |
|-------|-------|-------|
| DEBUG | 10 | Detailed diagnostic information |
| INFO | 20 | General informational messages |
| MAINTENANCE | 25 | Site/API maintenance warnings |
| WARNING | 30 | Warning messages |
| ERROR | 40 | Error messages |
| CRITICAL | 50 | Critical errors |

### Console Output Format

```
[HH:mm:ss.fff] SOURCENAME | LEVEL  | Message
```

Example:
```
[10:30:45.123] ARES_CZ | INFO   | Search started: by_id = 00006947
[10:30:45.456] ARES_CZ | INFO   | Found entity for IČO 00006947: Ministerstvo financí
[10:30:45.789] ARES_CZ | MAINT  | Justice.cz is under maintenance
```

### File Log Format (JSON)

```json
{
  "timestamp": "2026-02-21T10:30:45.123456",
  "level": "INFO",
  "logger": "src.scrapers.ares_czech.ARESCzechScraper",
  "message": "Search started: by_id = 00006947",
  "scraper": "ARES_CZ",
  "extra": {
    "search_type": "by_id",
    "identifier": "00006947"
  }
}
```

---

## C# Logging

### ScraperLogger Usage

```csharp
using UnifiedOutput;

var logger = new ScraperLogger("ARES", enableDebug: false);

// Standard log methods
logger.Info("Info message");
logger.Warning("Warning message");
logger.Error("Error message", exception);
logger.Debug("Debug message");
logger.Maintenance("Maintenance detected");

// Context-specific logging
logger.LogRequest("GET", "https://api.example.com");
logger.LogResponse("https://api.example.com", 200, 150.5);
logger.LogParseStart("HTML");
logger.LogParseComplete("HTML", 5);
logger.LogRateLimit(5.0);
logger.LogMockFallback("API unavailable");

// Search logging
logger.LogSearchStart("00006947", "by_ICO");
logger.LogSearchComplete(1, "00006947");

// Operation timing
using (var op = logger.BeginTimedOperation("API Request"))
{
    // Your operation code here
}
```

### Console Output Format

```
[HH:mm:ss.fff] SOURCENAME | LEVEL  | Message
```

Example:
```
[10:30:45.123] ARES | INFO   | Search started: by_id = 00006947
[10:30:45.456] ARES | INFO   | Found entity for IČO 00006947: Ministerstvo financí
[10:30:45.789] ARES | MAINT  | Justice.cz is under maintenance
```

---

## Logging by Operation Type

### HTTP Requests

```python
# Automatically logged with timing
scraper.log_request("GET", url)
scraper.log_response(url, status_code, duration_ms)
```

Output:
```
DEBUG | GET https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/00006947
✅ 200 from https://ares.gov.cz/... (150ms)
```

### Parsing Operations

```python
scraper.log_parse_start("HTML")
scraper.log_parse_complete("HTML", items_found=5)
```

Output:
```
DEBUG | Parsing HTML...
INFO  | Parsed HTML: 5 items
```

### Maintenance Detection

```python
scraper.log_maintenance("Justice.cz")
```

Output:
```
MAINTENANCE | Justice.cz is under maintenance
```

### Rate Limiting

```python
scraper.log_rate_limit(5.0)
```

Output:
```
DEBUG | Rate limit: waiting 5.0s
```

---

## Configuration

### Enable Debug Logging

**Python:**
```bash
export LOG_LEVEL=DEBUG
```

**C#:**
```csharp
var logger = new ScraperLogger("ARES", enableDebug: true);
```

### Log File Location

**Python:**
- Default: `python/scraper.log`
- Can be customized via `LOG_FILE` environment variable

**C#:**
- Console only (file logging can be added)

### Disable Console Logging

**Python:**
```python
# Modify logger_enhanced.py or set environment variable
```

---

## Log Examples by Scraper

### ARES Czech Scraper

```
[10:30:45] ARES_CZ | INFO   | ARES_CZ scraper ready (rate limit: 500 req/min)
[10:30:45] ARES_CZ | INFO   | Search started: by_id = 00006947
[10:30:45] ARES_CZ | DEBUG  | GET https://ares.gov.cz/.../00006947
[10:30:45] ARES_CZ | DEBUG  | ✅ 200 from ... (156ms)
[10:30:45] ARES_CZ | INFO   | Found entity for IČO 00006947: Ministerstvo financí
[10:30:45] ARES_CZ | DEBUG  | Parsing ARES_API...
[10:30:45] ARES_CZ | INFO   | Parsed ARES_API: 1 items
[10:30:45] ARES_CZ | INFO   | Sub-sources: 4 active registries
[10:30:45] ARES_CZ | INFO   | Search complete for 00006947: 1 result(s)
```

### Justice Czech Scraper

```
[10:30:45] JUSTICE_CZ | INFO   | Justice.cz scraper ready (playwright=True, delay=10s)
[10:30:45] JUSTICE_CZ | INFO   | Search started: by_id = 05984866
[10:30:45] JUSTICE_CZ | DEBUG  | Rate limit: waiting 10.0s
[10:30:55] JUSTICE_CZ | MAINT  | Justice.cz is under maintenance
```

### ORSR Slovak Scraper

```
[10:30:45] ORSR_SK | INFO   | ORSR_SK scraper ready (rate limit: 60 req/min)
[10:30:45] ORSR_SK | INFO   | Search started: by_id = 47559870
[10:30:45] ORSR_SK | DEBUG  | GET https://www.orsr.sk/hladaj_ico.asp?ICO=47559870
[10:30:46] ORSR_SK | DEBUG  | ✅ 200 from ... (850ms)
[10:30:46] ORSR_SK | INFO   | Found entity: ZELEX, s.r.o.
[10:30:46] ORSR_SK | INFO   | Search complete for 47559870: 1 result(s)
```

---

## Troubleshooting with Logs

### Enable Debug Logging

```bash
# Python
export LOG_LEVEL=DEBUG
python3 -c "from src.scrapers.ares_czech import ARESCzechScraper; ..."
```

### Check Log Files

```bash
# Python - View recent logs
tail -f python/scraper.log

# Filter for specific scraper
grep "ARES_CZ" python/scraper.log
grep "MAINTENANCE" python/scraper.log
```

### Common Log Patterns

**Search for errors:**
```bash
grep "ERROR" python/scraper.log
```

**Search for maintenance:**
```bash
grep "MAINTENANCE" python/scraper.log
```

**Search for specific ICO:**
```bash
grep "00006947" python/scraper.log
```

**View request timing:**
```bash
grep "duration_ms" python/scraper.log
```

---

## Files Modified

**Python:**
- `src/utils/logger_enhanced.py` - Enhanced logger with structured logging
- `src/scrapers/base.py` - Added enhanced logging methods to BaseScraper
- `src/scrapers/ares_czech.py` - Updated to use enhanced logging
- `src/scrapers/justice_czech.py` - Updated to use enhanced logging
- `src/scrapers/orsr_slovak.py` - Updated to use enhanced logging
- `src/scrapers/rpvs_slovak.py` - Updated to use enhanced logging

**C#:**
- `ScraperLogger.cs` - New enhanced logger for C#
- `AresClient.cs` - Updated to use ScraperLogger
- `JusticeClient.cs` - Updated to use ScraperLogger
- `OrsrClient.cs` - Updated to use ScraperLogger
- `RpvsClient.cs` - Updated to use ScraperLogger

---

## Best Practices

1. **Always log search operations**: Use `log_search_start()` and `log_search_complete()`
2. **Log HTTP requests**: Use `log_request()` and `log_response()` for API calls
3. **Log parsing operations**: Use `log_parse_start()` and `log_parse_complete()`
4. **Log maintenance**: Use `log_maintenance()` when maintenance is detected
5. **Log rate limiting**: Use `log_rate_limit()` to show delays
6. **Log errors with context**: Include relevant ICO, URL, or operation name
7. **Use appropriate log levels**: DEBUG for details, INFO for normal ops, WARNING for issues

---

## Maintenance Response Logging

When maintenance is detected, you'll see:

```
MAINTENANCE | Justice.cz is under maintenance
```

The response will include:
```json
{
  "metadata": {
    "maintenance": true,
    "maintenance_message": "Justice.cz is under maintenance (Momentálně probíhá údržba)"
  }
}
```

---

## JSON Structured Logs

File logs are in JSON format for easy parsing:

```json
{
  "timestamp": "2026-02-21T10:30:45.123456",
  "level": "INFO",
  "logger": "src.scrapers.ares_czech.ARESCzechScraper",
  "message": "Found entity for IČO 00006947: Ministerstvo financí",
  "scraper": "ARES_CZ",
  "extra": {
    "ico": "00006947",
    "action": "response"
  }
}
```

This can be parsed by log aggregation tools like:
- ELK Stack
- Splunk
- Graylog
- AWS CloudWatch Logs
