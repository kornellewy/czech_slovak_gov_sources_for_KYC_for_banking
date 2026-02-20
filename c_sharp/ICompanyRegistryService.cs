using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnifiedOutput;

namespace CompanyRegistry
{
    /// <summary>
    /// Interface for company registry service.
    /// Implement this interface to create custom registry providers.
    /// </summary>
    public interface ICompanyRegistryService
    {
        /// <summary>
        /// Get basic company information by ICO.
        /// </summary>
        Task<UnifiedData?> GetCompanyInfoAsync(string ico, Country? country = null);

        /// <summary>
        /// Get Ultimate Beneficial Owner (UBO) information.
        /// </summary>
        Task<UnifiedData?> GetUboInfoAsync(string ico, Country? country = null);

        /// <summary>
        /// Get tax information (VAT status, tax debts).
        /// </summary>
        Task<UnifiedData?> GetTaxInfoAsync(string ico, Country? country = null);

        /// <summary>
        /// Get complete company information from all available sources.
        /// </summary>
        Task<UnifiedData?> GetFullInfoAsync(string ico, Country? country = null);

        /// <summary>
        /// Search for companies by name.
        /// </summary>
        Task<List<UnifiedData>> SearchByNameAsync(string name, Country? country = null, int limit = 10);

        /// <summary>
        /// Verify if a VAT number is valid and active.
        /// </summary>
        Task<VatVerificationResult> VerifyVatNumberAsync(string vatId, Country? country = null);

        /// <summary>
        /// Get ownership structure summary.
        /// </summary>
        Task<OwnershipSummary?> GetOwnersSummaryAsync(string ico, Country? country = null, double minOwnership = 0.0);
    }

    /// <summary>
    /// Supported countries for registry queries.
    /// </summary>
    public enum Country
    {
        CzechRepublic,
        Slovakia
    }

    /// <summary>
    /// VAT verification result.
    /// </summary>
    public class VatVerificationResult
    {
        public bool Valid { get; set; }
        public bool Active { get; set; }
        public string? CompanyName { get; set; }
        public string? Ico { get; set; }
        public string? VatId { get; set; }
        public bool IsMock { get; set; }
    }

    /// <summary>
    /// Ownership structure summary.
    /// </summary>
    public class OwnershipSummary
    {
        public string? CompanyName { get; set; }
        public string? Ico { get; set; }
        public int TotalOwners { get; set; }
        public List<OwnerInfo> Owners { get; set; } = new();
        public bool OwnershipConcentrated { get; set; }
        public bool IsMock { get; set; }
    }

    /// <summary>
    /// Information about a single owner.
    /// </summary>
    public class OwnerInfo
    {
        public string? Name { get; set; }
        public string Type { get; set; } = "unknown";  // individual, entity, trust_fund
        public double OwnershipPct { get; set; }
        public double? VotingRightsPct { get; set; }
        public string? Jurisdiction { get; set; }
        public string Role { get; set; } = "unknown";
    }
}
