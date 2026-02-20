using System;
using System.Collections.Generic;
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

        [JsonPropertyName("dic")]
        public string? Dic { get; set; }

        [JsonPropertyName("financniUrad")]
        public string? FinancniUrad { get; set; }

        [JsonPropertyName("datumAktualizace")]
        public string? DatumAktualizace { get; set; }

        [JsonPropertyName("czNace2008")]
        public List<string>? CzNace2008 { get; set; }

        [JsonPropertyName("czNace")]
        public List<string>? CzNace { get; set; }

        [JsonPropertyName("seznamRegistraci")]
        public Dictionary<string, string>? SeznamRegistraci { get; set; }

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
        private DateTime _lastRequestTime = DateTime.MinValue;
        private readonly object _lockObject = new();

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
        }

        /// <summary>
        /// Search company by ICO and return unified output format.
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            await ApplyRateLimitAsync();

            var url = $"{BaseUrl}/{ico.Trim()}";

            try
            {
                var response = await _httpClient.GetStringAsync(url);
                var aresResponse = JsonSerializer.Deserialize<AresResponse>(response);

                if (aresResponse?.Kod != null && aresResponse.Kod != "OK")
                {
                    return null;
                }

                return MapToUnifiedOutput(aresResponse!);
            }
            catch (HttpRequestException)
            {
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

            // Determine VAT status
            string? vatStatus = null;
            if (response.SeznamRegistraci != null && response.SeznamRegistraci.TryGetValue("dph", out var dph))
            {
                vatStatus = dph == "ano" ? "active" : "inactive";
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
