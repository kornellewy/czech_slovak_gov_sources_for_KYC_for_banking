using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using Microsoft.Playwright;

namespace BrowserAutomation
{
    /// <summary>
    /// Playwright-based browser automation client for dynamic websites.
    ///
    /// This client provides browser automation capabilities using Playwright for .NET.
    /// It's useful for scraping websites that require JavaScript rendering or have
    /// anti-bot protection that blocks simple HTTP requests.
    ///
    /// Usage:
    ///     using var browser = new PlaywrightBrowserClient(headless: true);
    ///     var html = await browser.GetPageHtmlAsync("https://example.com");
    ///
    /// Requirements:
    ///     1. Install Microsoft.Playwright NuGet package
    ///     2. Run 'playwright install' to download browser binaries
    ///
    /// Installation:
    ///     dotnet add package Microsoft.Playwright
    ///     playwright install
    /// </summary>
    public class PlaywrightBrowserClient : IDisposable
    {
        private readonly bool _headless;
        private IPlaywright? _playwright;
        private IBrowser? _browser;
        private IPage? _page;
        private IBrowserContext? _context;
        private bool _disposed;

        /// <summary>
        /// Default timeout in milliseconds for page operations.
        /// </summary>
        public const int DefaultTimeout = 30000;

        /// <summary>
        /// Screenshot directory for debugging.
        /// </summary>
        public string ScreenshotDir { get; set; } = Path.Combine(Directory.GetCurrentDirectory(), "screenshots");

        /// <summary>
        /// Whether Playwright is available (browsers installed).
        /// </summary>
        public bool IsAvailable { get; private set; }

        public PlaywrightBrowserClient(bool headless = true)
        {
            _headless = headless;
            InitializeAsync().GetAwaiter().GetResult();
        }

        /// <summary>
        /// Initialize Playwright and check if browsers are installed.
        /// </summary>
        private async Task InitializeAsync()
        {
            try
            {
                _playwright = await Playwright.CreateAsync();
                IsAvailable = true;

                // Create screenshot directory
                if (!Directory.Exists(ScreenshotDir))
                {
                    Directory.CreateDirectory(ScreenshotDir);
                }
            }
            catch (Exception ex)
            {
                IsAvailable = false;
                throw new InvalidOperationException(
                    "Playwright is not available. Install with: dotnet add package Microsoft.Playwright && playwright install",
                    ex);
            }
        }

