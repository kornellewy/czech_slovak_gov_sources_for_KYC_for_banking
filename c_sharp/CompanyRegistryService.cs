using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using UnifiedOutput;
using Ares;
using Orsr;
using Rpo;
using Rpvs;
using Justice;
using Esm;
using FinancnaSprava;

namespace CompanyRegistry
{
    /// <summary>
    /// Main implementation of the Company Registry Service.
    /// Provides a unified interface for querying SK/CZ business registries.
    ///
    /// Usage:
    ///     var service = new CompanyRegistryService();
    ///     var info = await service.GetCompanyInfoAsync("06649114", Country.CzechRepublic);
    ///     Console.WriteLine(info.Entity.CompanyNameRegistry);
    /// </summary>
    public class CompanyRegistryService : ICompanyRegistryService, IDisposable
    {
        private readonly Country _defaultCountry;

        public CompanyRegistryService(Country defaultCountry = Country.CzechRepublic)
        {
            _defaultCountry = defaultCountry;
        }

        /// <summary>
        /// Get basic company information by ICO.
        /// </summary>
        public async Task<UnifiedData?> GetCompanyInfoAsync(string ico, Country? country = null)
        {
            var c = country ?? _defaultCountry;
            var source = c == Country.CzechRepublic ? DataSource.Ares : DataSource.Orsr;

            return await QueryBySourceAsync(source, ico);
        }

        /// <summary>
        /// Get Ultimate Beneficial Owner (UBO) information.
        /// </summary>
        public async Task<UnifiedData?> GetUboInfoAsync(string ico, Country? country = null)
        {
            var c = country ?? _defaultCountry;
            var source = c == Country.CzechRepublic ? DataSource.Esm : DataSource.Rpvs;

            return await QueryBySourceAsync(source, ico);
        }

        /// <summary>
        /// Get tax information (VAT status, tax debts).
        /// </summary>
        public async Task<UnifiedData?> GetTaxInfoAsync(string ico, Country? country = null)
        {
            var c = country ?? _defaultCountry;
            var source = c == Country.CzechRepublic ? DataSource.Ares : DataSource.Financna;

            return await QueryBySourceAsync(source, ico);
        }

        /// <summary>
        /// Get complete company information from all available sources.
        /// </summary>
        public async Task<UnifiedData?> GetFullInfoAsync(string ico, Country? country = null)
        {
            var c = country ?? _defaultCountry;

            // Start with basic info
            var result = await GetCompanyInfoAsync(ico, c);
            if (result == null) return null;

            // Add UBO info
            var uboResult = await GetUboInfoAsync(ico, c);
            if (uboResult != null && uboResult.Holders != null)
            {
                result.Holders.AddRange(uboResult.Holders);
            }

            // Add commercial register info for Czech
            if (c == Country.CzechRepublic)
            {
                var justiceResult = await QueryBySourceAsync(DataSource.Justice, ico);
                if (justiceResult != null && justiceResult.Holders != null)
                {
                    result.Holders.AddRange(justiceResult.Holders);
                }
            }

            return result;
        }

        /// <summary>
        /// Search for companies by name.
        /// Note: Only Slovak ORSR supports name search.
        /// </summary>
        public async Task<List<UnifiedData>> SearchByNameAsync(string name, Country? country = null, int limit = 10)
        {
            var c = country ?? _defaultCountry;

            if (c != Country.Slovakia)
            {
                return new List<UnifiedData>();  // ARES doesn't support name search
            }

            using var client = new OrsrClient();
            var results = await client.SearchByNameAsync(name);

            return results.Take(limit).ToList();
        }

