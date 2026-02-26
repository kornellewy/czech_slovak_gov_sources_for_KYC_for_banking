using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using UnifiedOutput;

namespace Rpo
{
    /// <summary>
    /// RPO Slovak Register of Legal Entities client.
    /// API: https://api.statistics.sk/rpo/v1
    ///
    /// API Documentation:
    /// - Managed by Statistical Office of Slovak Republic (Štatistický úrad SR)
    /// - Open Data under Creative Commons Attribution 4.0 license
    /// - No API key required for public queries
    /// - Rate limit: 100 requests/minute
    ///
    /// Search endpoint: GET /search?identifier={ico}
    /// Entity endpoint: GET /entity/{id} (uses internal RPO ID, not ICO)
    ///
    /// Usage:
    ///     var client = new RpoClient();
    ///     var result = await client.SearchByICOAsync("47559870");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Response Models

    /// <summary>
    /// RPO search response (wrapped in results).
    /// </summary>
    public class RpoSearchResponse
    {
        [JsonPropertyName("results")]
        public List<RpoSearchResult>? Results { get; set; }
    }

    /// <summary>
    /// RPO search result item.
    /// </summary>
    public class RpoSearchResult
    {
        [JsonPropertyName("id")]
        public int? Id { get; set; }

        [JsonPropertyName("identifiers")]
        public List<RpoIdentifier>? Identifiers { get; set; }

        [JsonPropertyName("fullNames")]
        public List<RpoFullName>? FullNames { get; set; }
    }

    /// <summary>
    /// RPO identifier (ICO).
    /// </summary>
    public class RpoIdentifier
    {
        [JsonPropertyName("value")]
        public string? Value { get; set; }
    }

    /// <summary>
    /// RPO full name.
    /// </summary>
    public class RpoFullName
    {
        [JsonPropertyName("value")]
        public string? Value { get; set; }
    }

    /// <summary>
    /// RPO entity response from /entity/{id}.
    /// </summary>
    public class RpoEntity
    {
        [JsonPropertyName("id")]
        public int? Id { get; set; }

        [JsonPropertyName("identifiers")]
        public List<RpoIdentifier>? Identifiers { get; set; }

        [JsonPropertyName("fullNames")]
        public List<RpoFullName>? FullNames { get; set; }

        [JsonPropertyName("legalForms")]
        public List<RpoLegalForm>? LegalForms { get; set; }

        [JsonPropertyName("establishment")]
        public string? Establishment { get; set; }

        [JsonPropertyName("addresses")]
        public List<RpoAddress>? Addresses { get; set; }

        [JsonPropertyName("statutoryBodies")]
        public List<RpoStakeholder>? StatutoryBodies { get; set; }

        [JsonPropertyName("stakeholders")]
        public List<RpoStakeholder>? Stakeholders { get; set; }
    }

    /// <summary>
    /// RPO legal form.
    /// </summary>
    public class RpoLegalForm
    {
        [JsonPropertyName("value")]
        public RpoLegalFormValue? Value { get; set; }
    }

    public class RpoLegalFormValue
    {
        [JsonPropertyName("value")]
        public string? Value { get; set; }

        [JsonPropertyName("code")]
        public string? Code { get; set; }
    }

    /// <summary>
    /// RPO address.
    /// </summary>
    public class RpoAddress
    {
        [JsonPropertyName("street")]
        public string? Street { get; set; }

        [JsonPropertyName("buildingNumber")]
        public string? BuildingNumber { get; set; }

        [JsonPropertyName("postalCodes")]
        public List<string>? PostalCodes { get; set; }

        [JsonPropertyName("municipality")]
        public RpoMunicipality? Municipality { get; set; }

        [JsonPropertyName("country")]
        public RpoCountry? Country { get; set; }
    }

    public class RpoMunicipality
    {
        [JsonPropertyName("value")]
        public string? Value { get; set; }
    }

    public class RpoCountry
    {
        [JsonPropertyName("code")]
        public string? Code { get; set; }
    }

    /// <summary>
    /// RPO stakeholder/statutory body.
    /// </summary>
    public class RpoStakeholder
    {
        [JsonPropertyName("personName")]
        public RpoPersonName? PersonName { get; set; }

        [JsonPropertyName("stakeholderType")]
        public RpoStakeholderType? StakeholderType { get; set; }
    }

    public class RpoPersonName
    {
        [JsonPropertyName("formatedName")]
        public string? FormatedName { get; set; }
    }

    public class RpoStakeholderType
    {
        [JsonPropertyName("value")]
        public string? Value { get; set; }
    }

    #endregion

    #region Client

    public class RpoClient
    {
        private const string BaseUrl = "https://api.statistics.sk/rpo/v1";
        private const string Source = "RPO_SK";
        private readonly HttpClient _httpClient;

