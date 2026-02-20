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
        }

        /// <summary>
        /// Search company by ICO and return unified output format.
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            await ApplyRateLimitAsync();

            try
            {
                var url = $"{SearchUrl}?ICO={Uri.EscapeDataString(ico.Trim())}&lan=en";
                var html = await GetStringWindows1250Async(url);

                return ParseSearchResult(html, ico);
            }
            catch (HttpRequestException)
            {
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
                        if (cells.Count >= 2)
                        {
                            var link = row.Descendants("a").FirstOrDefault();
                            if (link != null)
                            {
                                var name = link.Value;
                                var text = row.Value;

                                if (text.Contains(ico))
                                {
                                    // Find address in text
                                    string? fullAddress = null;
                                    foreach (var cell in cells)
                                    {
                                        var cellText = cell.Value;
                                        if (cellText.Contains(",") && cellText.Any(char.IsDigit))
                                        {
                                            fullAddress = cellText.Trim();
                                            break;
                                        }
                                    }

                                    var address = new UnifiedAddress
                                    {
                                        FullAddress = fullAddress,
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
                }

                return null;
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
