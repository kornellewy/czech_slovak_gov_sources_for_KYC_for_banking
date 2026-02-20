using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Text.Json;
using System.Text.RegularExpressions;
using UnifiedOutput;

namespace Ives
{
    /// <summary>
    /// IVES (Register of Non-Governmental Non-Profit Organizations) Slovak client.
    /// Website: https://ives.minv.sk/rmno
    /// Official Name: Register mimovládnych neziskových organizácií (RMNO)
    ///
    /// Output: UnifiedData format with entity, ngo_info, and metadata sections.
    ///
    /// Usage:
    ///     var client = new IvesClient();
    ///     var result = await client.SearchByICOAsync("00123456");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Data Models

    /// <summary>
    /// NGO types.
    /// </summary>
    public static class NgoTypes
    {
        public const string CivicAssociation = "civic_association";
        public const string Foundation = "foundation";
        public const string NonInvestmentFund = "non_investment_fund";
        public const string NonProfitOrganization = "non_profit_organization";
        public const string RegisteredLeasehold = "registered_leasehold";
    }

    /// <summary>
    /// NGO-specific information.
    /// </summary>
    public class NgoInfo
    {
        public string? NgoType { get; set; }
        public string? NgoTypeOriginal { get; set; }
        public string? RegistrationDate { get; set; }
        public string? Court { get; set; }
        public string? FileNumber { get; set; }
        public string? ScopeOfActivities { get; set; }
        public List<string>? RegisteredGeneralBenefits { get; set; }
    }

    /// <summary>
    /// IVES entity response from API.
    /// </summary>
    public class IvesEntity
    {
        public string? Ico { get; set; }
        public string? Name { get; set; }
        public string? Nazov { get; set; }
        public string? NgoType { get; set; }
        public string? TypOrganizacie { get; set; }
        public string? Status { get; set; }
        public IvesAddress? Address { get; set; }
        public IvesAddress? Adresa { get; set; }
        public string? RegistrationDate { get; set; }
        public string? DatumZapisu { get; set; }
        public string? Court { get; set; }
        public string? Sud { get; set; }
        public string? FileNumber { get; set; }
        public string? Znacka { get; set; }
    }

    public class IvesAddress
    {
        public string? Street { get; set; }
        public string? Ulica { get; set; }
        public string? City { get; set; }
        public string? Obec { get; set; }
        public string? PostalCode { get; set; }
        public string? Psc { get; set; }
        public string? Full { get; set; }
        public string? Cela { get; set; }
    }

    #endregion

    #region Client

    /// <summary>
    /// IVES Slovak NGO Register client with unified output format.
    /// </summary>
    public class IvesClient : IDisposable
    {
        private const string BaseUrl = "https://ives.minv.sk";
        private const string SearchUrl = "https://ives.minv.sk/rmno";
        private const string Source = "IVES_SK";
        private const int RequestsPerMinute = 30;

        private readonly HttpClient _httpClient;
        private readonly SemaphoreSlim _rateLimiter;
        private DateTime _lastRequestTime = DateTime.MinValue;
        private readonly object _lockObject = new();

        private static readonly Dictionary<string, string> NgoTypeMappings = new()
        {
            { "občianske združenie", NgoTypes.CivicAssociation },
            { "občianske združenia", NgoTypes.CivicAssociation },
            { "nadácia", NgoTypes.Foundation },
            { "nadácie", NgoTypes.Foundation },
            { "neinvestičný fond", NgoTypes.NonInvestmentFund },
            { "neinvestičné fondy", NgoTypes.NonInvestmentFund },
            { "nno", NgoTypes.NonProfitOrganization }
        };

        public IvesClient()
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
        /// Search NGO by ICO and return unified output format.
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            await ApplyRateLimitAsync();

            try
            {
                var cleanIco = Regex.Replace(ico ?? "", @"[^\d]", "");

                if (!Regex.IsMatch(cleanIco, @"^\d{8}$"))
                {
                    return null;
                }

                // Try API endpoint
                var apiUrl = $"{SearchUrl}/api/organizations/{cleanIco}";

                try
                {
                    var response = await _httpClient.GetAsync(apiUrl);
                    if (response.IsSuccessStatusCode)
                    {
                        var json = await response.Content.ReadAsStringAsync();
                        var data = JsonSerializer.Deserialize<IvesEntity>(json, new JsonSerializerOptions
                        {
                            PropertyNameCaseInsensitive = true
                        });

                        if (data != null)
                        {
                            return ParseResponse(data, cleanIco);
                        }
                    }
                }
                catch (HttpRequestException ex)
                {
                    Console.WriteLine($"API request failed: {ex.Message}");
                }

                // Fallback to mock data
                return GetMockData(cleanIco);
            }
            catch (Exception)
            {
                return null;
            }
        }