        /// <summary>
        /// Verify if a VAT number is valid and active.
        /// </summary>
        public async Task<VatVerificationResult> VerifyVatNumberAsync(string vatId, Country? country = null)
        {
            // Detect country from VAT ID prefix
            Country c;
            if (country.HasValue)
            {
                c = country.Value;
            }
            else if (vatId.ToUpper().StartsWith("CZ"))
            {
                c = Country.CzechRepublic;
            }
            else if (vatId.ToUpper().StartsWith("SK"))
            {
                c = Country.Slovakia;
            }
            else
            {
                c = _defaultCountry;
            }

            // Extract ICO from VAT ID
            var ico = vatId.Length > 2 && (vatId.Substring(0, 2).ToUpper() == "CZ" || vatId.Substring(0, 2).ToUpper() == "SK")
                ? vatId.Substring(2)
                : vatId;

            var result = await GetCompanyInfoAsync(ico, c);

            if (result == null)
            {
                return new VatVerificationResult
                {
                    Valid = false,
                    Active = false,
                    Ico = ico
                };
            }

            return new VatVerificationResult
            {
                Valid = true,
                Active = result.TaxInfo?.VatStatus == "active",
                CompanyName = result.Entity.CompanyNameRegistry,
                Ico = result.Entity.IcoRegistry,
                VatId = result.TaxInfo?.VatId,
                IsMock = result.Metadata.IsMock
            };
        }

        /// <summary>
        /// Get ownership structure summary.
        /// </summary>
        public async Task<OwnershipSummary?> GetOwnersSummaryAsync(string ico, Country? country = null, double minOwnership = 0.0)
        {
            var result = await GetFullInfoAsync(ico, country);
            if (result == null) return null;

            var holders = result.Holders ?? new List<UnifiedHolder>();

            // Filter by minimum ownership
            var owners = holders
                .Where(h => h.OwnershipPctDirect >= minOwnership)
                .OrderByDescending(h => h.OwnershipPctDirect)
                .Select(h => new OwnerInfo
                {
                    Name = h.Name,
                    Type = h.HolderType,
                    OwnershipPct = h.OwnershipPctDirect,
                    VotingRightsPct = h.VotingRightsPct,
                    Jurisdiction = h.Jurisdiction,
                    Role = h.Role
                })
                .ToList();

            return new OwnershipSummary
            {
                CompanyName = result.Entity.CompanyNameRegistry,
                Ico = result.Entity.IcoRegistry,
                TotalOwners = owners.Count,
                Owners = owners,
                OwnershipConcentrated = owners.Any(o => o.OwnershipPct > 50),
                IsMock = result.Metadata.IsMock
            };
        }

        private async Task<UnifiedData?> QueryBySourceAsync(DataSource source, string ico)
        {
            try
            {
                return source switch
                {
                    DataSource.Ares => await new AresClient().SearchByICOAsync(ico),
                    DataSource.Orsr => await new OrsrClient().SearchByICOAsync(ico),
                    DataSource.Rpo => await new RpoClient().SearchByICOAsync(ico),
                    DataSource.Rpvs => await new RpvsClient().SearchByICOAsync(ico),
                    DataSource.Justice => await new JusticeClient().SearchByICOAsync(ico),
                    DataSource.Esm => await new EsmClient().SearchByICOAsync(ico),
                    DataSource.Financna => await new FinancnaSpravaClient().SearchByICOAsync(ico),
                    _ => null
                };
            }
            catch
            {
                return null;
            }
        }

        public void Dispose()
        {
            // Cleanup if needed
        }

        private enum DataSource
        {
            Ares,
            Orsr,
            Rpo,
            Rpvs,
            Justice,
            Esm,
            Financna
        }
    }

    /// <summary>
    /// Singleton service provider for dependency injection scenarios.
    /// </summary>
    public static class CompanyRegistryServiceProvider
    {
        private static ICompanyRegistryService? _defaultService;

        /// <summary>
        /// Get the default service instance.
        /// </summary>
        public static ICompanyRegistryService GetService(Country defaultCountry = Country.CzechRepublic)
        {
            _defaultService ??= new CompanyRegistryService(defaultCountry);
            return _defaultService;
        }

        /// <summary>
        /// Set a custom service implementation (useful for testing/mocking).
        /// </summary>
        public static void SetService(ICompanyRegistryService service)
        {
            _defaultService = service;
        }
    }
}
