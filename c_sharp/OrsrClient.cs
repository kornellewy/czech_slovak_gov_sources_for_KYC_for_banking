using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Xml.Linq;
using UnifiedOutput;

namespace Orsr
{
    /// <summary>
    /// ORSR (Business Register) Slovak company registry client.
    /// Website: https://www.orsr.sk
    ///
    /// Output: UnifiedData? format with entity, metadata sections.
    ///
    /// Usage:
    ///     var client = new OrsrClient();
    ///     var result = await client.SearchByICOAsync("35763491");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Client

    /// <summary>
    /// ORSR Slovak Business Register client with unified output format.
    /// </summary>
    public class OrsrClient : IDisposable
    {
        private const string BaseUrl = "https://www.orsr.sk";
        private const string SearchUrl = "https://www.orsr.sk/hladaj_ico.asp";
        private const string Source = "ORSR_SK";
        private const int RequestsPerMinute = 60;

        private readonly HttpClient _httpClient;
        private readonly SemaphoreSlim _rateLimiter;
        private readonly ScraperLogger _logger;
        private DateTime _lastRequestTime = DateTime.MinValue;
        private readonly object _lockObject = new();

        private static readonly Dictionary<string, string> CourtCodes = new()
        {
            { "Obchodný register Okresného súdu Bratislava I", "OS1BA" },
            { "Obchodný register Okresného súdu Bratislava II", "OS2BA" },
            { "Obchodný register Mestského súdu Bratislava I", "MS1BA" },
            { "Obchodný register Okresného súdu Košice I", "OS1KI" },
            { "Obchodný register Okresného súdu Trnava", "OSTT" },
            { "Obchodný register Okresného súdu Nitra", "OSNR" },
            { "Obchodný register Okresného súdu Žilina", "OSZA" },
            { "Obchodný register Okresného súdu Banská Bystrica", "OSBB" },
            { "Obchodný register Okresného súdu Prešov", "OSPO" }
        };

        public OrsrClient()
        {
            var handler = new HttpClientHandler
            {
                AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate
            };

            _httpClient = new HttpClient(handler)
            {
                Timeout = TimeSpan.FromSeconds(30)
            };

            _httpClient.DefaultRequestHeaders.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

            _rateLimiter = new SemaphoreSlim(1, 1);
            _logger = new ScraperLogger("ORSR", enableDebug: false);
            _logger.Info($"ORSR Client initialized (rate limit: {RequestsPerMinute} req/min)");
        }

        /// <summary>
        /// Search company by ICO and return unified output format.
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            _logger.LogSearchStart(ico?.Trim(), "by_ICO");
            await ApplyRateLimitAsync();

            var stopwatch = System.Diagnostics.Stopwatch.StartNew();

            try
            {
                var url = $"{SearchUrl}?ICO={Uri.EscapeDataString(ico.Trim())}&lan=en";
                _logger.LogRequest("GET", url);

                var html = await GetStringWindows1250Async(url);

                stopwatch.Stop();
                _logger.LogResponse(url, 200, stopwatch.ElapsedMilliseconds);

                _logger.LogParseStart("HTML");
                var result = ParseSearchResult(html, ico);

                if (result != null)
                {
                    _logger.LogParseComplete("HTML", 1);
                    _logger.LogSearchComplete(1, ico);
                }

                return result;
            }
            catch (HttpRequestException ex)
            {
                stopwatch.Stop();
                _logger.LogResponse($"{SearchUrl}?ICO={ico}", 500, stopwatch.ElapsedMilliseconds);
                _logger.LogError("SearchByICOAsync", ex, new { ico });
                return null;
            }
        }

        /// <summary>
        /// Search companies by name and return list of unified outputs.
        /// </summary>
        public async Task<List<UnifiedData>> SearchByNameAsync(string name)
        {
            await ApplyRateLimitAsync();

            try
            {
                var url = $"{BaseUrl}/search_subjekt.asp?OBMENO={Uri.EscapeDataString(name)}&lan=en";
                var html = await GetStringWindows1250Async(url);

                return ParseSearchResults(html);
            }
            catch (HttpRequestException)
            {
                return new List<UnifiedData>();
            }
        }

        private async Task<string> GetStringWindows1250Async(string url)
        {
            var bytes = await _httpClient.GetByteArrayAsync(url);

            // Register Windows-1250 encoding
            Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
            var encoding = Encoding.GetEncoding("windows-1250");

            return encoding.GetString(bytes);
        }

