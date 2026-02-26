using System;
using System.Threading.Tasks;
using Ares;
using UnifiedOutput;

/// <summary>
/// ARES Sub-source Extraction Test Program
/// Tests the new sub-source extraction feature in AresClient.
/// </summary>
class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("=== ARES Sub-Source Extraction Test ===\n");

        var client = new AresClient();

        // Test ICOs
        var testIcos = new[] { "05984866", "00006947", "06649114" };

        foreach (var ico in testIcos)
        {
            Console.WriteLine($"--- ICO: {ico} ---");

            try
            {
                var result = await client.SearchByICOAsync(ico, includeSubsource: true);

                if (result == null)
                {
                    Console.WriteLine("❌ Company not found\n");
                    continue;
                }

                Console.WriteLine($"✅ Company: {result.Entity.CompanyNameRegistry}");
                Console.WriteLine($"   Address: {result.Entity.RegisteredAddress?.FullAddress}");
                Console.WriteLine($"   VAT: {result.TaxInfo?.VatStatus}");

                if (result.Subsource is AresSubsource subsource)
                {
                    Console.WriteLine($"\n   📋 Active Sub-sources: {subsource.ActiveCount}");

                    foreach (var reg in subsource.Registrations)
                    {
                        if (reg.Value.IsActive)
                        {
                            Console.WriteLine($"      ✅ {reg.Key}: {reg.Value.EnglishName ?? reg.Value.Name}");
                        }
                    }

                    if (subsource.AdditionalData?.Count > 0)
                    {
                        Console.WriteLine($"\n   📦 Additional Data:");

                        foreach (var data in subsource.AdditionalData)
                        {
                            Console.WriteLine($"      {data.Key}:");
                            Console.WriteLine($"         Company: {data.Value.CompanyName}");
                            if (data.Value.FileReference != null)
                            {
                                Console.WriteLine($"         File Ref: {data.Value.FileReference}");
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Error: {ex.Message}");
            }

            Console.WriteLine();
        }

        Console.WriteLine("=== Test Complete ===");
    }
}
