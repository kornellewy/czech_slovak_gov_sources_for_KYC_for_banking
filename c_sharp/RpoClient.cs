using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnifiedOutput;

namespace Rpo
{
    /// <summary>
    /// RPO Slovak Register of Legal Entities client.
    /// API: https://api.statistics.sk/rpo/v1
    ///
    /// Note: API parameter format needs discovery. Provides mock data fallback.
    /// Output: UnifiedData? format with entity, metadata sections.
    ///
    /// Usage:
    ///     var client = new RpoClient();
    ///     var result = await client.SearchByICOAsync("35763491");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Client

    public class RpoClient
    {
        private const string BaseUrl = "https://api.statistics.sk/rpo/v1";
        private const string Source = "RPO_SK";

        // Mock database with raw data
        private static readonly Dictionary<string, Dictionary<string, object?>> MockDatabase = new()
        {
            {
                "35763491",
                new Dictionary<string, object?>
                {
                    ["name"] = "Slovenská sporiteľňa, a.s.",
                    ["legal_form"] = "Akciová spoločnosť",
                    ["legal_form_code"] = "112",
                    ["status"] = "active",
                    ["date_registered"] = "1991-01-01",
                    ["address"] = new Dictionary<string, object?>
                    {
                        ["street"] = "Tomášikova 48",
                        ["city"] = "Bratislava",
                        ["postal_code"] = "832 37",
                        ["country"] = "Slovensko",
                        ["country_code"] = "SK",
                        ["full_address"] = "Tomášikova 48, 832 37 Bratislava"
                    }
                }
            },
            {
                "31328356",
                new Dictionary<string, object?>
                {
                    ["name"] = "Všeobecná úverová banka, a.s.",
                    ["legal_form"] = "Akciová spoločnosť",
                    ["status"] = "active",
                    ["address"] = new Dictionary<string, object?>
                    {
                        ["city"] = "Bratislava",
                        ["country"] = "Slovensko",
                        ["country_code"] = "SK"
                    }
                }
            },
            {
                "44103755",
                new Dictionary<string, object?>
                {
                    ["name"] = "Slovak Telekom, a.s.",
                    ["legal_form"] = "Akciová spoločnosť",
                    ["status"] = "active",
                    ["address"] = new Dictionary<string, object?>
                    {
                        ["city"] = "Bratislava",
                        ["country"] = "Slovensko",
                        ["country_code"] = "SK"
                    }
                }
            },
            {
                "36246621",
                new Dictionary<string, object?>
                {
                    ["name"] = "Doprastav, a.s.",
                    ["legal_form"] = "Akciová spoločnosť",
                    ["status"] = "active",
                    ["address"] = new Dictionary<string, object?>
                    {
                        ["city"] = "Bratislava",
                        ["country"] = "Slovensko",
                        ["country_code"] = "SK"
                    }
                }
            }
        };

        /// <summary>
        /// Search entity by ICO and return unified output format.
        /// </summary>
        public Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            if (MockDatabase.TryGetValue(ico, out var data))
            {
                var output = BuildUnifiedOutput(ico, data, isMock: true);
                return Task.FromResult<UnifiedData?>(output);
            }

            // Return basic output for unknown ICOs
            var emptyOutput = new UnifiedData
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
                    RegisterUrl = $"{BaseUrl}/entity/{ico}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = true
                }
            };

            return Task.FromResult<UnifiedData?>(emptyOutput);
        }

        private UnifiedData BuildUnifiedOutput(string ico, Dictionary<string, object?> data, bool isMock)
        {
            // Build address
            UnifiedAddress? address = null;
            if (data.TryGetValue("address", out var addressObj) && addressObj is Dictionary<string, object?> addressData)
            {
                address = new UnifiedAddress
                {
                    Street = addressData.TryGetValue("street", out var street) ? street?.ToString() : null,
                    City = addressData.TryGetValue("city", out var city) ? city?.ToString() : null,
                    PostalCode = addressData.TryGetValue("postal_code", out var pc) ? pc?.ToString() : null,
                    Country = addressData.TryGetValue("country", out var country) ? country?.ToString() : null,
                    CountryCode = addressData.TryGetValue("country_code", out var cc) ? cc?.ToString() : null,
                    FullAddress = addressData.TryGetValue("full_address", out var fa) ? fa?.ToString() : null
                };
            }

            var entity = new UnifiedEntity
            {
                IcoRegistry = ico,
                CompanyNameRegistry = data.TryGetValue("name", out var name) ? name?.ToString() : null,
                LegalForm = data.TryGetValue("legal_form", out var lf) ? lf?.ToString() : null,
                LegalFormCode = data.TryGetValue("legal_form_code", out var lfc) ? lfc?.ToString() : null,
                Status = data.TryGetValue("status", out var status) ? OutputNormalizer.NormalizeStatus(status?.ToString()) : null,
                IncorporationDate = data.TryGetValue("date_registered", out var dr) ? dr?.ToString() : null,
                RegisteredAddress = address
            };

            var metadata = new UnifiedMetadata
            {
                Source = Source,
                RegisterName = OutputNormalizer.GetRegisterName(Source),
                RegisterUrl = $"{BaseUrl}/entity/{ico}",
                RetrievedAt = DateTime.UtcNow.ToString("o"),
                IsMock = isMock
            };

            return new UnifiedData
            {
                Entity = entity,
                Holders = new List<UnifiedHolder>(),
                Metadata = metadata
            };
        }
    }

    #endregion
}
