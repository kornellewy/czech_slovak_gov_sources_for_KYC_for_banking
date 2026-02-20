using System;
using System.Threading.Tasks;
using Microsoft.Playwright;

namespace PlaywrightTest;

class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("Playwright Test for Justice.cz");
        Console.WriteLine("=============================\n");

        try
        {
            using var playwright = await Playwright.CreateAsync();
            Console.WriteLine("✓ Playwright installed\n");

            // Test Justice.cz
            Console.WriteLine("Testing Justice.cz search...");
            
            await using var browser = await playwright.Chromium.LaunchAsync(new()
            {
                Headless = true
            });

            await using var context = await browser.NewContextAsync(new()
            {
                UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                Locale = "cs-CZ"
            });

            var page = await context.NewPageAsync();
            var url = "https://or.justice.cz/ias/ui/rejstrik-$firma?ico=05984866";

            Console.WriteLine($"URL: {url}");
            await page.GotoAsync(url, new() { WaitUntil = WaitUntilState.NetworkIdle });

            var title = await page.TitleAsync();
            Console.WriteLine($"Title: {title}");

            var content = await page.ContentAsync();
            Console.WriteLine($"HTML: {content.Length:N0} chars");

            if (content.Contains("DEVROCK"))
                Console.WriteLine("✓ Found DEVROCK a.s.");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"✗ Error: {ex.Message}");
            Console.WriteLine("\nInstall with:");
            Console.WriteLine("  dotnet add package Microsoft.Playwright");
            Console.WriteLine("  playwright install chromium");
        }
    }
}