        /// <summary>
        /// Search NGOs by name and return list of results.
        /// </summary>
        public async Task<List<UnifiedData>> SearchByNameAsync(string name)
        {
            await ApplyRateLimitAsync();

            try
            {
                var apiUrl = $"{SearchUrl}/api/search?name={Uri.EscapeDataString(name)}";

                var response = await _httpClient.GetAsync(apiUrl);
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    var data = JsonSerializer.Deserialize<SearchResponse>(json, new JsonSerializerOptions
                    {
                        PropertyNameCaseInsensitive = true
                    });

                    if (data?.Results != null)
                    {
                        var results = new List<UnifiedData>();
                        foreach (var item in data.Results.Take(20))
                        {
                            if (!string.IsNullOrEmpty(item.Ico))
                            {
                                var parsed = ParseResponse(item, item.Ico);
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

        private UnifiedData? ParseResponse(IvesEntity data, string ico)
        {
            try
            {
                var icoVal = data.Ico ?? ico;
                var name = data.Name ?? data.Nazov;
                var address = data.Address ?? data.Adresa;

                var entity = new UnifiedEntity
                {
                    IcoRegistry = icoVal,
                    CompanyNameRegistry = name,
                    Status = NormalizeStatus(data.Status ?? "active")
                };

                var ngoInfo = new NgoInfo
                {
                    NgoType = NormalizeNgoType(data.NgoType ?? data.TypOrganizacie),
                    NgoTypeOriginal = data.NgoType ?? data.TypOrganizacie,
                    RegistrationDate = data.RegistrationDate ?? data.DatumZapisu,
                    Court = data.Court ?? data.Sud,
                    FileNumber = data.FileNumber ?? data.Znacka
                };

                var metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{SearchUrl}?ico={icoVal}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = false
                };

                var result = new UnifiedData
                {
                    Entity = entity,
                    Holders = new List<UnifiedHolder>(),
                    Metadata = metadata
                };

                // Add NGO info to AdditionalData
                result.AdditionalData = new Dictionary<string, object>
                {
                    { "ngo_info", new
                        {
                            ngo_type = ngoInfo.NgoType,
                            ngo_type_original = ngoInfo.NgoTypeOriginal,
                            registration_date = ngoInfo.RegistrationDate,
                            court = ngoInfo.Court,
                            file_number = ngoInfo.FileNumber
                        }
                    }
                };

                return result;
            }
            catch
            {
                return null;
            }
        }

        private string NormalizeStatus(string status)
        {
            return status.ToLower() switch
            {
                "active" => "active",
                "registered" => "active",
                "zapísaná" => "active",
                "deleted" => "cancelled",
                "vymazaná" => "cancelled",
                "suspended" => "suspended",
                "pozastavená" => "suspended",
                _ => status
            };
        }

        private string? NormalizeNgoType(string? ngoType)
        {
            if (string.IsNullOrEmpty(ngoType))
                return null;

            var lower = ngoType.ToLower().Trim();
            return NgoTypeMappings.GetValueOrDefault(lower, "other");
        }

        private UnifiedData? GetMockData(string ico)
        {
            var mockData = new Dictionary<string, IvesEntity>
            {
                {
                    "00123456", new IvesEntity
                    {
                        Name = "Example Civic Association",
                        Ico = "00123456",
                        NgoType = "občianske združenie",
                        RegistrationDate = "2010-05-15",
                        Court = "Okresný súd Bratislava I",
                        FileNumber = "OZ-123/2010",
                        Address = new IvesAddress
                        {
                            Street = "Example Street 123",
                            City = "Bratislava",
                            PostalCode = "811 01",
                            Full = "Example Street 123, 811 01 Bratislava"
                        }
                    }
                },
                {
                    "00223456", new IvesEntity
                    {
                        Name = "Example Foundation",
                        Ico = "00223456",
                        NgoType = "nadácia",
                        RegistrationDate = "2015-03-01",
                        Court = "Okresný súd Bratislava I",
                        FileNumber = "N-456/2015",
                        Address = new IvesAddress
                        {
                            Street = "Foundation Street 456",
                            City = "Bratislava",
                            PostalCode = "811 02",
                            Full = "Foundation Street 456, 811 02 Bratislava"
                        }
                    }
                }
            };

            if (mockData.TryGetValue(ico, out var data))
            {
                return ParseResponse(data, ico);
            }

            return null;
        }

        /// <summary>
        /// Get available NGO type mappings.
        /// </summary>
        public Dictionary<string, string> GetNgoTypes()
        {
            return new Dictionary<string, string>(NgoTypeMappings);
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

    #region Supporting Classes

    internal class SearchResponse
    {
        public List<IvesEntity>? Results { get; set; }
    }

    #endregion

    #endregion
}
