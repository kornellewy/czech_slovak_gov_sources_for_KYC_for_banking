using System;
using System.Threading.Tasks;
using CompanyRegistry;
using UnifiedOutput;

/// <summary>
/// Example program demonstrating how to use the Company Registry API
/// in your own C# applications.
/// </summary>
class ApiExample
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("============================================================");
        Console.WriteLine(" COMPANY REGISTRY API - C# USAGE EXAMPLES");
        Console.WriteLine("============================================================");

        await Example1_BasicLookup();
        await Example2_OwnershipStructure();
        await Example3_VatVerification();
        await Example4_FullInfo();
        await Example5_BatchProcessing();
        await Example6_CrossBorderQueries();

        Console.WriteLine("\n============================================================");
        Console.WriteLine(" All examples completed!");
        Console.WriteLine("============================================================");
        Console.WriteLine("\nTo use in your code:");
        Console.WriteLine("  var service = new CompanyRegistryService();");
        Console.WriteLine("  var result = await service.GetCompanyInfoAsync(\"06649114\");");
    }

    /// <summary>
    /// Example 1: Basic company lookup
    /// </summary>
    static async Task Example1_BasicLookup()
    {
        Console.WriteLine("\n" + new string('=', 60));
        Console.WriteLine("Example 1: Basic Company Lookup");
        Console.WriteLine(new string('=', 60));

        var service = new CompanyRegistryService();

        // Look up Prusa Research
        var result = await service.GetCompanyInfoAsync("06649114", Country.CzechRepublic);

        if (result != null)
        {
            Console.WriteLine($"Company: {result.Entity.CompanyNameRegistry}");
            Console.WriteLine($"Status: {result.Entity.Status}");
            Console.WriteLine($"Legal Form: {result.Entity.LegalForm}");
            Console.WriteLine($"Address: {result.Entity.RegisteredAddress?.FullAddress}");
        }
        else
        {
            Console.WriteLine("Company not found");
        }
    }

    /// <summary>
    /// Example 2: Get ownership structure
    /// </summary>
    static async Task Example2_OwnershipStructure()
    {
        Console.WriteLine("\n" + new string('=', 60));
        Console.WriteLine("Example 2: Ownership Structure");
        Console.WriteLine(new string('=', 60));

        var service = new CompanyRegistryService();

        // Get Slovenská sporiteľňa ownership
        var summary = await service.GetOwnersSummaryAsync("35763491", Country.Slovakia);

        if (summary != null)
        {
            Console.WriteLine($"Company: {summary.CompanyName}");
            Console.WriteLine($"Total Owners: {summary.TotalOwners}");
            Console.WriteLine($"Ownership Concentrated: {summary.OwnershipConcentrated}");
            Console.WriteLine("\nOwners:");

            foreach (var owner in summary.Owners)
            {
                Console.WriteLine($"  - {owner.Name}");
                Console.WriteLine($"    Type: {owner.Type}");
                Console.WriteLine($"    Ownership: {owner.OwnershipPct}%");
                Console.WriteLine($"    Voting Rights: {owner.VotingRightsPct}%");
                if (owner.Jurisdiction != null)
                {
                    Console.WriteLine($"    Jurisdiction: {owner.Jurisdiction}");
                }
            }
        }
    }

    /// <summary>
    /// Example 3: Verify VAT number
    /// </summary>
    static async Task Example3_VatVerification()
    {
        Console.WriteLine("\n" + new string('=', 60));
        Console.WriteLine("Example 3: VAT Number Verification");
        Console.WriteLine(new string('=', 60));

        var service = new CompanyRegistryService();

        // Verify Czech VAT number
        var result = await service.VerifyVatNumberAsync("CZ06649114");

        Console.WriteLine($"VAT ID: CZ06649114");
        Console.WriteLine($"Valid: {result.Valid}");
        Console.WriteLine($"Active: {result.Active}");

        if (result.Valid)
        {
            Console.WriteLine($"Company: {result.CompanyName}");
            Console.WriteLine($"ICO: {result.Ico}");
            Console.WriteLine($"Is Mock: {result.IsMock}");
        }
    }

    /// <summary>
    /// Example 4: Get complete company information
    /// </summary>
    static async Task Example4_FullInfo()
    {
        Console.WriteLine("\n" + new string('=', 60));
        Console.WriteLine("Example 4: Complete Company Information");
        Console.WriteLine(new string('=', 60));

        var service = new CompanyRegistryService();

        // Get all available information
        var full = await service.GetFullInfoAsync("06649114", Country.CzechRepublic);

        if (full != null)
        {
            Console.WriteLine("\n--- Entity ---");
            Console.WriteLine($"Name: {full.Entity.CompanyNameRegistry}");
            Console.WriteLine($"Status: {full.Entity.Status}");
            Console.WriteLine($"VAT ID: {full.Entity.VatId}");

            Console.WriteLine("\n--- Holders ---");
            Console.WriteLine($"Count: {full.Holders.Count}");
            foreach (var holder in full.Holders)
            {
                Console.WriteLine($"  - {holder.Name} ({holder.Role})");
            }

            Console.WriteLine("\n--- Tax Info ---");
            if (full.TaxInfo != null)
            {
                Console.WriteLine($"VAT Status: {full.TaxInfo.VatStatus}");
            }

            Console.WriteLine("\n--- Metadata ---");
            Console.WriteLine($"Source: {full.Metadata.Source}");
            Console.WriteLine($"Retrieved: {full.Metadata.RetrievedAt}");
            Console.WriteLine($"Is Mock: {full.Metadata.IsMock}");
        }
    }

    /// <summary>
    /// Example 5: Batch processing
    /// </summary>
    static async Task Example5_BatchProcessing()
    {
        Console.WriteLine("\n" + new string('=', 60));
        Console.WriteLine("Example 5: Batch Processing");
        Console.WriteLine(new string('=', 60));

        var service = new CompanyRegistryService();

        // List of ICOs to process
        var icos = new[] { "00006947", "00216305", "06649114" };

        Console.WriteLine("Processing companies...");

        foreach (var ico in icos)
        {
            var result = await service.GetCompanyInfoAsync(ico, Country.CzechRepublic);
            if (result != null)
            {
                Console.WriteLine($"  [{ico}] {result.Entity.CompanyNameRegistry} - {result.Entity.Status}");
            }
        }
    }

    /// <summary>
    /// Example 6: Cross-border queries
    /// </summary>
    static async Task Example6_CrossBorderQueries()
    {
        Console.WriteLine("\n" + new string('=', 60));
        Console.WriteLine("Example 6: Cross-Border Queries");
        Console.WriteLine(new string('=', 60));

        var service = new CompanyRegistryService();

        var companies = new[]
        {
            (Ico: "06649114", Country: Country.CzechRepublic, Name: "Prusa Research"),
            (Ico: "35763491", Country: Country.Slovakia, Name: "Slovenská sporiteľňa"),
        };

        foreach (var (ico, country, expectedName) in companies)
        {
            var result = await service.GetCompanyInfoAsync(ico, country);
            if (result != null)
            {
                Console.WriteLine($"[{country}] {result.Entity.CompanyNameRegistry} ({ico})");
            }
        }
    }

    /// <summary>
    /// Example 7: Using dependency injection
    /// </summary>
    static void Example7_DependencyInjection()
    {
        Console.WriteLine("\n" + new string('=', 60));
        Console.WriteLine("Example 7: Dependency Injection Setup");
        Console.WriteLine(new string('=', 60));

        Console.WriteLine(@"
// In your Startup.cs or Program.cs:

// Add the service
builder.Services.AddSingleton<ICompanyRegistryService>(sp =>
    new CompanyRegistryService(Country.CzechRepublic));

// In your controller/service:
public class CompanyController : ControllerBase
{
    private readonly ICompanyRegistryService _registry;

    public CompanyController(ICompanyRegistryService registry)
    {
        _registry = registry;
    }

    [HttpGet(""company/{ico}"")]
    public async Task<IActionResult> GetCompany(string ico)
    {
        var result = await _registry.GetCompanyInfoAsync(
            ico, Country.CzechRepublic);

        if (result == null)
            return NotFound();

        return Ok(new
        {
            name = result.Entity.CompanyNameRegistry,
            status = result.Entity.Status
        });
    }
}
        ");
    }
}
