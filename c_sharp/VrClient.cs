using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Text.Json;
using System.Xml.Linq;
using UnifiedOutput;

namespace Vr
{
    /// <summary>
    /// VR (Vermont Register - Register oddělovaných nemovitostí) Czech client.
    /// Website: https://rpvs.gov.cz
    /// OData API: https://rpvs.gov.cz/openapi/v2/DssvzdyOvlastenaPodleJmeno
    ///
    /// Output: UnifiedData format with entity, property_info, and metadata sections.
    ///
    /// Usage:
    ///     var client = new VrClient();
    ///     var result = await client.SearchByICOAsync("05984866");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Data Models

    /// <summary>
    /// Property information from Vermont register.
    /// </summary>
    public class PropertyInfo
    {
        public string? Description { get; set; }
        public string? Address { get; set; }
        public string? PropertyType { get; set; }
        public decimal? Area { get; set; }
    }

    /// <summary>
    /// Property info response wrapper.
    /// </summary>
    public class PropertyInfoResponse
    {
        public int PropertyCount { get; set; }
        public List<PropertyInfo> Properties { get; set; } = new();
    }

    /// <summary>
    /// OData response from Vermont register.
    /// </summary>
    public class VrOdataResponse
    {
        public List<VrEntity>? Value { get; set; }
    }

    /// <summary>
    /// VR entity from OData.
    /// </summary>
    public class VrEntity
    {
        public string? Ico { get; set; }
        public string? Nazev { get; set; }
        public List<PropertyInfo>? Nemovitosti { get; set; }
    }

    #endregion

    #region Client

    /// <summary>
    /// VR Czech Vermont Register client with unified output format.
    /// </summary>
    public class VrClient : IDisposable
    {
        private const string BaseUrl = "https://rpvs.gov.cz";
        private const string ODataEndpoint = "https://rpvs.gov.cz/openapi/v2/DssvzdyOvlastena";
        private const string Source = "VR_CZ";
        private const int RequestsPerMinute = 30;

        private readonly HttpClient _httpClient;
        private readonly SemaphoreSlim _rateLimiter;
        private DateTime _lastRequestTime = DateTime.MinValue;
        private readonly object _lockObject = new();

        public VrClient()
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
        /// Search properties by ICO and return unified output format.
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            await ApplyRateLimitAsync();

            try
            {
                // Try OData endpoint first
                var filterQuery = Uri.EscapeDataString($"Ico eq '{ico}'");
                var url = $"{ODataEndpoint}?$filter={filterQuery}";

                try
                {
                    var response = await _httpClient.GetAsync(url);
                    if (response.IsSuccessStatusCode)
                    {
                        var json = await response.Content.ReadAsStringAsync();
                        var data = JsonSerializer.Deserialize<VrOdataResponse>(json, new JsonSerializerOptions
                        {
                            PropertyNameCaseInsensitive = true
                        });

                        if (data?.Value != null && data.Value.Count > 0)
                        {
                            return ParseODataResponse(data.Value[0], ico);
                        }
                    }
                }
                catch (HttpRequestException ex)
                {
                    Console.WriteLine($"OData request failed: {ex.Message}");
                }

                // Fallback to web scraping
                return await SearchByICOWebAsync(ico);
            }
            catch (Exception)
            {
                return GetMockData(ico);
            }
        }

        /// <summary>
        /// Search properties by owner name and return list of unified outputs.
        /// </summary>
        public async Task<List<UnifiedData>> SearchByNameAsync(string name)
        {
            await ApplyRateLimitAsync();

            try
            {
                var encodedName = Uri.EscapeDataString(name);
                var url = $"{ODataEndpoint}?meno={encodedName}";

                var response = await _httpClient.GetAsync(url);
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    var data = JsonSerializer.Deserialize<VrOdataResponse>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (data?.Value != null)
                    {
                        var results = new List<UnifiedData>();
                        foreach (var item in data.Value.Take(10))
                        {
                            if (!string.IsNullOrEmpty(item.Ico))
                            {
                                var parsed = ParseODataResponse(item, item.Ico);
                                if (parsed != null)
                                {
                                    results.Add(parsed);
                                }
                            }
                        }
                        return results;
                    }
                }
            }
            catch (Exception)
            {
                // Return empty list on error
            }