        private UnifiedData? ParseSearchResult(string html, string ico)
        {
            try
            {
                var doc = XDocument.Parse(PreprocessHtml(html));
                var tables = doc.Descendants("table");

                foreach (var table in tables)
                {
                    var rows = table.Descendants("tr");
                    foreach (var row in rows)
                    {
                        var cells = row.Descendants("td").ToList();
                        // Need at least 3 cells for a valid result row
                        if (cells.Count >= 3)
                        {
                            // Check if this is a data row (has vypis.asp link to detail page)
                            var detailLink = cells[2].Descendants("a")
                                .FirstOrDefault(a => a.Value != null && a.Attribute("href") != null &&
                                                   a.Attribute("href").Value.Contains("vypis.asp") &&
                                                   a.Attribute("href").Value.Contains("ID="));

                            if (detailLink != null)
                            {
                                // Extract company name from second cell (index 1)
                                // Company name is the text content, not the link text
                                var name = cells[1].Value.Trim();

                                // Build detail URL
                                var href = detailLink.Attribute("href").Value;
                                var detailUrl = href.StartsWith("http") ? href : $"{BaseUrl}/{href}";

                                // Try to fetch complete data from detail page
                                var detailResult = GetCompanyDetailAsync(detailUrl).GetAwaiter().GetResult();
                                if (detailResult != null)
                                {
                                    return detailResult;
                                }

                                // Fallback: return basic info
                                var address = new UnifiedAddress
                                {
                                    FullAddress = ExtractAddress(cells),
                                    Country = "Slovensko",
                                    CountryCode = "SK"
                                };

                                var entity = new UnifiedEntity
                                {
                                    IcoRegistry = ico,
                                    CompanyNameRegistry = name,
                                    Status = "active",
                                    RegisteredAddress = address
                                };

                                var metadata = new UnifiedMetadata
                                {
                                    Source = Source,
                                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                                    RegisterUrl = $"{SearchUrl}?ICO={ico}&lan=en",
                                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                                    IsMock = false
                                };

                                return new UnifiedData
                                {
                                    Entity = entity,
                                    Holders = new List<UnifiedHolder>(),
                                    Metadata = metadata
                                };
                            }
                        }
                    }
                }

                return null;
            }
            catch
            {
                return null;
            }
        }

        private string? ExtractAddress(List<XElement> cells)
        {
            foreach (var cell in cells)
            {
                var cellText = cell.Value.Trim();
                // Look for address pattern (contains comma and digits)
                if (cellText.Contains(",") && cellText.Any(char.IsDigit))
                {
                    return cellText;
                }
            }
            return null;
        }

        private async Task<UnifiedData?> GetCompanyDetailAsync(string detailUrl)
        {
            try
            {
                await ApplyRateLimitAsync();
                var html = await GetStringWindows1250Async(detailUrl);
                return ParseDetailPage(html, detailUrl);
            }
            catch
            {
                return null;
            }
        }

