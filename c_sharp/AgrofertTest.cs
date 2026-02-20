using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using UnifiedOutput;

namespace AgrofertTest
{
    /// <summary>
    /// AGROFERT a.s. Test - Demonstrates unified output format.
    /// Note: AGROFERT a.s. (ICO: 25932910) is not accessible via public ARES API.
    /// This demo shows the expected unified output format with simulated data.
    /// </summary>
    class Program
    {
        static async Task Main(string[] args)
        {
            Console.WriteLine("╔" + new string('=', 68) + "╗");
            Console.WriteLine("║              AGROFERT a.s. - C# TEST                          ║");
            Console.WriteLine("╚" + new string('=', 68) + "╝");

            Console.WriteLine("\nNote: AGROFERT a.s. (ICO: 25932910) is not found in the public ARES API.");
            Console.WriteLine("The company was reorganized in 2017. This demo shows the expected");
            Console.WriteLine("unified output format with simulated data.\n");

            // Create AGROFERT demo data
            var agrofertData = CreateAgrofertDemoData();

            // Print unified output
            PrintUnifiedOutput(agrofertData);

            // Try to search ARES for AGROFERT (will return null)
            Console.WriteLine("\n" + new string('=', 70));
            Console.WriteLine("  Searching ARES API for AGROFERT a.s. (25932910)...");
            Console.WriteLine(new string('=', 70));

            using var client = new Ares.AresClient();
            var aresResult = await client.SearchByICOAsync("25932910");

            if (aresResult != null)
            {
                Console.WriteLine($"  ✓ Found: {aresResult.Entity.CompanyNameRegistry}");
                Console.WriteLine($"  Status: {aresResult.Entity.Status}");
                Console.WriteLine($"  Mock: {aresResult.Metadata.IsMock}");
            }
            else
            {
                Console.WriteLine("  ✗ Not found in ARES (404 - company not in public database)");
            }

            // Summary
            Console.WriteLine("\n" + new string('=', 70));
            Console.WriteLine("  SUMMARY");
            Console.WriteLine(new string('=', 70));
            Console.WriteLine("\nC# Unified Output Format:");
            Console.WriteLine("  ✓ Entity class: IcoRegistry, CompanyNameRegistry, LegalForm, Status");
            Console.WriteLine("  ✓ Holders: List<UnifiedHolder> with HolderType, Role, Name");
            Console.WriteLine("  ✓ TaxInfo class: VatId, VatStatus, TaxDebts");
            Console.WriteLine("  ✓ Metadata class: Source, RegisterName, RegisterUrl, RetrievedAt");
            Console.WriteLine(new string('=', 70));
        }

        static UnifiedData CreateAgrofertDemoData()
        {
            var address = new UnifiedAddress
            {
                Street = "Palackého 1320/1",
                City = "Praha 2 - Nové Město",
                PostalCode = "120 00",
                Country = "Česká republika",
                CountryCode = "CZ",
                FullAddress = "Palackého 1320/1, 120 00 Praha 2"
            };

            var entity = new UnifiedEntity
            {
                IcoRegistry = "25932910",
                CompanyNameRegistry = "AGROFERT a.s.",
                LegalForm = "Akciová společnost",
                LegalFormCode = "121",
                Status = "active",
                IncorporationDate = "1995-01-01",
                RegisteredAddress = address,
                NaceCodes = new List<string> { "01110", "01610" },
                VatId = "CZ25932910",
                TaxId = "25932910"
            };

            var holders = new List<UnifiedHolder>
            {
                new UnifiedHolder
                {
                    HolderType = "entity",
                    Role = "shareholder",
                    Name = "Agrofert Holding a.s.",
                    Ico = "25755241",
                    Jurisdiction = "CZ",
                    OwnershipPctDirect = 100.0,
                    VotingRightsPct = 100.0,
                    RecordEffectiveFrom = "2017-02-01"
                }
            };

            var taxDebts = new TaxDebts
            {
                HasDebts = false,
                AmountEur = 0.0
            };

            var taxInfo = new UnifiedTaxInfo
            {
                VatId = "CZ25932910",
                VatStatus = "active",
                TaxId = "25932910",
                TaxDebtsInfo = taxDebts
            };

            var metadata = new UnifiedMetadata
            {
                Source = "ARES_CZ",
                RegisterName = "Register of Economic Subjects (ARES)",
                RegisterUrl = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/25932910",
                RetrievedAt = DateTime.UtcNow.ToString("o"),
                SnapshotReference = "ARES_CZ_25932910_20260219",
                Level = 0,
                IsMock = true
            };

            return new UnifiedData
            {
                Entity = entity,
                Holders = holders,
                TaxInfo = taxInfo,
                Metadata = metadata
            };
        }