        // RPO country code mappings (numeric to ISO 3166-1 alpha-2)
        private static readonly Dictionary<string, string> CountryCodeMappings = new()
        {
            { "703", "SK" }, // Slovak Republic
            { "203", "CZ" }, // Czech Republic
            { "040", "AT" }, // Austria
            { "276", "DE" }, // Germany
            { "380", "IT" }, // Italy
            { "348", "HU" }, // Hungary
            { "616", "PL" }, // Poland
            { "826", "GB" }, // United Kingdom
            { "840", "US" }, // United States
        };

        public RpoClient()
        {
            _httpClient = new HttpClient
            {
                Timeout = TimeSpan.FromSeconds(30)
            };
            _httpClient.DefaultRequestHeaders.Add("User-Agent", "RpoClient/1.0");
        }

        /// <summary>
        /// Search entity by ICO and return unified output format.
        /// Uses two-step API process:
        /// 1. Search endpoint to get internal RPO ID
        /// 2. Entity endpoint for full details
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            try
            {
                // Step 1: Search by identifier (ICO) to get internal ID
                var searchUrl = $"{BaseUrl}/search?identifier={ico}";
                var searchResponse = await _httpClient.GetStringAsync(searchUrl);
                var searchWrapper = JsonSerializer.Deserialize<RpoSearchResponse>(searchResponse);

                if (searchWrapper?.Results == null || searchWrapper.Results.Count == 0)
                {
                    return new UnifiedData
                    {
                        Entity = new UnifiedEntity
                        {
                            IcoRegistry = ico,
                            CompanyNameRegistry = null
                        },
                        Holders = new List<UnifiedHolder>(),
                        Metadata = new UnifiedMetadata
                        {
                            Source = Source,
                            RegisterName = OutputNormalizer.GetRegisterName(Source),
                            RegisterUrl = $"{BaseUrl}/search?identifier={ico}",
                            RetrievedAt = DateTime.UtcNow.ToString("o"),
                            IsMock = false
                        }
                    };
                }

                // Get internal ID from first result
                var internalId = searchWrapper.Results[0].Id;
                if (!internalId.HasValue)
                {
                    return null;
                }

                // Step 2: Fetch full entity details
                var entityUrl = $"{BaseUrl}/entity/{internalId}";
                var entityResponse = await _httpClient.GetStringAsync(entityUrl);
                var entity = JsonSerializer.Deserialize<RpoEntity>(entityResponse);

                if (entity == null)
                {
                    return null;
                }

                return BuildUnifiedOutput(entity, ico, isMock: false);
            }
            catch (HttpRequestException)
            {
                // Network error - use fallback mock data
                return GetFallbackMockData(ico);
            }
            catch (Exception)
            {
                // Other errors - use fallback mock data
                return GetFallbackMockData(ico);
            }
        }

        private UnifiedData BuildUnifiedOutput(RpoEntity entity, string ico, bool isMock)
        {
            // Extract ICO from identifiers
            string? icoValue = ico;
            if (entity.Identifiers != null && entity.Identifiers.Count > 0)
            {
                icoValue = entity.Identifiers[0].Value ?? ico;
            }

            // Extract company name
            string? companyName = null;
            if (entity.FullNames != null && entity.FullNames.Count > 0)
            {
                companyName = entity.FullNames[0].Value;
            }

            // Extract legal form
            string? legalForm = null;
            string? legalFormCode = null;
            if (entity.LegalForms != null && entity.LegalForms.Count > 0)
            {
                legalForm = entity.LegalForms[0].Value?.Value;
                legalFormCode = entity.LegalForms[0].Value?.Code;
            }

            // Build address
            UnifiedAddress? address = null;
            if (entity.Addresses != null && entity.Addresses.Count > 0)
            {
                address = ParseRpoAddress(entity.Addresses[0]);
            }

            // Build entity
            var unifiedEntity = new UnifiedEntity
            {
                IcoRegistry = icoValue,
                CompanyNameRegistry = companyName,
                LegalForm = legalForm,
                LegalFormCode = legalFormCode,
                Status = "active", // RPO doesn't provide status, assume active if found
                IncorporationDate = entity.Establishment,
                RegisteredAddress = address
            };

            // Build holders
            var holders = ParseHolders(entity);

            // Build metadata
            var metadata = new UnifiedMetadata
            {
                Source = Source,
                RegisterName = OutputNormalizer.GetRegisterName(Source),
                RegisterUrl = entity.Id.HasValue ? $"{BaseUrl}/entity/{entity.Id}" : null,
                RetrievedAt = DateTime.UtcNow.ToString("o"),
                IsMock = isMock
            };

            return new UnifiedData
            {
                Entity = unifiedEntity,
                Holders = holders,
                Metadata = metadata
            };
        }

