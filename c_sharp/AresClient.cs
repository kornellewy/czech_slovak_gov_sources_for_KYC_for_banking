using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using UnifiedOutput;

namespace Ares
{
    /// <summary>
    /// ARES (Register of Economic Subjects) Czech company registry client.
    /// API Documentation: https://ares.gov.cz/swagger-ui/
    ///
    /// Output: UnifiedOutput format with entity, holders, tax_info, metadata sections.
    ///
    /// Usage:
    ///     var client = new AresClient();
    ///     var result = await client.SearchByICOAsync("00006947");
    ///     Console.WriteLine(result.ToJson());
    ///
    ///     // With sub-source information
    ///     var result = await client.SearchByICOAsync("00006947", includeSubsource: true);
    ///     Console.WriteLine(result.Subsource?.ActiveCount);
    /// </summary>

    #region Data Models

    /// <summary>
    /// Root response from ARES API.
    /// </summary>
    public class AresResponse
    {
        [JsonPropertyName("ico")]
        public string? Ico { get; set; }

        [JsonPropertyName("obchodniJmeno")]
        public string? ObchodniJmeno { get; set; }

        [JsonPropertyName("sidlo")]
        public AresAddress? Sidlo { get; set; }

        [JsonPropertyName("pravniForma")]
        public string? PravniForma { get; set; }

        [JsonPropertyName("pravniFormaKod")]
        public string? PravniFormaKod { get; set; }

        [JsonPropertyName("pravniFormaRos")]
        public string? PravniFormaRos { get; set; }

        [JsonPropertyName("dic")]
        public string? Dic { get; set; }

        [JsonPropertyName("financniUrad")]
        public string? FinancniUrad { get; set; }

        [JsonPropertyName("datumVzniku")]
        public string? DatumVzniku { get; set; }

        [JsonPropertyName("datumAktualizace")]
        public string? DatumAktualizace { get; set; }

        [JsonPropertyName("icoId")]
        public string? IcoId { get; set; }

        [JsonPropertyName("czNace2008")]
        public List<string>? CzNace2008 { get; set; }

        [JsonPropertyName("czNace")]
        public List<string>? CzNace { get; set; }

        [JsonPropertyName("seznamRegistraci")]
        public Dictionary<string, string>? SeznamRegistraci { get; set; }

        [JsonPropertyName("dalsiUdaje")]
        public List<AresDalsiUdaje>? DalsiUdaje { get; set; }

        [JsonPropertyName("kod")]
        public string? Kod { get; set; }

        [JsonPropertyName("popis")]
        public string? Popis { get; set; }
    }

    /// <summary>
    /// Address from ARES API.
    /// </summary>
    public class AresAddress
    {
        [JsonPropertyName("nazevUlice")]
        public string? NazevUlice { get; set; }

        [JsonPropertyName("cisloDomovni")]
        public int? CisloDomovni { get; set; }

        [JsonPropertyName("cisloOrientacni")]
        public JsonElement CisloOrientacniJson { get; set; }

        [JsonIgnore]
        public string? CisloOrientacni
        {
            get
            {
                if (CisloOrientacniJson.ValueKind == JsonValueKind.String)
                    return CisloOrientacniJson.GetString();
                if (CisloOrientacniJson.ValueKind == JsonValueKind.Number)
                    return CisloOrientacniJson.GetInt32().ToString();
                return null;
            }
        }

        [JsonPropertyName("nazevObce")]
        public string? NazevObce { get; set; }

        [JsonPropertyName("nazevMestskeCasti")]
        public string? NazevMestskeCasti { get; set; }

        [JsonPropertyName("psc")]
        public JsonElement PscJson { get; set; }

        [JsonIgnore]
        public string? Psc
        {
            get
            {
                if (PscJson.ValueKind == JsonValueKind.String)
                    return PscJson.GetString();
                if (PscJson.ValueKind == JsonValueKind.Number)
                    return PscJson.GetInt32().ToString();
                return null;
            }
        }

        [JsonPropertyName("nazevStatu")]
        public string? NazevStatu { get; set; }
    }

    /// <summary>
    /// Additional data from sub-sources (dalsiUdaje).
    /// </summary>
    public class AresDalsiUdaje
    {
        [JsonPropertyName("datovyZdroj")]
        public string? DatovyZdroj { get; set; }

