using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace UnifiedOutput
{
    /// <summary>
    /// Unified output format normalizer for all scrapers.
    /// Provides standardized data structures and normalization functions
    /// to ensure consistent output format across all scrapers.
    /// </summary>

    #region Data Models

    /// <summary>
    /// Standardized address structure.
    /// </summary>
    public class UnifiedAddress
    {
        [JsonPropertyName("street")]
        public string? Street { get; set; }

        [JsonPropertyName("city")]
        public string? City { get; set; }

        [JsonPropertyName("postal_code")]
        public string? PostalCode { get; set; }

        [JsonPropertyName("country")]
        public string? Country { get; set; }

        [JsonPropertyName("country_code")]
        public string? CountryCode { get; set; }

        [JsonPropertyName("full_address")]
        public string? FullAddress { get; set; }
    }

    /// <summary>
    /// Unified entity/company information.
    /// </summary>
    public class UnifiedEntity
    {
        [JsonPropertyName("ico_registry")]
        public string? IcoRegistry { get; set; }

        [JsonPropertyName("company_name_registry")]
        public string? CompanyNameRegistry { get; set; }

        [JsonPropertyName("legal_form")]
        public string? LegalForm { get; set; }

        [JsonPropertyName("legal_form_code")]
        public string? LegalFormCode { get; set; }

        [JsonPropertyName("status")]
        public string? Status { get; set; }

        [JsonPropertyName("status_effective_date")]
        public string? StatusEffectiveDate { get; set; }

        [JsonPropertyName("incorporation_date")]
        public string? IncorporationDate { get; set; }

        [JsonPropertyName("registered_address")]
        public UnifiedAddress? RegisteredAddress { get; set; }

        [JsonPropertyName("nace_codes")]
        public List<string>? NaceCodes { get; set; }

        [JsonPropertyName("vat_id")]
        public string? VatId { get; set; }

        [JsonPropertyName("tax_id")]
        public string? TaxId { get; set; }
    }

    /// <summary>
    /// Unified holder/owner structure.
    /// </summary>
    public class UnifiedHolder
    {
        [JsonPropertyName("holder_type")]
        public string HolderType { get; set; } = "unknown"; // individual, entity, trust_fund

        [JsonPropertyName("role")]
        public string Role { get; set; } = "unknown"; // shareholder, beneficial_owner, statutory_body, procurist, liquidator

        [JsonPropertyName("name")]
        public string? Name { get; set; }

        [JsonPropertyName("ico")]
        public string? Ico { get; set; }

        [JsonPropertyName("jurisdiction")]
        public string? Jurisdiction { get; set; } // ISO country code for entity holders

        [JsonPropertyName("citizenship")]
        public string? Citizenship { get; set; } // ISO country code for individuals

        [JsonPropertyName("date_of_birth")]
        public string? DateOfBirth { get; set; }

        [JsonPropertyName("residency")]
        public string? Residency { get; set; } // ISO country code

        [JsonPropertyName("address")]
        public UnifiedAddress? Address { get; set; }

        [JsonPropertyName("ownership_pct_direct")]
        public double OwnershipPctDirect { get; set; } = 0.0;

        [JsonPropertyName("voting_rights_pct")]
        public double? VotingRightsPct { get; set; }

        [JsonPropertyName("record_effective_from")]
        public string? RecordEffectiveFrom { get; set; }

        [JsonPropertyName("record_effective_to")]
        public string? RecordEffectiveTo { get; set; }
    }

    /// <summary>
    /// Tax debt information.
    /// </summary>
    public class TaxDebts
    {
        [JsonPropertyName("has_debts")]
        public bool HasDebts { get; set; } = false;

        [JsonPropertyName("amount_eur")]
        public double AmountEur { get; set; } = 0.0;

        [JsonPropertyName("details")]
        public string? Details { get; set; }
    }

    /// <summary>
    /// Unified tax information structure.
    /// </summary>
    public class UnifiedTaxInfo
    {
        [JsonPropertyName("vat_id")]
        public string? VatId { get; set; }

        [JsonPropertyName("vat_status")]
        public string? VatStatus { get; set; } // active, inactive

        [JsonPropertyName("tax_id")]
        public string? TaxId { get; set; }

        [JsonPropertyName("tax_debts")]
        public TaxDebts? TaxDebtsInfo { get; set; }
    }

    /// <summary>
    /// Unified metadata structure.
    /// </summary>
    public class UnifiedMetadata
    {
        [JsonPropertyName("source")]
        public string Source { get; set; } = "";

        [JsonPropertyName("register_name")]
        public string RegisterName { get; set; } = "";

        [JsonPropertyName("register_url")]
        public string? RegisterUrl { get; set; }

        [JsonPropertyName("retrieved_at")]
        public string RetrievedAt { get; set; } = DateTime.UtcNow.ToString("o");

        [JsonPropertyName("snapshot_reference")]
        public string? SnapshotReference { get; set; }

        [JsonPropertyName("parent_entity_ico")]
        public string? ParentEntityIco { get; set; }

        [JsonPropertyName("level")]
        public int Level { get; set; } = 0;

        [JsonPropertyName("is_mock")]
        public bool IsMock { get; set; } = false;
    }

    /// <summary>
    /// Complete unified output structure.
    /// </summary>
    public class UnifiedData
    {
        [JsonPropertyName("entity")]
        public UnifiedEntity Entity { get; set; } = new UnifiedEntity();

        [JsonPropertyName("holders")]
        public List<UnifiedHolder> Holders { get; set; } = new List<UnifiedHolder>();

        [JsonPropertyName("tax_info")]
        public UnifiedTaxInfo? TaxInfo { get; set; }

        [JsonPropertyName("metadata")]
        public UnifiedMetadata Metadata { get; set; } = new UnifiedMetadata();

        public string ToJson(bool indent = true)
        {
            var options = new JsonSerializerOptions
            {
                WriteIndented = indent,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
            };
            return JsonSerializer.Serialize(this, options);
        }
    }

    #endregion

    #region Normalization Helpers

    /// <summary>
    /// Helper class for normalizing data from different sources.
    /// </summary>
    public static class OutputNormalizer
    {
        // Country code mappings to ISO 3166-1 alpha-2
        private static readonly Dictionary<string, string> CountryCodeMappings = new()
        {
            {"slovensko", "SK"}, {"slovakia", "SK"}, {"slovak", "SK"}, {"sk", "SK"},
            {"česká republika", "CZ"}, {"ceska republika", "CZ"}, {"czech republic", "CZ"},
            {"czechia", "CZ"}, {"česko", "CZ"}, {"cesko", "CZ"}, {"cz", "CZ"},
            {"austria", "AT"}, {"rakúsko", "AT"}, {"rakousko", "AT"}, {"at", "AT"},
            {"germany", "DE"}, {"nemecko", "DE"}, {"de", "DE"},
            {"italy", "IT"}, {"taliansko", "IT"}, {"it", "IT"},
            {"hungary", "HU"}, {"maďarsko", "HU"}, {"madarsko", "HU"}, {"hu", "HU"},
            {"poland", "PL"}, {"poľsko", "PL"}, {"polsko", "PL"}, {"pl", "PL"},
            {"united kingdom", "GB"}, {"velká británia", "GB"}, {"velka britanie", "GB"},
            {"gb", "GB"}, {"uk", "GB"},
            {"usa", "US"}, {"united states", "US"}, {"spojené štáty", "US"}, {"us", "US"},
        };

        // Status value mappings to normalized values
        private static readonly Dictionary<string, string> StatusMappings = new()
        {
            {"aktivní", "active"}, {"aktivni", "active"}, {"active", "active"},
            {"aktívny", "active"}, {"aktívne", "active"}, {"činný", "active"},
            {"cinný", "active"}, {"zapsaný", "active"}, {"zapsany", "active"},
            {"zrušený", "cancelled"}, {"zruseny", "cancelled"}, {"cancelled", "cancelled"},
            {"zrušena", "cancelled"}, {"zrusena", "cancelled"}, {"vymazaný", "cancelled"},
            {"likvidace", "in_liquidation"}, {"liquidation", "in_liquidation"},
            {"v likvidaci", "in_liquidation"}, {"v likvidácii", "in_liquidation"},
            {"konkurz", "bankruptcy"}, {"bankruptcy", "bankruptcy"}, {"v konkurze", "bankruptcy"},
            {"zaniklý", "dissolved"}, {"zanikly", "dissolved"}, {"dissolved", "dissolved"},
            {"pozastavený", "suspended"}, {"suspended", "suspended"},
            {"neaktivní", "inactive"}, {"inactive", "inactive"},
        };

        // Register names for each source
        private static readonly Dictionary<string, string> RegisterNames = new()
        {
            {"ARES_CZ", "Register of Economic Subjects (ARES)"},
            {"JUSTICE_CZ", "Commercial Register (Obchodní rejstřík)"},
            {"ESM_CZ", "Register of Beneficial Owners (Evidence skutečných majitelů)"},
            {"ORSR_SK", "Business Register (Obchodný register SR)"},
            {"RPO_SK", "Register of Legal Entities (Register právnických osôb)"},
            {"RPVS_SK", "Register of Public Sector Partners"},
            {"FINANCNA_SK", "Financial Administration (Finančná správa)"},
            {"STATS_SK", "Statistical Office of the Slovak Republic"},
        };

        /// <summary>
        /// Normalize country name/code to ISO 3166-1 alpha-2 format.
        /// </summary>
        public static string? NormalizeCountryCode(string? country)
        {
            if (string.IsNullOrWhiteSpace(country))
                return null;

            var countryLower = country.ToLower().Trim();

            // Already a valid 2-letter code
            if (countryLower.Length == 2 && char.IsLetter(countryLower[0]) && char.IsLetter(countryLower[1]))
                return countryLower.ToUpper();

            return CountryCodeMappings.TryGetValue(countryLower, out var code) ? code : null;
        }

        /// <summary>
        /// Normalize status value to standard format.
        /// </summary>
        public static string? NormalizeStatus(string? status)
        {
            if (string.IsNullOrWhiteSpace(status))
                return null;

            var statusLower = status.ToLower().Trim();
            return StatusMappings.TryGetValue(statusLower, out var normalized) ? normalized : statusLower;
        }

        /// <summary>
        /// Get human-readable register name for source.
        /// </summary>
        public static string GetRegisterName(string source)
        {
            return RegisterNames.TryGetValue(source, out var name) ? name : source;
        }

        /// <summary>
        /// Detect holder type from holder data.
        /// </summary>
        public static string DetectHolderType(Dictionary<string, object?> holderData)
        {
            // Check explicit type field
            if (holderData.TryGetValue("type", out var type) || holderData.TryGetValue("holder_type", out type))
            {
                var typeStr = type?.ToString()?.ToLower() ?? "";
                if (typeStr.Contains("fyzic") || typeStr.Contains("individual") || typeStr.Contains("natural"))
                    return "individual";
                if (typeStr.Contains("pravnic") || typeStr.Contains("entity") || typeStr.Contains("corporate"))
                    return "entity";
                if (typeStr.Contains("trust") || typeStr.Contains("fund"))
                    return "trust_fund";
            }

            // Check for birth date (indicates individual)
            if (holderData.ContainsKey("birth_date") || holderData.ContainsKey("date_of_birth"))
                return "individual";

            // Check for company indicators in name
            if (holderData.TryGetValue("name", out var nameObj))
            {
                var name = nameObj?.ToString()?.ToLower() ?? "";
                var companyIndicators = new[] { "a.s.", "s.r.o.", "ag", "gmbh", "inc.", "corp.", "ltd.", "spol." };
                foreach (var indicator in companyIndicators)
                {
                    if (name.Contains(indicator))
                        return "entity";
                }
            }

            // Check if there's an IČO for the holder (indicates entity)
            if (holderData.ContainsKey("ico") || holderData.ContainsKey("ico_registry"))
                return "entity";

            return "individual";
        }

        /// <summary>
        /// Get current timestamp in ISO format.
        /// </summary>
        public static string GetRetrievedAt()
        {
            return DateTime.UtcNow.ToString("o");
        }

        /// <summary>
        /// Build entity URL based on source and ICO.
        /// </summary>
        public static string? BuildRegisterUrl(string source, string? ico)
        {
            if (string.IsNullOrEmpty(ico))
                return null;

            return source.ToUpper() switch
            {
                "ARES_CZ" => $"https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}",
                "ORSR_SK" => $"https://www.orsr.sk/hladaj_ico.asp?ICO={ico}&lan=en",
                "RPO_SK" => $"https://api.statistics.sk/rpo/v1/entity/{ico}",
                "RPVS_SK" => $"https://rpvs.gov.sk/opendatav2/partner/{ico}",
                "FINANCNA_SK" => $"https://opendata.financnasprava.sk/api/tax/{ico}",
                "ESM_CZ" => $"https://issm.justice.cz/ubo/{ico}",
                "JUSTICE_CZ" => $"https://or.justice.cz/ias/ui/rejstrik?ico={ico}",
                _ => null
            };
        }
    }

    #endregion
}
