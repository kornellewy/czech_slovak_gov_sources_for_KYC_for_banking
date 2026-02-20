using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using UnifiedOutput;
using System.Text.Json;
using System.Linq;

namespace Rpvs
{
    /// <summary>
    /// RPVS Slovak Register of Public Sector Partners (UBO) client.
    /// API: https://rpvs.gov.sk/opendatav2/PartneriVerejnehoSektora
    ///
    /// OData endpoint format: $filter=Ico eq 'ICO'
    /// Provides public data without API key.
    ///
    /// Usage:
    ///     var client = new RpvsClient();
    ///     var result = await client.SearchByICOAsync("35763491");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region OData Response Models

    public class RpvsODataResponse
    {
        public List<RpvsEntity> Value { get; set; } = new();
    }

    public class RpvsEntity
    {
        public string? Ico { get; set; }
        public string? ObchodneMeno { get; set; }  // Trade name
        public string? FormaOsoby { get; set; }   // Legal form
        public string? PlatnostOd { get; set; }   // Valid from
        public string? PlatnostDo { get; set; }   // Valid to (null = active)
    }

    #endregion

    #region Client

    public class RpvsClient : IDisposable
    {
        private const string BaseUrl = "https://rpvs.gov.sk/opendatav2";
        private const string ODataEndpoint = "https://rpvs.gov.sk/opendatav2/PartneriVerejnehoSektora";
        private const string Source = "RPVS_SK";

        private static readonly HttpClient httpClient = new()
        {
            Timeout = TimeSpan.FromSeconds(30)
        };

        // Mock database for fallback when API is unavailable
        private static readonly Dictionary<string, (string CompanyName, List<Dictionary<string, object?>> Holders)> MockDatabase = new()
        {
            {
                "35763491",
                ("Slovenská sporiteľňa, a.s.", new List<Dictionary<string, object?>>
                {
                    new()
                    {
                        ["name"] = "Erste Group Bank AG",
                        ["type"] = "entity",
                        ["role"] = "beneficial_owner",
                        ["ownership_percentage"] = 100.0,
                        ["voting_rights"] = 100.0,
                        ["citizenship"] = "AT",
                        ["address"] = new Dictionary<string, object?>
                        {
                            ["city"] = "Vienna",
                            ["country"] = "Austria"
                        }
                    }
                })
            },
            {
                "31328356",
                ("Všeobecná úverová banka, a.s.", new List<Dictionary<string, object?>>
                {
                    new()
                    {
                        ["name"] = "Intesa Sanpaolo S.p.A.",
                        ["type"] = "entity",
                        ["role"] = "beneficial_owner",
                        ["ownership_percentage"] = 94.49,
                        ["voting_rights"] = 94.49,
                        ["citizenship"] = "IT",
                        ["address"] = new Dictionary<string, object?>
                        {
                            ["city"] = "Milan",
                            ["country"] = "Italy"
                        }
                    }
                })
            },
            {
                "44103755",
                ("Slovak Telekom, a.s.", new List<Dictionary<string, object?>>
                {
                    new()
                    {
                        ["name"] = "Deutsche Telekom AG",
                        ["type"] = "entity",
                        ["role"] = "beneficial_owner",
                        ["ownership_percentage"] = 51.0,
                        ["voting_rights"] = 51.0,
                        ["citizenship"] = "DE",
                        ["address"] = new Dictionary<string, object?>
                        {
                            ["city"] = "Bonn",
                            ["country"] = "Germany"
                        }
                    }
                })
            }
        };

        /// <summary>
        /// Search UBO data by ICO using OData API.
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            try
            {
                // OData filter syntax: $filter=Ico eq '35763491'
                string url = $"{ODataEndpoint}?$filter=Ico eq '{ico}'";

                var response = await httpClient.GetAsync(url);
                if (response.IsSuccessStatusCode)
                {
                    var json = await response.Content.ReadAsStringAsync();
                    var odataResponse = JsonSerializer.Deserialize<RpvsODataResponse>(json,
                        new JsonSerializerOptions { PropertyNameCaseInsensitive = true });

                    if (odataResponse?.Value != null && odataResponse.Value.Count > 0)
                    {
                        var entity = odataResponse.Value[0];
                        return ParseODataResponse(entity, ico);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"RPVS API request failed: {ex.Message}");
            }

            // Fall back to mock data
            return GetMockData(ico);
        }