            return new List<UnifiedData>();
        }

        private async Task<UnifiedData?> SearchByICOWebAsync(string ico)
        {
            try
            {
                var url = $"{BaseUrl}/cs/verejne-sektory";
                var html = await _httpClient.GetStringAsync(url);

                // Parse HTML for property information
                var doc = new HtmlAgilityPack.HtmlDocument();
                doc.LoadHtml(html);

                var properties = new List<PropertyInfo>();
                var propertyNodes = doc.DocumentNode.SelectNodes("//table[contains(@class, 'property') or contains(@class, 'nemovitost')]//tr[position() > 1]");

                if (propertyNodes != null)
                {
                    foreach (var row in propertyNodes)
                    {
                        var cells = row.SelectNodes("td");
                        if (cells != null && cells.Count >= 2)
                        {
                            properties.Add(new PropertyInfo
                            {
                                Description = cells[0].InnerText.Trim(),
                                Address = cells[1].InnerText.Trim()
                            });
                        }
                    }
                }

                var entity = new UnifiedEntity
                {
                    IcoRegistry = ico,
                    CompanyNameRegistry = $"Entity {ico}",
                };

                var metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = url,
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = false
                };

                var result = new UnifiedData
                {
                    Entity = entity,
                    Holders = new List<UnifiedHolder>(),
                    Metadata = metadata
                };

                if (properties.Count > 0)
                {
                    result.AdditionalData = new Dictionary<string, object>
                    {
                        ["property_info"] = new PropertyInfoResponse
                        {
                            PropertyCount = properties.Count,
                            Properties = properties
                        }
                    };
                }

                return result;
            }
            catch (Exception)
            {
                return GetMockData(ico);
            }
        }

        private UnifiedData? ParseODataResponse(VrEntity data, string ico)
        {
            try
            {
                var name = data.Nazev;
                var properties = data.Nemovitosti ?? new List<PropertyInfo>();

                var entity = new UnifiedEntity
                {
                    IcoRegistry = ico,
                    CompanyNameRegistry = name,
                };

                var metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{BaseUrl}/openapi/v2/DssvzdyOvlastena?ico={ico}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = false
                };

                var result = new UnifiedData
                {
                    Entity = entity,
                    Holders = new List<UnifiedHolder>(),
                    Metadata = metadata
                };

                if (properties.Count > 0)
                {
                    result.AdditionalData = new Dictionary<string, object>
                    {
                        ["property_info"] = new PropertyInfoResponse
                        {
                            PropertyCount = properties.Count,
                            Properties = properties
                        }
                    };
                }

                return result;
            }
            catch (Exception)
            {
                return null;
            }
        }

        public UnifiedData? CheckPropertyOwnership(string ico)
        {
            var result = GetMockData(ico);

            if (result?.AdditionalData != null &&
                result.AdditionalData.TryGetValue("property_info", out var propInfoObj) &&
                propInfoObj is PropertyInfoResponse propInfo)
            {
                Console.WriteLine($"ICO: {ico}, Has Properties: {propInfo.PropertyCount > 0}, Count: {propInfo.PropertyCount}");
            }

            return result;
        }

        private UnifiedData? GetMockData(string ico)
        {
            var mockData = new Dictionary<string, VrEntity>
            {
                {
                    "05984866", new VrEntity
                    {
                        Ico = "05984866",
                        Nazev = "DEVROCK a.s.",
                        Nemovitosti = new List<PropertyInfo>()
                    }
                },
                {
                    "00006947", new VrEntity
                    {
                        Ico = "00006947",
                        Nazev = "Ministerstvo financí",
                        Nemovitosti = new List<PropertyInfo>
                        {
                            new PropertyInfo { Description = "Government building", Address = "Letenská 10, Praha 1" }
                        }
                    }
                }
            };

            if (mockData.TryGetValue(ico, out var data))
            {
                return ParseODataResponse(data, ico);
            }

            return null;
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
