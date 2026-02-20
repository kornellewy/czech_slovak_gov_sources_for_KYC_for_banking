using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnifiedOutput;

namespace FinancnaSprava
{
    /// <summary>
    /// Finančná správa Slovak Tax Office client.
    /// API: https://opendata.financnasprava.sk/api
    ///
    /// Provides VAT status and tax debt information.
    /// Output: UnifiedOutput format with entity, tax_info, metadata sections.
    ///
    /// Usage:
    ///     var client = new FinancnaSpravaClient();
    ///     var result = await client.SearchByICOAsync("35763491");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Client

    public class FinancnaSpravaClient
    {
        private const string BaseUrl = "https://opendata.financnasprava.sk/api";
        private const string Source = "FINANCNA_SK";

        // Mock database with raw data
        private static readonly Dictionary<string, (string Name, string Dic, string VatId, string VatStatus, bool HasDebts, double AmountEur)> MockDatabase = new()
        {
            { "35763491", ("Slovenská sporiteľňa, a.s.", "20357634911", "SK20357634911", "active", false, 0.0) },
            { "44103755", ("Slovak Telekom, a.s.", "2022214291", "SK2022214291", "active", false, 0.0) },
            { "36246621", ("Doprastav, a.s.", "2020272814", "SK2020272814", "active", false, 0.0) }
        };

        /// <summary>
        /// Get tax status by ICO and return unified output format.
        /// </summary>
        public Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            if (MockDatabase.TryGetValue(ico, out var data))
            {
                var output = BuildUnifiedOutput(ico, data.Name, data.Dic, data.VatId, data.VatStatus, data.HasDebts, data.AmountEur, isMock: true);
                return Task.FromResult<UnifiedData?>(output);
            }

            // Return basic output for unknown ICOs
            var emptyOutput = new UnifiedData
            {
                Entity = new UnifiedEntity
                {
                    IcoRegistry = ico
                },
                Holders = new List<UnifiedHolder>(),
                Metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{BaseUrl}/tax/{ico}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = true
                }
            };

            return Task.FromResult<UnifiedData?>(emptyOutput);
        }

        /// <summary>
        /// Legacy method - Get tax status (returns unified format).
        /// </summary>
        public async Task<UnifiedData?> GetTaxStatusAsync(string ico)
        {
            return await SearchByICOAsync(ico);
        }

        private UnifiedData BuildUnifiedOutput(string ico, string name, string dic, string vatId, string vatStatus, bool hasDebts, double amountEur, bool isMock)
        {
            var entity = new UnifiedEntity
            {
                IcoRegistry = ico,
                CompanyNameRegistry = name,
                VatId = vatId,
                TaxId = dic
            };

            var taxInfo = new UnifiedTaxInfo
            {
                VatId = vatId,
                VatStatus = vatStatus,
                TaxId = dic,
                TaxDebtsInfo = new TaxDebts
                {
                    HasDebts = hasDebts,
                    AmountEur = amountEur
                }
            };

            var metadata = new UnifiedMetadata
            {
                Source = Source,
                RegisterName = OutputNormalizer.GetRegisterName(Source),
                RegisterUrl = $"{BaseUrl}/tax/{ico}",
                RetrievedAt = DateTime.UtcNow.ToString("o"),
                IsMock = isMock
            };

            return new UnifiedData
            {
                Entity = entity,
                Holders = new List<UnifiedHolder>(),
                TaxInfo = taxInfo,
                Metadata = metadata
            };
        }
    }

    #endregion
}