        [JsonPropertyName("obchodniJmeno")]
        public List<AresObchodniJmenoEntry>? ObchodniJmeno { get; set; }

        [JsonPropertyName("sidlo")]
        public List<AresSidloEntry>? Sidlo { get; set; }

        [JsonPropertyName("spisovaZnacka")]
        public string? SpisovaZnacka { get; set; }

        [JsonPropertyName("pravniForma")]
        public string? PravniForma { get; set; }

        [JsonPropertyName("datumZapisu")]
        public string? DatumZapisu { get; set; }

        [JsonPropertyName("datumVymazu")]
        public string? DatumVymazu { get; set; }
    }

    /// <summary>
    /// Company name entry in dalsiUdaje.
    /// </summary>
    public class AresObchodniJmenoEntry
    {
        [JsonPropertyName("obchodniJmeno")]
        public string? ObchodniJmeno { get; set; }

        [JsonPropertyName("primarniZaznam")]
        public bool? PrimarniZaznam { get; set; }
    }

    /// <summary>
    /// Address entry in dalsiUdaje.
    /// </summary>
    public class AresSidloEntry
    {
        [JsonPropertyName("sidlo")]
        public AresAddress? Sidlo { get; set; }

        [JsonPropertyName("primarniZaznam")]
        public bool? PrimarniZaznam { get; set; }
    }

    #endregion

    #region Sub-source Models

    /// <summary>
    /// Sub-source information extracted from ARES response.
    /// </summary>
    public class AresSubsource
    {
        [JsonPropertyName("registrations")]
        public Dictionary<string, AresRegistrationStatus>? Registrations { get; set; }

        [JsonPropertyName("additional_data")]
        public Dictionary<string, AresAdditionalData>? AdditionalData { get; set; }

        [JsonPropertyName("active_count")]
        public int ActiveCount { get; set; }

        [JsonPropertyName("ros_legal_form")]
        public string? RosLegalForm { get; set; }
    }

    /// <summary>
    /// Registration status for a sub-source.
    /// </summary>
    public class AresRegistrationStatus
    {
        [JsonPropertyName("status")]
        public string? Status { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("name")]
        public string? Name { get; set; }

        [JsonPropertyName("english_name")]
        public string? EnglishName { get; set; }
    }

    /// <summary>
    /// Additional data from a sub-source.
    /// </summary>
    public class AresAdditionalData
    {
        [JsonPropertyName("company_name")]
        public string? CompanyName { get; set; }

        [JsonPropertyName("address")]
        public UnifiedAddress? Address { get; set; }

        [JsonPropertyName("legal_form")]
        public string? LegalForm { get; set; }

        [JsonPropertyName("file_reference")]
        public string? FileReference { get; set; }

        [JsonPropertyName("registration_date")]
        public string? RegistrationDate { get; set; }

        [JsonPropertyName("deletion_date")]
        public string? DeletionDate { get; set; }
    }

    #endregion

    #region Client

    /// <summary>
    /// ARES Czech company registry client with unified output format.
    /// </summary>
    public class AresClient : IDisposable
    {
        private const string BaseUrl = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty";
        private const int RequestsPerMinute = 500;

        private readonly HttpClient _httpClient;
        private readonly SemaphoreSlim _rateLimiter;
        private readonly ScraperLogger _logger;
        private DateTime _lastRequestTime = DateTime.MinValue;
        private readonly object _lockObject = new();

        // Sub-source definitions
        private static readonly Dictionary<string, (string Name, string English)> Subsources = new()
        {
            { "RZP", ("Rejstřík osob", "Commercial Register (Justice.cz)") },
            { "ROS", ("RES", "Resident Income Tax") },
            { "VR", ("VR", "Vermont Register (Real Estate)") },
            { "RES", ("RES", "Resident Income Tax") },
            { "DPH", ("DPH", "VAT Register") },
            { "RPSH", ("RPSH", "Statistical Register") },
            { "SD", ("SD", "Tax Debts Register") },
            { "IR", ("IR", "Income Tax Register") },
            { "RS", ("RS", "Synonyms Register") },
            { "NRPZS", ("NRPZS", "Insolvency Register") },
            { "RED", ("RED", "Register of Entrepreneurs") },
            { "SZR", ("SZR", "Unified Agricultural Register") },
            { "Monitor", ("Monitor", "Monitoring register") },
        };