        private UnifiedData? ParseDetailPage(string html, string detailUrl)
        {
            try
            {
                var doc = XDocument.Parse(PreprocessHtml(html));

                var detailData = new Dictionary<string, string?>
                {
                    ["name"] = null,
                    ["ico"] = null,
                    ["address"] = null,
                    ["date_registered"] = null,
                    ["court"] = null,
                    ["legal_form"] = null
                };

                // Define label patterns (both English and Slovak)
                var labelPatterns = new Dictionary<string, string[]>
                {
                    ["name"] = new[] { "Business name", "Obchodné meno" },
                    ["ico"] = new[] { "Identification number (IČO)", "Identification number (I", "IČO:" },
                    ["address"] = new[] { "Registered seat", "Sídlo" },
                    ["date_registered"] = new[] { "Date of entry", "Dátum zápisu" },
                    ["court"] = new[] { "Court", "Súd" },
                    ["legal_form"] = new[] { "Legal form", "Právna forma" }
                };

                // Extract key-value pairs from tables
                foreach (var table in doc.Descendants("table"))
                {
                    foreach (var row in table.Descendants("tr"))
                    {
                        var cells = row.Descendants("td").ToList();
                        if (cells.Count >= 2)
                        {
                            var key = cells[0].Value.Trim();
                            var valueCell = cells[1];

                            // Value might be in nested table
                            var nestedTable = valueCell.Descendants("table").FirstOrDefault();
                            string value;
                            if (nestedTable != null)
                            {
                                var nestedRows = nestedTable.Descendants("tr").ToList();
                                if (nestedRows.Any())
                                {
                                    var nestedCells = nestedRows[0].Descendants("td").ToList();
                                    value = nestedCells.Any() ? nestedCells[0].Value.Trim() : valueCell.Value.Trim();
                                }
                                else
                                {
                                    value = valueCell.Value.Trim();
                                }
                            }
                            else
                            {
                                value = valueCell.Value.Trim();
                            }

                            // Match key to field using patterns
                            foreach (var kvp in labelPatterns)
                            {
                                var field = kvp.Key;
                                var patterns = kvp.Value;
                                if (patterns.Any(p => key.IndexOf(p, StringComparison.OrdinalIgnoreCase) >= 0))
                                {
                                    // Clean up the value (remove "(from: DATE)" suffix)
                                    value = value.Split(new[] { "(from:" }, StringSplitOptions.None)[0].Trim();
                                    if (!string.IsNullOrEmpty(value))
                                    {
                                        detailData[field] = value;
                                    }
                                    break;
                                }
                            }
                        }
                    }
                }

                // Clean up ICO
                var ico = detailData["ico"]?.Replace(" ", "").Split(new[] { "(from:" }, StringSplitOptions.None)[0].Trim() ?? "";

                // Build address
                var address = new UnifiedAddress
                {
                    FullAddress = detailData["address"],
                    Country = "Slovensko",
                    CountryCode = "SK"
                };

                var entity = new UnifiedEntity
                {
                    IcoRegistry = ico,
                    CompanyNameRegistry = detailData["name"],
                    LegalForm = detailData["legal_form"],
                    Status = "active",
                    IncorporationDate = detailData["date_registered"],
                    RegisteredAddress = address
                };

                var metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = detailUrl,
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = false
                };

                return new UnifiedData
                {
                    Entity = entity,
                    Holders = new List<UnifiedHolder>(),
                    Metadata = metadata
                };
            }
            catch
            {
                return null;
            }
        }

        private List<UnifiedData> ParseSearchResults(string html)
        {
            var results = new List<UnifiedData>();

            try
            {
                var doc = XDocument.Parse(PreprocessHtml(html));
                var tables = doc.Descendants("table");

                foreach (var table in tables)
                {
                    var rows = table.Descendants("tr");
                    foreach (var row in rows)
                    {
                        var link = row.Descendants("a").FirstOrDefault();
                        if (link != null)
                        {
                            var name = link.Value;
                            var text = row.Value;
                            var ico = ExtractICO(text);

                            if (!string.IsNullOrEmpty(ico))
                            {
                                var entity = new UnifiedEntity
                                {
                                    IcoRegistry = ico,
                                    CompanyNameRegistry = name,
                                    Status = "active"
                                };

                                var metadata = new UnifiedMetadata
                                {
                                    Source = Source,
                                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                                    RegisterUrl = $"{SearchUrl}?ICO={ico}&lan=en",
                                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                                    IsMock = false
                                };

                                results.Add(new UnifiedData
                                {
                                    Entity = entity,
                                    Holders = new List<UnifiedHolder>(),
                                    Metadata = metadata
                                });
                            }
                        }
                    }
                }
            }
            catch
            {
                // Return empty list on parse error
            }

            return results;
        }

        private string ExtractICO(string text)
        {
            var parts = text.Split(new[] { ' ', '\t', '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (var part in parts)
            {
                if (part.Length == 8 && part.All(char.IsDigit))
                {
                    return part;
                }
            }
            return string.Empty;
        }

        private string PreprocessHtml(string html)
        {
            return $"<root>{html}</root>";
        }

        private async Task ApplyRateLimitAsync()
        {
            await _rateLimiter.WaitAsync();
            try
            {
                lock (_lockObject)
                {
                    var elapsed = DateTime.Now - _lastRequestTime;
                    var intervalMs = 60000 / RequestsPerMinute;

                    if (elapsed.TotalMilliseconds < intervalMs)
                    {
                        var delay = intervalMs - (int)elapsed.TotalMilliseconds;
                        Thread.Sleep(delay);
                    }
                    _lastRequestTime = DateTime.Now;
                }
            }
            finally
            {
                _rateLimiter.Release();
            }
        }

        public void Dispose()
        {
            _httpClient.Dispose();
            _rateLimiter.Dispose();
        }
    }

    #endregion
}