        private UnifiedData ParseODataResponse(RpvsEntity entity, string ico)
        {
            // Determine status from PlatnostDo (validity to date)
            string status = "active";
            if (!string.IsNullOrEmpty(entity.PlatnostDo))
            {
                if (DateTime.TryParse(entity.PlatnostDo, out var expiry) && expiry < DateTime.UtcNow)
                {
                    status = "cancelled";
                }
            }

            return new UnifiedData
            {
                Entity = new UnifiedEntity
                {
                    IcoRegistry = entity.Ico ?? ico,
                    CompanyNameRegistry = entity.ObchodneMeno,
                    LegalForm = entity.FormaOsoby,
                    Status = status
                },
                Holders = new List<UnifiedHolder>(),  // UBO data may require separate endpoint
                Metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{ODataEndpoint}?$filter=Ico eq '{ico}'",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = false
                }
            };
        }

        private UnifiedData? GetMockData(string ico)
        {
            if (MockDatabase.TryGetValue(ico, out var data))
            {
                var holders = new List<UnifiedHolder>();
                foreach (var holderData in data.Holders)
                {
                    holders.Add(BuildHolder(holderData));
                }

                return new UnifiedData
                {
                    Entity = new UnifiedEntity
                    {
                        IcoRegistry = ico,
                        CompanyNameRegistry = data.CompanyName
                    },
                    Holders = holders,
                    Metadata = new UnifiedMetadata
                    {
                        Source = Source,
                        RegisterName = OutputNormalizer.GetRegisterName(Source),
                        RegisterUrl = $"{ODataEndpoint}?$filter=Ico eq '{ico}'",
                        RetrievedAt = DateTime.UtcNow.ToString("o"),
                        IsMock = true
                    }
                };
            }

            return new UnifiedData
            {
                Entity = new UnifiedEntity
                {
                    IcoRegistry = ico,
                    CompanyNameRegistry = $"Unknown Entity ({ico})"
                },
                Holders = new List<UnifiedHolder>(),
                Metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{ODataEndpoint}?$filter=Ico eq '{ico}'",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = true
                }
            };
        }

        private UnifiedHolder BuildHolder(Dictionary<string, object?> data)
        {
            var name = data.TryGetValue("name", out var nameObj) ? nameObj?.ToString() : "";
            var holderType = OutputNormalizer.DetectHolderType(data);
            var citizenship = data.TryGetValue("citizenship", out var citObj) ? citObj?.ToString() : null;

            string? jurisdiction = null;
            if (holderType == "entity")
            {
                if (data.TryGetValue("address", out var addrObj) && addrObj is Dictionary<string, object?> addr)
                {
                    if (addr.TryGetValue("country", out var countryObj))
                    {
                        jurisdiction = OutputNormalizer.NormalizeCountryCode(countryObj?.ToString());
                    }
                }
                jurisdiction ??= OutputNormalizer.NormalizeCountryCode(citizenship);
            }

            UnifiedAddress? address = null;
            if (data.TryGetValue("address", out var addressObj) && addressObj is Dictionary<string, object?> addressData)
            {
                address = new UnifiedAddress
                {
                    City = addressData.TryGetValue("city", out var city) ? city?.ToString() : null,
                    Country = addressData.TryGetValue("country", out var country) ? country?.ToString() : null,
                    CountryCode = addressData.TryGetValue("country", out var c) ? OutputNormalizer.NormalizeCountryCode(c?.ToString()) : null
                };
            }

            double ownershipPct = 0;
            if (data.TryGetValue("ownership_percentage", out var ownObj) && ownObj != null)
            {
                _ = double.TryParse(ownObj.ToString(), out ownershipPct);
            }

            double? votingRights = null;
            if (data.TryGetValue("voting_rights", out var voteObj) && voteObj != null)
            {
                if (double.TryParse(voteObj.ToString(), out var vr))
                {
                    votingRights = vr;
                }
            }

            return new UnifiedHolder
            {
                HolderType = holderType,
                Role = "beneficial_owner",
                Name = name,
                Jurisdiction = jurisdiction,
                Citizenship = OutputNormalizer.NormalizeCountryCode(citizenship),
                Residency = OutputNormalizer.NormalizeCountryCode(citizenship),
                Address = address,
                OwnershipPctDirect = ownershipPct,
                VotingRightsPct = votingRights
            };
        }

        public void Dispose()
        {
            httpClient?.Dispose();
        }
    }

    #endregion
}
