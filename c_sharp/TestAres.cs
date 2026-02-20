using System;
using System.Threading.Tasks;
using Ares;
using UnifiedOutput;

namespace TestAres
{
    class Program
    {
        static async Task Main(string[] args)
        {
            Console.WriteLine("Testing ARES Client - Unified Output Format");
            Console.WriteLine("===========================================\n");

            using var client = new AresClient();

            // Test 1: Known entity (Ministerstvo financí)
            Console.WriteLine("Test 1: Ministerstvo financí (00006947)");
            var result1 = await client.SearchByICOAsync("00006947");
            if (result1 != null)
            {
                Console.WriteLine($"  ✓ Found: {result1.Entity.CompanyNameRegistry}");
                Console.WriteLine($"  Status: {result1.Entity.Status}");
                Console.WriteLine($"  VAT: {result1.TaxInfo?.VatStatus}");
                Console.WriteLine($"  Mock: {result1.Metadata.IsMock}");
            }
            else
            {
                Console.WriteLine("  ✗ Not found");
            }

            // Test 2: Prusa Research a.s.
            Console.WriteLine("\nTest 2: Prusa Research a.s. (06649114)");
            var result2 = await client.SearchByICOAsync("06649114");
            if (result2 != null)
            {
                Console.WriteLine($"  ✓ Found: {result2.Entity.CompanyNameRegistry}");
                Console.WriteLine($"  Legal Form: {result2.Entity.LegalForm}");
                Console.WriteLine($"  Status: {result2.Entity.Status}");
                Console.WriteLine($"  VAT ID: {result2.Entity.VatId}");
                Console.WriteLine($"  VAT Status: {result2.TaxInfo?.VatStatus}");
                Console.WriteLine($"  Address: {result2.Entity.RegisteredAddress?.FullAddress}");
                Console.WriteLine($"  Country Code: {result2.Entity.RegisteredAddress?.CountryCode}");
                Console.WriteLine($"  Mock: {result2.Metadata.IsMock}");
                Console.WriteLine($"\n  Full JSON:\n{result2.ToJson()}");
            }
            else
            {
                Console.WriteLine("  ✗ Not found");
            }

            // Test 3: AGROFERT a.s. (not in ARES)
            Console.WriteLine("\nTest 3: AGROFERT a.s. (25932910)");
            var result3 = await client.SearchByICOAsync("25932910");
            if (result3 != null)
            {
                Console.WriteLine($"  ✓ Found: {result3.Entity.CompanyNameRegistry}");
            }
            else
            {
                Console.WriteLine("  ✗ Not found (AGROFERT not in ARES database)");
            }

            Console.WriteLine("\n===========================================");
            Console.WriteLine("C# Unified Output Format Test Complete");
        }
    }
}
