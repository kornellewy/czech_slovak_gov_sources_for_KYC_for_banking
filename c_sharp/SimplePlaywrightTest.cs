using System;
using System.Threading.Tasks;
using Microsoft.Playwright;

/// <summary>
/// Simple Playwright test for Justice.cz
///
/// Build: dotnet build SimplePlaywrightTest.csproj
/// Run: dotnet run --project SimplePlaywrightTest.csproj
/// </summary>

class SimplePlaywrightTest
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Simple Playwright Test for Justice.cz");
        Console.WriteLine("======================================\n");

        // Check if Playwright is installed
        Console.WriteLine("Checking Playwright installation...");

        try
        {
            using var playwright = await Playwright.CreateAsync();
            Console.WriteLine("✓ Playwright installed successfully");

            // Test 1: Fetch Justice.cz search page
            Console.WriteLine("\nTest 1: Fetching Justice.cz search page...");
            await TestJusticeSearch(playwright);

            // Test 2: Fetch detail page
            Console.WriteLine("\nTest 2: Fetching Justice.cz detail page...");
            await TestJusticeDetail(playwright);

            Console.WriteLine("\n✓ All tests completed!");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"\n✗ Error: {ex.Message}");
            Console.WriteLine("\nTo install Playwright:");
            Console.WriteLine("  dotnet add package Microsoft.Playwright");
            Console.WriteLine("  playwright install chromium");
        }
    }

    static async Task TestJusticeSearch(IPlaywright playwright)
    {
        await using var browser = await playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions
        {
            Headless = true
        });

        await using var context = await browser.NewContextAsync(new BrowserNewContextOptions
        {
            UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            Locale = "cs-CZ"
        });

        var page = await context.NewPageAsync();

        var ico = "05984866";
        var url = $"https://or.justice.cz/ias/ui/rejstrik-$firma?ico={ico}";

        Console.WriteLine($"  URL: {url}");

        await page.GotoAsync(url, new PageGotoOptions
        {
            WaitUntil = WaitUntilState.NetworkIdle,
            Timeout = 30000
        });

        var title = await page.TitleAsync();
        Console.WriteLine($"  Title: {title}");

        var content = await page.ContentAsync();
        Console.WriteLine($"  HTML length: {content.Length:N0} characters");

        if (content.Contains("DEVROCK"))
        {
            Console.WriteLine("  ✓ Found company: DEVROCK a.s.");
        }

        if (content.Contains("result-details"))
        {
            Console.WriteLine("  ✓ Found result table");
        }
    }

    static async Task TestJusticeDetail(IPlaywright playwright)
    {
        await using var browser = await playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions
        {
            Headless = true
        });

        await using var context = await browser.NewContextAsync();
        var page = await context.NewPageAsync();

        var ico = "06649114"; // Prusa Research
        var url = $"https://or.justice.cz/ias/ui/rejstrik-$firma?ico={ico}";

        await page.GotoAsync(url, new PageGotoOptions
        {
            WaitUntil = WaitUntilState.DOMContentLoaded
        });

        var content = await page.ContentAsync();

        if (content.Contains("Prusa Research"))
        {
            Console.WriteLine("  ✓ Found company: Prusa Research a.s.");
        }
    }
}
