using System;
using System.Threading.Tasks;
using Rpvs;
using UnifiedOutput;

class TestRpvsOnly
{
    static async Task Main(string[] args)
    {
        var client = new RpvsClient();
        
        // Test with an ICO that exists in RPVS
        var result = await client.SearchByICOAsync("47559870");
        
        if (result != null)
        {
            Console.WriteLine("=== RPVS OData API Test ===");
            Console.WriteLine($"ICO: {result.Entity.IcoRegistry}");
            Console.WriteLine($"Name: {result.Entity.CompanyNameRegistry}");
            Console.WriteLine($"Legal Form: {result.Entity.LegalForm}");
            Console.WriteLine($"Status: {result.Entity.Status}");
            Console.WriteLine($"Source: {result.Metadata.Source}");
            Console.WriteLine($"Is Mock: {result.Metadata.IsMock}");
        }
    }
}
