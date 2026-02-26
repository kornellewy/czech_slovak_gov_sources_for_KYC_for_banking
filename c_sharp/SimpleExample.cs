using System;
using System.Threading.Tasks;
using Ares;
using Rpo;
using UnifiedOutput;

/// <summary>
/// Simple example using only ARES (Czech) and RPO (Slovak) registries.
/// </summary>
class SimpleExample
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("============================================================");
        Console.WriteLine(" SIMPLE EXAMPLE - ARES (CZ) + RPO (SK)");
        Console.WriteLine("============================================================");

        // Example 1: ARES - Czech company lookup
        await Example_Ares();

        // Example 2: RPO - Slovak company lookup
        await Example_Rpo();

        Console.WriteLine("\n============================================================");
        Console.WriteLine(" Done!");
        Console.WriteLine("============================================================");
    }

    static async Task Example_Ares()
    {
        Console.WriteLine("\n--- ARES (Czech Republic) ---");
        Console.WriteLine("Querying: Prusa Research a.s. (ICO: 06649114)\n");

        var client = new AresClient();
        var result = await client.SearchByICOAsync("06649114");

        if (result != null)
        {
            Console.WriteLine($"Company: {result.Entity.CompanyNameRegistry}");
            Console.WriteLine($"ICO: {result.Entity.IcoRegistry}");
            Console.WriteLine($"Status: {result.Entity.Status}");
            Console.WriteLine($"Legal Form: {result.Entity.LegalForm}");
            Console.WriteLine($"VAT ID: {result.Entity.VatId}");

            if (result.Entity.RegisteredAddress != null)
            {
                Console.WriteLine($"Address: {result.Entity.RegisteredAddress.FullAddress}");
            }

            Console.WriteLine($"Is Mock: {result.Metadata.IsMock}");
        }
        else
        {
            Console.WriteLine("Company not found");
        }
    }

    static async Task Example_Rpo()
    {
        Console.WriteLine("\n--- RPO (Slovakia) ---");
        Console.WriteLine("Querying: ZELEX, s.r.o. (ICO: 47559870)\n");

        var client = new RpoClient();
        var result = await client.SearchByICOAsync("47559870");

        if (result != null)
        {
            Console.WriteLine($"Company: {result.Entity.CompanyNameRegistry}");
            Console.WriteLine($"ICO: {result.Entity.IcoRegistry}");
            Console.WriteLine($"Status: {result.Entity.Status}");
            Console.WriteLine($"Legal Form: {result.Entity.LegalForm}");
            Console.WriteLine($"Incorporation Date: {result.Entity.IncorporationDate}");

            if (result.Entity.RegisteredAddress != null)
            {
                var addr = result.Entity.RegisteredAddress;
                Console.WriteLine($"Address: {addr.Street}, {addr.City} {addr.PostalCode}");
                Console.WriteLine($"Country: {addr.CountryCode}");
            }

            if (result.Holders.Count > 0)
            {
                Console.WriteLine($"\nHolders ({result.Holders.Count}):");
                foreach (var holder in result.Holders)
                {
                    Console.WriteLine($"  - [{holder.Role}] {holder.Name}");
                }
            }

            Console.WriteLine($"\nIs Mock: {result.Metadata.IsMock}");
        }
        else
        {
            Console.WriteLine("Company not found");
        }
    }
}
