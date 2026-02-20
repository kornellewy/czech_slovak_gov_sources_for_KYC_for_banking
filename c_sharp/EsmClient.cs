using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnifiedOutput;

namespace Esm
{
    /// <summary>
    /// ESM Czech Register of Beneficial Owners client.
    /// Website: https://issm.justice.cz
    ///
    /// IMPORTANT: This API is RESTRICTED and requires AML certification.
    /// This is a PLACEHOLDER implementation with mock data only.
    /// Output: UnifiedData? format with entity, holders, metadata sections.
    ///
    /// Usage:
    ///     var client = new EsmClient();
    ///     var result = await client.SearchByICOAsync("06649114");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Client

    public class EsmClient
    {
        private const string BaseUrl = "https://issm.justice.cz";
        private const string Source = "ESM_CZ";

        public static readonly EsmAccessRequirements AccessRequirements = new()
        {
            Qualification = "AML obligated person (bank, notary, auditor, etc.)",
            Registration = "Required registration at issm.justice.cz",
            ApiKey = "API key required for access",
            Website = "https://issm.justice.cz",
            LegalBasis = "Zákon o evidenci skutečných majitelů"
        };

        // Mock database with raw data
        private static readonly Dictionary<string, (string CompanyName, List<Dictionary<string, object?>> Holders)> MockDatabase = new()
        {
            {
                "06649114",
                ("Prusa Research a.s.", new List<Dictionary<string, object?>>
                {
                    new()
                    {
                        ["name"] = "Josef Průša",
                        ["type"] = "individual",
                        ["role"] = "beneficial_owner",
                        ["ownership_percentage"] = 100.0,
                        ["voting_rights"] = 100.0,
                        ["birth_date"] = "1990-05-24",
                        ["citizenship"] = "CZ",
                        ["address"] = new Dictionary<string, object?>
                        {
                            ["city"] = "Praha",
                            ["country"] = "Česká republika"
                        }
                    }
                })
            },
            {
                "00216305",
                ("Česká pošta, s.p.", new List<Dictionary<string, object?>>
                {
                    new()
                    {
                        ["name"] = "Česká republika",
                        ["type"] = "entity",
                        ["role"] = "beneficial_owner",
                        ["ownership_percentage"] = 100.0,
                        ["voting_rights"] = 100.0,
                        ["citizenship"] = "CZ"
                    }
                })
            },
            {
                "00006947",
                ("Ministerstvo financí", new List<Dictionary<string, object?>>
                {
                    new()
                    {
                        ["name"] = "Česká republika",
                        ["type"] = "entity",
                        ["role"] = "beneficial_owner",
                        ["ownership_percentage"] = 100.0
                    }
                })
            }
        };

        /// <summary>
        /// Search beneficial owners by ICO and return unified output format.
        /// </summary>
        public Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            if (MockDatabase.TryGetValue(ico, out var data))
            {
                var output = BuildUnifiedOutput(ico, data.CompanyName, data.Holders, isMock: true);
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
                    RegisterUrl = $"{BaseUrl}/ubo/{ico}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = true
                }
            };

            return Task.FromResult<UnifiedData?>(emptyOutput);
        }

        /// <summary>
        /// Legacy method - Get beneficial owners (returns unified format).
        /// </summary>
        public async Task<UnifiedData?> GetBeneficialOwnersAsync(string ico)
        {
            return await SearchByICOAsync(ico);
        }

        public EsmAccessRequirements GetAccessRequirements()
        {
            return AccessRequirements;
        }

        private UnifiedData BuildUnifiedOutput(string ico, string companyName, List<Dictionary<string, object?>> holdersData, bool isMock)
        {
            var holders = new List<UnifiedHolder>();

            foreach (var holderData in holdersData)
            {
                holders.Add(BuildHolder(holderData));
            }

            return new UnifiedData
            {
                Entity = new UnifiedEntity
                {
                    IcoRegistry = ico,
                    CompanyNameRegistry = companyName
                },
                Holders = holders,
                Metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{BaseUrl}/ubo/{ico}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = isMock
                }
            };
        }

        private UnifiedHolder BuildHolder(Dictionary<string, object?> data)
        {
            var name = data.TryGetValue("name", out var nameObj) ? nameObj?.ToString() : "";
            var holderType = OutputNormalizer.DetectHolderType(data);

            // Get citizenship
            var citizenship = data.TryGetValue("citizenship", out var citObj) ? citObj?.ToString() : null;

            // Get jurisdiction for entities
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

            // Build address
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

            // Get ownership percentage
            double ownershipPct = 0;
            if (data.TryGetValue("ownership_percentage", out var ownObj) && ownObj != null)
            {
                _ = double.TryParse(ownObj.ToString(), out ownershipPct);
            }

            // Get voting rights
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
                DateOfBirth = data.TryGetValue("birth_date", out var bd) ? bd?.ToString() : null,
                Residency = OutputNormalizer.NormalizeCountryCode(citizenship),
                Address = address,
                OwnershipPctDirect = ownershipPct,
                VotingRightsPct = votingRights
            };
        }
    }

    /// <summary>
    /// ESM access requirements information.
    /// </summary>
    public class EsmAccessRequirements
    {
        public string Qualification { get; set; } = "";
        public string Registration { get; set; } = "";
        public string ApiKey { get; set; } = "";
        public string Website { get; set; } = "";
        public string LegalBasis { get; set; } = "";
    }

    #endregion
}
