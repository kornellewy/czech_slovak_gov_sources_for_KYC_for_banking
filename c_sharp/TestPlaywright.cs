using System;
using System.Threading.Tasks;
using BrowserAutomation;

namespace PlaywrightTest
{
    /// <summary>
    /// Test program for Playwright browser automation.
    ///
    /// Installation:
    ///     1. Add NuGet package: dotnet add package Microsoft.Playwright
    ///     2. Install browsers: playwright install
    ///     3. Run: dotnet run
    /// </summary>
    class Program
    {
        static async Task Main(string[] args)
        {
            Console.WriteLine("Playwright Browser Client Test");
            Console.WriteLine("==============================\n");

            // Test 1: Basic page fetch
            Console.WriteLine("Test 1: Fetching Justice.cz search page...");
            await TestJusticeCzFetch();

            // Test 2: With screenshot
            Console.WriteLine("\nTest 2: Fetching with screenshot...");
            await TestWithScreenshot();

            Console.WriteLine("\nAll tests completed!");
        }

        static async Task TestJusticeCzFetch()
        {
            using var browser = new PlaywrightBrowserClient(headless: true);

            var ico = "05984866";
            var url = $"https://or.justice.cz/ias/ui/rejstrik-$firma?ico={ico}";

            Console.WriteLine($"Fetching: {url}");

            try
            {
                var html = await browser.GetPageHtmlAsync(url, "table.result-details");
                var title = await browser.GetTitleAsync();

                Console.WriteLine($"✓ Page loaded: {title}");
                Console.WriteLine($"✓ HTML length: {html.Length:N0} characters");

                // Check for content
                if (html.Contains("DEVROCK"))
                {
                    Console.WriteLine("✓ Found company: DEVROCK a.s.");
                }

                // Check for result table
                if (html.Contains("result-details"))
                {
                    Console.WriteLine("✓ Found result table");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"✗ Error: {ex.Message}");
            }
        }

        static async Task TestWithScreenshot()
        {
            using var browser = new PlaywrightBrowserClient(headless: true);

            var ico = "06649114"; // Prusa Research
            var url = $"https://or.justice.cz/ias/ui/rejstrik-$firma?ico={ico}";

            Console.WriteLine($"Fetching: {url}");

            try
            {
                await browser.NavigateAndWaitAsync(url, "table.result-details");

                var screenshotPath = await browser.TakeScreenshotAsync($"justice_{ico}.png");
                if (screenshotPath != null)
                {
                    Console.WriteLine($"✓ Screenshot saved: {screenshotPath}");
                }

                var html = await browser.GetPageHtmlAsync(url);
                Console.WriteLine($"✓ HTML length: {html.Length:N0} characters");

                if (html.Contains("Prusa Research"))
                {
                    Console.WriteLine("✓ Found company: Prusa Research a.s.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"✗ Error: {ex.Message}");
            }
        }
    }
}