        /// <summary>
        /// Launch browser and create a new page with proper headers.
        /// </summary>
        private async Task EnsureBrowserAsync()
        {
            if (_browser != null && _page != null)
                return;

            if (_playwright == null)
            {
                await InitializeAsync();
            }

            // Launch browser
            _browser = await _playwright!.Chromium.LaunchAsync(new BrowserTypeLaunchOptions
            {
                Headless = _headless,
                Args = new[]
                {
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                }
            });

            // Create context with realistic settings
            _context = await _browser.NewContextAsync(new BrowserNewContextOptions
            {
                UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ViewportSize = new ViewportSize { Width = 1920, Height = 1080 },
                Locale = "cs-CZ",
                TimeZoneId = "Europe/Prague",
            });

            // Add extra headers to avoid bot detection
            await _context.SetExtraHTTPHeadersAsync(new Dictionary<string, string>
            {
                ["Accept-Language"] = "cs-CZ,cs;q=0.9,en;q=0.8",
                ["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                ["Accept-Encoding"] = "gzip, deflate, br",
                ["DNT"] = "1",
                ["Connection"] = "keep-alive",
                ["Upgrade-Insecure-Requests"] = "1"
            });

            // Create page
            _page = await _context.NewPageAsync();
            _page.SetDefaultTimeout(DefaultTimeout);
        }

        /// <summary>
        /// Navigate to URL and get page HTML content.
        /// </summary>
        /// <param name="url">URL to navigate to</param>
        /// <param name="waitSelector">Optional CSS selector to wait for</param>
        /// <param name="waitUntil">Navigation wait condition (default: networkidle)</param>
        /// <returns>HTML content of the page</returns>
        public async Task<string> GetPageHtmlAsync(
            string url,
            string? waitSelector = null,
            WaitUntilState waitUntil = WaitUntilState.NetworkIdle)
        {
            await EnsureBrowserAsync();

            await _page!.GotoAsync(url, new PageGotoOptions
            {
                WaitUntil = waitUntil,
                Timeout = DefaultTimeout
            });

            // Wait for specific selector if provided
            if (!string.IsNullOrEmpty(waitSelector))
            {
                await _page.WaitForSelectorAsync(waitSelector, new PageWaitForSelectorOptions
                {
                    Timeout = DefaultTimeout
                });
            }

            return await _page.ContentAsync();
        }

        /// <summary>
        /// Take a screenshot of the current page.
        /// </summary>
        /// <param name="filename">Screenshot filename (null for auto-generated)</param>
        /// <param name="fullPage">Whether to capture full scrollable page</param>
        /// <returns>Path to saved screenshot</returns>
        public async Task<string?> TakeScreenshotAsync(string? filename = null, bool fullPage = true)
        {
            if (_page == null)
                return null;

            try
            {
                if (string.IsNullOrEmpty(filename))
                {
                    filename = $"screenshot_{DateTime.Now:yyyyMMdd_HHmmss}.png";
                }

                var filepath = Path.Combine(ScreenshotDir, filename);
                await _page.ScreenshotAsync(new PageScreenshotOptions
                {
                    Path = filepath,
                    FullPage = fullPage
                });

                return filepath;
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Execute JavaScript in the browser context.
        /// </summary>
        /// <param name="script">JavaScript code to execute</param>
        /// <returns>Result of execution</returns>
        public async Task<object?> ExecuteJavaScriptAsync(string script)
        {
            await EnsureBrowserAsync();
            return await _page!.EvaluateAsync(script);
        }

        /// <summary>
        /// Wait for a specific selector to appear on the page.
        /// </summary>
        /// <param name="selector">CSS selector</param>
        /// <param name="timeout">Timeout in milliseconds</param>
        /// <returns>True if found, false if timeout</returns>
        public async Task<bool> WaitForContentAsync(string selector, int timeout = DefaultTimeout)
        {
            await EnsureBrowserAsync();
            try
            {
                await _page!.WaitForSelectorAsync(selector, new PageWaitForSelectorOptions
                {
                    Timeout = timeout
                });
                return true;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Scroll to bottom of page (for infinite scroll pages).
        /// </summary>
        /// <param name="maxScrolls">Maximum number of scroll attempts</param>
        /// <param name="scrollDelay">Delay between scrolls in ms</param>
        public async Task ScrollAndWaitAsync(int maxScrolls = 5, int scrollDelay = 500)
        {
            await EnsureBrowserAsync();

            for (int i = 0; i < maxScrolls; i++)
            {
                var oldHeight = await _page!.EvaluateAsync<long>("document.body.scrollHeight");
                await _page.EvaluateAsync("window.scrollTo(0, document.body.scrollHeight)");
                await Task.Delay(scrollDelay);

                var newHeight = await _page.EvaluateAsync<long>("document.body.scrollHeight");
                if (newHeight == oldHeight)
                    break;
            }
        }

        /// <summary>
        /// Extract text content from matching elements.
        /// </summary>
        /// <param name="selector">CSS selector</param>
        /// <param name="attribute">Optional attribute name (null returns text)</param>
        /// <returns>List of text/attribute values</returns>
        public async Task<List<string>> ExtractContentAsync(string selector, string? attribute = null)
        {
            await EnsureBrowserAsync();

            var elements = await _page!.QuerySelectorAllAsync(selector);
            var results = new List<string>();

            foreach (var element in elements)
            {
                if (string.IsNullOrEmpty(attribute))
                {
                    results.Add(await element.TextContentAsync() ?? "");
                }
                else
                {
                    results.Add(await element.GetAttributeAsync(attribute) ?? "");
                }
            }

            return results;
        }

        /// <summary>
        /// Get page title.
        /// </summary>
        public async Task<string> GetTitleAsync()
        {
            await EnsureBrowserAsync();
            return await _page!.TitleAsync();
        }

        /// <summary>
        /// Navigate and wait with automatic screenshot on error.
        /// </summary>
        public async Task<bool> NavigateAndWaitAsync(
            string url,
            string? waitSelector = null,
            WaitUntilState waitUntil = WaitUntilState.NetworkIdle)
        {
            try
            {
                await EnsureBrowserAsync();
                await _page!.GotoAsync(url, new PageGotoOptions
                {
                    WaitUntil = waitUntil,
                    Timeout = DefaultTimeout
                });

                if (!string.IsNullOrEmpty(waitSelector))
                {
                    return await WaitForContentAsync(waitSelector);
                }

                return true;
            }
            catch
            {
                // Take screenshot for debugging
                await TakeScreenshotAsync($"error_{DateTime.Now:yyyyMMdd_HHmmss}.png");
                return false;
            }
        }

        /// <summary>
        /// Close browser and cleanup resources.
        /// </summary>
        public void Dispose()
        {
            if (_disposed)
                return;

            _page?.CloseAsync().GetAwaiter().GetResult();
            _context?.CloseAsync().GetAwaiter().GetResult();
            _browser?.CloseAsync().GetAwaiter().GetResult();
            _playwright?.Dispose();

            _disposed = true;
        }

        /// <summary>
        /// Finalizer to ensure cleanup.
        /// </summary>
        ~PlaywrightBrowserClient()
        {
            Dispose();
        }
    }

    /// <summary>
    /// Extension methods for Playwright browser client.
    /// </summary>
    public static class PlaywrightExtensions
    {
        /// <summary>
        /// Get page content as text (innerText).
        /// </summary>
        public static async Task<string> GetPageTextAsync(this IPage page)
        {
            return await page.EvaluateAsync<string>("() => document.body.innerText");
        }

        /// <summary>
        /// Check if selector exists on page.
        /// </summary>
        public static async Task<bool> HasSelectorAsync(this IPage page, string selector)
        {
            return await page.QuerySelectorAsync(selector) != null;
        }

        /// <summary>
        /// Get all links with href attribute from page.
        /// </summary>
        public static async Task<List<(string text, string href)>> GetAllLinksAsync(this IPage page)
        {
            var elements = await page.QuerySelectorAllAsync("a[href]");
            var links = new List<(string, string)>();

            foreach (var element in elements)
            {
                var text = await element.TextContentAsync() ?? "";
                var href = await element.GetAttributeAsync("href") ?? "";
                links.Add((text.Trim(), href));
            }

            return links;
        }
    }
}