        public AresClient()
        {
            var handler = new HttpClientHandler
            {
                AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate
            };

            _httpClient = new HttpClient(handler)
            {
                Timeout = TimeSpan.FromSeconds(30)
            };

            _httpClient.DefaultRequestHeaders.Add("User-Agent", "BankingScraper/1.0");
            _httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));

            _rateLimiter = new SemaphoreSlim(1, 1);
            _logger = new ScraperLogger("ARES", enableDebug: false);
            _logger.Info($"ARES Client initialized (rate limit: {RequestsPerMinute} req/min)");
        }

        /// <summary>
        /// Search company by ICO and return unified output format.
        /// </summary>
        /// <param name="ico">Czech company identification number (8 digits)</param>
        /// <param name="includeSubsource">Whether to include sub-source registration details</param>
        public async Task<UnifiedData?> SearchByICOAsync(string ico, bool includeSubsource = false)
        {
            _logger.LogSearchStart(ico?.Trim(), "by_ICO");
            await ApplyRateLimitAsync();

            var url = $"{BaseUrl}/{ico.Trim()}";

            try
            {
                var stopwatch = Stopwatch.StartNew();

                _logger.LogRequest("GET", url);

                var response = await _httpClient.GetStringAsync(url);
                var aresResponse = JsonSerializer.Deserialize<AresResponse>(response);

                stopwatch.Stop();
                _logger.LogResponse(url, 200, stopwatch.ElapsedMilliseconds);

                if (aresResponse?.Kod != null && aresResponse.Kod != "OK")
                {
                    _logger.Warning($"No entity found with IČO: {ico} - {aresResponse.Popis}");
                    return null;
                }

                _logger.Info($"Found entity for IČO {ico}: {aresResponse.ObchodniJmeno}");

                var result = MapToUnifiedOutput(aresResponse!);

                if (includeSubsource && result != null)
                {
                    _logger.Debug("Extracting sub-source data");
                    result.Subsource = ExtractSubsource(aresResponse!);

                    if (result.Subsource is AresSubsource subsource)
                    {
                        _logger.Info($"Sub-sources: {subsource.ActiveCount} active registries");
                    }
                }

                _logger.LogSearchComplete(1, ico);

                return result;
            }
            catch (HttpRequestException ex)
            {
                _logger.LogError("SearchByICO", ex, new { ico });
                return null;
            }
        }

        private UnifiedData? MapToUnifiedOutput(AresResponse response)
        {
            if (response == null) return null;

            var address = response.Sidlo != null ? new UnifiedAddress
            {
                Street = response.Sidlo.NazevUlice,
                City = response.Sidlo.NazevObce,
                PostalCode = response.Sidlo.Psc,
                Country = response.Sidlo.NazevStatu,
                CountryCode = OutputNormalizer.NormalizeCountryCode(response.Sidlo.NazevStatu),
                FullAddress = BuildFullAddress(response.Sidlo)
            } : null;

            // Determine VAT status from stavZdrojeDph (not dph)
            string? vatStatus = null;
            if (response.SeznamRegistraci != null)
            {
                foreach (var kvp in response.SeznamRegistraci)
                {
                    if (kvp.Key.Equals("stavZdrojeDph", StringComparison.OrdinalIgnoreCase) ||
                        kvp.Key.Equals("Dph", StringComparison.OrdinalIgnoreCase))
                    {
                        vatStatus = kvp.Value == "AKTIVNI" ? "active" : "inactive";
                        break;
                    }
                }
            }

            var entity = new UnifiedEntity
            {
                IcoRegistry = response.Ico,
                CompanyNameRegistry = response.ObchodniJmeno,
                LegalForm = response.PravniForma,
                LegalFormCode = response.PravniFormaKod,
                Status = "active",
                RegisteredAddress = address,
                NaceCodes = response.CzNace2008 ?? response.CzNace,
                VatId = response.Dic,
                TaxId = response.Dic
            };

            var taxInfo = new UnifiedTaxInfo
            {
                VatId = response.Dic,
                VatStatus = vatStatus,
                TaxId = response.Dic
            };

            var metadata = new UnifiedMetadata
            {
                Source = "ARES_CZ",
                RegisterName = OutputNormalizer.GetRegisterName("ARES_CZ"),
                RegisterUrl = $"{BaseUrl}/{response.Ico}",
                RetrievedAt = DateTime.UtcNow.ToString("o"),
                IsMock = false
            };

            return new UnifiedData
            {
                Entity = entity,
                Holders = new List<UnifiedHolder>(),
                TaxInfo = taxInfo,
                Metadata = metadata
            };
        }

        /// <summary>
        /// Extract sub-source registration information from ARES response.
        /// </summary>
        private AresSubsource ExtractSubsource(AresResponse response)
        {
            var subsource = new AresSubsource
            {
                Registrations = new Dictionary<string, AresRegistrationStatus>(),
                AdditionalData = new Dictionary<string, AresAdditionalData>(),
                ActiveCount = 0,
                RosLegalForm = response.PravniFormaRos
            };

            // Extract seznamRegistraci (sub-source statuses)
            if (response.SeznamRegistraci != null)
            {
                foreach (var kvp in response.SeznamRegistraci)
                {
                    var key = kvp.Key;
                    var value = kvp.Value;

                    // Remove 'stavZdroje' prefix for cleaner keys
                    var cleanKey = key.Replace("stavZdroje", "");
                    var isActive = value == "AKTIVNI";

                    var status = new AresRegistrationStatus
                    {
                        Status = value,
                        IsActive = isActive
                    };

                    // Add name information if available
                    if (Subsources.TryGetValue(cleanKey, out var info))
                    {
                        status.Name = info.Name;
                        status.EnglishName = info.English;
                    }

                    subsource.Registrations[cleanKey] = status;

                    if (isActive)
                    {
                        subsource.ActiveCount++;
                    }
                }
            }

            // Extract dalsiUdaje (detailed data from sub-sources)
            if (response.DalsiUdaje != null)
            {
                foreach (var sourceData in response.DalsiUdaje)
                {
                    var source = sourceData.DatovyZdroj;
                    if (string.IsNullOrEmpty(source)) continue;

                    var additional = new AresAdditionalData();

                    // Extract company name
                    if (sourceData.ObchodniJmeno != null && sourceData.ObchodniJmeno.Count > 0)
                    {
                        additional.CompanyName = sourceData.ObchodniJmeno[0]?.ObchodniJmeno;
                    }

                    // Extract address
                    if (sourceData.Sidlo != null && sourceData.Sidlo.Count > 0 && sourceData.Sidlo[0]?.Sidlo != null)
                    {
                        var addr = sourceData.Sidlo[0].Sidlo;
                        additional.Address = new UnifiedAddress
                        {
                            Street = addr.NazevUlice,
                            City = addr.NazevObce,
                            PostalCode = addr.Psc,
                            Country = addr.NazevStatu
                        };
                    }

                    // Extract other fields
                    additional.LegalForm = sourceData.PravniForma;
                    additional.FileReference = sourceData.SpisovaZnacka;
                    additional.RegistrationDate = sourceData.DatumZapisu;
                    additional.DeletionDate = sourceData.DatumVymazu;

                    subsource.AdditionalData[source] = additional;
                }
            }

            return subsource;
        }

        private string? BuildFullAddress(AresAddress addr)
        {
            var parts = new List<string>();

            if (!string.IsNullOrEmpty(addr.NazevUlice))
            {
                var street = addr.NazevUlice;
                if (addr.CisloDomovni.HasValue)
                {
                    street += $" {addr.CisloDomovni}";
                    if (!string.IsNullOrEmpty(addr.CisloOrientacni))
                    {
                        street += $"/{addr.CisloOrientacni}";
                    }
                }
                parts.Add(street);
            }

            if (!string.IsNullOrEmpty(addr.Psc))
            {
                var pscStr = addr.Psc;
                var formattedPsc = pscStr.Length == 5 ? $"{pscStr[..3]} {pscStr[3..]}" : pscStr;

                if (!string.IsNullOrEmpty(addr.NazevObce))
                {
                    parts.Add($"{formattedPsc} {addr.NazevObce}");
                }
                else
                {
                    parts.Add(formattedPsc);
                }
            }
            else if (!string.IsNullOrEmpty(addr.NazevObce))
            {
                parts.Add(addr.NazevObce);
            }

            return string.Join(", ", parts);
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