        static void PrintUnifiedOutput(UnifiedData data)
        {
            Console.WriteLine(new string('=', 70));
            Console.WriteLine("  AGROFERT a.s. - UNIFIED OUTPUT FORMAT (C#)");
            Console.WriteLine(new string('=', 70));

            Console.WriteLine("\n--- entity ---");
            Console.WriteLine($"  ico_registry: {data.Entity.IcoRegistry}");
            Console.WriteLine($"  company_name_registry: {data.Entity.CompanyNameRegistry}");
            Console.WriteLine($"  legal_form: {data.Entity.LegalForm}");
            Console.WriteLine($"  status: {data.Entity.Status}");
            Console.WriteLine($"  incorporation_date: {data.Entity.IncorporationDate}");
            if (data.Entity.RegisteredAddress != null)
            {
                Console.WriteLine($"  registered_address:");
                Console.WriteLine($"    full_address: {data.Entity.RegisteredAddress.FullAddress}");
                Console.WriteLine($"    country_code: {data.Entity.RegisteredAddress.CountryCode}");
            }
            Console.WriteLine($"  vat_id: {data.Entity.VatId}");

            Console.WriteLine("\n--- holders ---");
            for (int i = 0; i < data.Holders.Count; i++)
            {
                var holder = data.Holders[i];
                Console.WriteLine($"  holder {i + 1}:");
                Console.WriteLine($"    holder_type: {holder.HolderType}");
                Console.WriteLine($"    role: {holder.Role}");
                Console.WriteLine($"    name: {holder.Name}");
                Console.WriteLine($"    ico: {holder.Ico}");
                Console.WriteLine($"    jurisdiction: {holder.Jurisdiction}");
                Console.WriteLine($"    ownership_pct_direct: {holder.OwnershipPctDirect}%");
                Console.WriteLine($"    voting_rights_pct: {holder.VotingRightsPct}%");
            }

            Console.WriteLine("\n--- tax_info ---");
            if (data.TaxInfo != null)
            {
                Console.WriteLine($"  vat_id: {data.TaxInfo.VatId}");
                Console.WriteLine($"  vat_status: {data.TaxInfo.VatStatus}");
                if (data.TaxInfo.TaxDebtsInfo != null)
                {
                    Console.WriteLine($"  tax_debts:");
                    Console.WriteLine($"    has_debts: {data.TaxInfo.TaxDebtsInfo.HasDebts}");
                    Console.WriteLine($"    amount_eur: {data.TaxInfo.TaxDebtsInfo.AmountEur}");
                }
            }

            Console.WriteLine("\n--- metadata ---");
            Console.WriteLine($"  source: {data.Metadata.Source}");
            Console.WriteLine($"  register_name: {data.Metadata.RegisterName}");
            Console.WriteLine($"  register_url: {data.Metadata.RegisterUrl}");
            Console.WriteLine($"  retrieved_at: {data.Metadata.RetrievedAt}");
            Console.WriteLine($"  is_mock: {data.Metadata.IsMock}");

            Console.WriteLine("\n--- full json ---");
            Console.WriteLine(data.ToJson());
        }
    }
}