        private UnifiedAddress? ParseRpoAddress(RpoAddress addr)
        {
            // Build street with building number
            string? street = null;
            if (!string.IsNullOrEmpty(addr.Street) && !string.IsNullOrEmpty(addr.BuildingNumber))
            {
                street = $"{addr.Street} {addr.BuildingNumber}";
            }
            else
            {
                street = addr.Street ?? addr.BuildingNumber;
            }

            // Get postal code
            string? postalCode = null;
            if (addr.PostalCodes != null && addr.PostalCodes.Count > 0)
            {
                postalCode = addr.PostalCodes[0];
            }

            // Get city
            string? city = addr.Municipality?.Value;

            // Map country code
            string? countryCode = null;
            if (addr.Country?.Code != null)
            {
                countryCode = MapCountryCode(addr.Country.Code);
            }

            return new UnifiedAddress
            {
                Street = street,
                City = city,
                PostalCode = postalCode,
                CountryCode = countryCode
            };
        }

        private string? MapCountryCode(string code)
        {
            if (CountryCodeMappings.TryGetValue(code, out var mapped))
            {
                return mapped;
            }

            // Already a 2-letter code?
            if (code.Length == 2)
            {
                return code.ToUpper();
            }

            return null;
        }

        private List<UnifiedHolder> ParseHolders(RpoEntity entity)
        {
            var holders = new List<UnifiedHolder>();

            // Parse statutory bodies
            if (entity.StatutoryBodies != null)
            {
                foreach (var sb in entity.StatutoryBodies)
                {
                    var holder = ParseHolder(sb, "statutory_body");
                    if (holder != null)
                    {
                        holders.Add(holder);
                    }
                }
            }

            // Parse stakeholders (shareholders)
            if (entity.Stakeholders != null)
            {
                foreach (var sh in entity.Stakeholders)
                {
                    var holder = ParseHolder(sh, "shareholder");
                    if (holder != null)
                    {
                        holders.Add(holder);
                    }
                }
            }

            return holders;
        }

        private UnifiedHolder? ParseHolder(RpoStakeholder stakeholder, string defaultRole)
        {
            var name = stakeholder.PersonName?.FormatedName;
            if (string.IsNullOrEmpty(name))
            {
                return null;
            }

            // Determine role from stakeholderType
            string role = defaultRole;
            var stakeholderTypeValue = stakeholder.StakeholderType?.Value;
            if (!string.IsNullOrEmpty(stakeholderTypeValue))
            {
                role = NormalizeRole(stakeholderTypeValue);
            }

            return new UnifiedHolder
            {
                HolderType = "individual",
                Role = role,
                Name = name
            };
        }

        private string NormalizeRole(string role)
        {
            var roleLower = role.ToLower().Trim();
            return roleLower switch
            {
                "konateľ" or "konatel" or "jednatel" or "jednateľ" => "statutory_body",
                "spoločník" or "spolocnik" or "akcionár" or "akcionar" => "shareholder",
                "dozorná rada" or "dozorna rada" => "statutory_body",
                "predstavenstvo" => "statutory_body",
                "prokurista" or "prokurist" => "procurist",
                "likvidátor" or "likvidator" => "liquidator",
                _ => roleLower
            };
        }

        private UnifiedData GetFallbackMockData(string ico)
        {
            // Fallback data for network errors only
            // Note: Banks and financial institutions may not be in RPO (they're in NBS register)
            var mockData = new Dictionary<string, Dictionary<string, object?>>
            {
                {
                    "31348262",
                    new Dictionary<string, object?>
                    {
                        ["name"] = "Wolters Kluwer SR s.r.o.",
                        ["legal_form"] = "Spoločnosť s ručením obmedzeným",
                        ["legal_form_code"] = "112",
                        ["status"] = "active",
                        ["date_registered"] = "2004-01-01"
                    }
                },
                {
                    "47559870",
                    new Dictionary<string, object?>
                    {
                        ["name"] = "ZELEX, s.r.o.",
                        ["legal_form"] = "Spoločnosť s ručením obmedzeným",
                        ["legal_form_code"] = "112",
                        ["status"] = "active",
                        ["date_registered"] = "2005-01-01"
                    }
                }
            };

            Dictionary<string, object?> data;
            if (mockData.TryGetValue(ico, out var foundData))
            {
                data = foundData;
            }
            else
            {
                data = new Dictionary<string, object?>
                {
                    ["name"] = $"Unknown Entity ({ico})",
                    ["status"] = "unknown"
                };
            }

            return new UnifiedData
            {
                Entity = new UnifiedEntity
                {
                    IcoRegistry = ico,
                    CompanyNameRegistry = data.TryGetValue("name", out var name) ? name?.ToString() : null,
                    LegalForm = data.TryGetValue("legal_form", out var lf) ? lf?.ToString() : null,
                    LegalFormCode = data.TryGetValue("legal_form_code", out var lfc) ? lfc?.ToString() : null,
                    Status = data.TryGetValue("status", out var status) ? OutputNormalizer.NormalizeStatus(status?.ToString()) : null,
                    IncorporationDate = data.TryGetValue("date_registered", out var dr) ? dr?.ToString() : null
                },
                Holders = new List<UnifiedHolder>(),
                Metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{BaseUrl}/entity/{ico}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = true // Always true for fallback data
                }
            };
        }
    }

    #endregion
}
