using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using System.Xml.Linq;
using UnifiedOutput;

namespace Justice
{
    /// <summary>
    /// Justice Czech Commercial Register client.
    /// Website: https://or.justice.cz
    ///
    /// Implementation based on patterns from: https://github.com/lubosdz/parser-justice-cz
    ///
    /// Search endpoints:
    /// - By ICO: https://or.justice.cz/ias/ui/rejstrik-firma?ico={ICO}
    /// - By name: https://or.justice.cz/ias/ui/rejstrik-firma?nazev={name}
    ///
    /// HTML Structure (from parser-justice-cz):
    /// - Table with class "result-details"
    /// - Row 1: td[1]=name, td[2]=ICO
    /// - Row 2: td[1]=file_number, td[2]=date_established
    /// - Row 3: td[1]=address
    /// - Links in ../../ul[1]/li/a (3 links: platny, uplny, sbirkaListin)
    ///
    /// Output: UnifiedData format with entity, metadata sections.
    ///
    /// Usage:
    ///     var client = new JusticeClient();
    ///     var result = await client.SearchByICOAsync("44315945");
    ///     Console.WriteLine(result.ToJson());
    /// </summary>

    #region Data Models

    /// <summary>
    /// Justice.cz entity response data (matching parser-justice-cz format).
    /// </summary>
    public class JusticeEntity
    {
        public string? Name { get; set; }
        public string? Ico { get; set; }
        public string? City { get; set; }           // Shortened city name
        public string? AddrCity { get; set; }      // Full city name
        public string? AddrZip { get; set; }       // Postal code
        public string? AddrStreetNr { get; set; }  // Street and number
        public string? AddrFull { get; set; }      // Full address
        public string? DenZapisuNum { get; set; }  // Date in ISO format
        public string? DenZapisuTxt { get; set; }  // Date in original text
        public string? SpisZnacka { get; set; }    // File number
        public string? UrlPlatnych { get; set; }   // Valid version URL
        public string? UrlUplny { get; set; }      // Full version URL
        public string? UrlSbirkaListin { get; set; } // Documents collection URL
    }

    #endregion

    #region Client

    /// <summary>
    /// Justice Czech Commercial Register client with web scraping and unified output format.
    /// Based on parser-justice-cz PHP implementation.
    /// </summary>
    public class JusticeClient : IDisposable
    {
        private const string BaseUrl = "https://or.justice.cz";
        // URL pattern from parser-justice-cz: URL_SERVER = 'https://or.justice.cz/ias/ui/rejstrik-$firma'
        private const string SearchUrl = "https://or.justice.cz/ias/ui/rejstrik-$firma";
        private const string Source = "JUSTICE_CZ";
        private const int RequestsPerMinute = 30;

        private readonly HttpClient _httpClient;
        private readonly SemaphoreSlim _rateLimiter;
        private DateTime _lastRequestTime = DateTime.MinValue;
        private readonly object _lockObject = new();

        // Czech month names for date parsing (from parser-justice-cz)
        private static readonly Dictionary<string, int> CzechMonths = new()
        {
            { "leden", 1 }, { "ledna", 1 },
            { "únor", 2 }, { "února", 2 },
            { "březen", 3 }, { "března", 3 },
            { "duben", 4 }, { "dubna", 4 },
            { "květen", 5 }, { "května", 5 },
            { "červen", 6 }, { "června", 6 },
            { "červenec", 7 }, { "července", 7 },
            { "srpen", 8 }, { "srpna", 8 },
            { "září", 9 },
            { "říjen", 10 }, { "října", 10 },
            { "listopad", 11 }, { "listopadu", 11 },
            { "prosinec", 12 }, { "prosince", 12 }
        };

        public JusticeClient()
        {
            var handler = new HttpClientHandler
            {
                AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate
            };

            _httpClient = new HttpClient(handler)
            {
                Timeout = TimeSpan.FromSeconds(30)
            };

            // Justice.cz requires proper browser headers to avoid blocking
            SetupBrowserHeaders();

            _rateLimiter = new SemaphoreSlim(1, 1);
        }

        /// <summary>
        /// Configure proper browser headers for Justice.cz to avoid immediate blocking.
        /// The library ensures valid browser headers (User-Agent) are sent, otherwise Justice.cz
        /// blocks the request immediately.
        /// </summary>
        private void SetupBrowserHeaders()
        {
            _httpClient.DefaultRequestHeaders.Clear();
            _httpClient.DefaultRequestHeaders.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");
            _httpClient.DefaultRequestHeaders.Add("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8");
            _httpClient.DefaultRequestHeaders.Add("Accept-Language", "cs-CZ,cs;q=0.9,en;q=0.8");
            _httpClient.DefaultRequestHeaders.Add("Accept-Encoding", "gzip, deflate, br");
            _httpClient.DefaultRequestHeaders.Add("DNT", "1");
            _httpClient.DefaultRequestHeaders.Add("Connection", "keep-alive");
            _httpClient.DefaultRequestHeaders.Add("Upgrade-Insecure-Requests", "1");
            _httpClient.DefaultRequestHeaders.Add("Sec-Fetch-Dest", "document");
            _httpClient.DefaultRequestHeaders.Add("Sec-Fetch-Mode", "navigate");
            _httpClient.DefaultRequestHeaders.Add("Sec-Fetch-Site", "none");
            _httpClient.DefaultRequestHeaders.Add("Cache-Control", "max-age=0");
        }

        /// <summary>
        /// Search company by ICO and return unified output format.
        /// Matches parser-justice-cz findByIco/getDetailByICO pattern.
        /// </summary>
        public async Task<UnifiedData?> SearchByICOAsync(string ico)
        {
            await ApplyRateLimitAsync();

            try
            {
                var cleanIco = Regex.Replace(ico ?? "", @"[^\d]", "");

                if (!Regex.IsMatch(cleanIco, @"^\d{8}$"))
                {
                    return null;
                }

                // Exact pattern from parser-justice-cz: URL_SERVER.'?ico='.$ico
                var url = $"{SearchUrl}?ico={cleanIco}";
                var html = await _httpClient.GetStringAsync(url);

                var results = ExtractSubjects(html);

                if (results.Count > 0)
                {
                    return results[0];
                }

                // Fallback to mock data
                return GetMockData(cleanIco);
            }
            catch (HttpRequestException)
            {
                return GetMockData(ico);
            }
        }

        /// <summary>
        /// Search companies by name and return list of unified outputs.
        /// Matches parser-justice-cz findByNazev pattern.
        /// </summary>
        public async Task<List<UnifiedData>> SearchByNameAsync(string name)
        {
            await ApplyRateLimitAsync();

            try
            {
                var trimmedName = (name ?? "").Trim();

                // Check if searching by ICO (8 digits)
                if (Regex.IsMatch(trimmedName, @"^\d{8}$"))
                {
                    var result = await SearchByICOAsync(trimmedName);
                    if (result != null)
                    {
                        return new List<UnifiedData> { result };
                    }
                }

                // Justice requires at least 3 chars (from parser-justice-cz)
                if (trimmedName.Length < 3)
                {
                    return new List<UnifiedData>();
                }

                // Exact pattern from parser-justice-cz: URL_SERVER.'?nazev='.urlencode($nazev)
                var url = $"{SearchUrl}?nazev={Uri.EscapeDataString(trimmedName)}";
                var html = await _httpClient.GetStringAsync(url);

                return ExtractSubjects(html);
            }
            catch (HttpRequestException)
            {
                return new List<UnifiedData>();
            }
        }

        /// <summary>
        /// Extract subjects from Justice.cz HTML response.
        /// Matches parser-justice-cz extractSubjects function.
        ///
        /// XPath pattern: //table[@class="result-details"]/tbody
        /// Row 1: tr[1]/td[1]=name, tr[1]/td[2]=ICO
        /// Row 2: tr[2]/td[1]=file_number, tr[2]/td[2]=date_established
        /// Row 3: tr[3]/td[1]=address
        /// Links: ../../ul[1]/li/a (3 links)
        /// </summary>
        private List<UnifiedData> ExtractSubjects(string html)
        {
            var results = new List<UnifiedData>();

            try
            {
                var doc = XDocument.Parse($"<root>{PreprocessHtml(html)}</root>");
                var ns = XNamespace.Get("http://www.w3.org/1999/xhtml");

                // Find table with class "result-details"
                var tables = doc.Descendants(ns + "table")
                    .Where(t => t.Attributes("class").Any(a => a.Value?.Contains("result-details") == true));

                foreach (var table in tables)
                {
                    var tbody = table.Element(ns + "tbody");
                    var rows = (tbody ?? table).Descendants(ns + "tr").ToList();

                    // Process rows in groups of 3 (each company spans 3 rows)
                    for (int i = 0; i < rows.Count - 2; i += 3)
                    {
                        var row1 = rows[i];
                        var row2 = rows[i + 1];
                        var row3 = rows[i + 2];

                        var cells1 = row1.Descendants(ns + "td").ToList();
                        if (cells1.Count < 2)
                            continue;

                        // Row 1: name (td[1]), ICO (td[2])
                        var name = TrimQuotes(cells1[0].Value);
                        name = Regex.Replace(name, @"\s+", " ").Trim();

                        var ico = Regex.Replace(cells1[1].Value ?? "", @"[^\d]", "");
                        if (string.IsNullOrEmpty(ico) || ico.Length != 8)
                            continue;

                        // Row 2: file_number (td[1]), date_established (td[2])
                        var cells2 = row2.Descendants(ns + "td").ToList();
                        var spisZnacka = cells2.Count > 0 ? TrimQuotes(cells2[0].Value) : "";
                        var dateText = cells2.Count > 1 ? TrimQuotes(cells2[1].Value) : "";
                        var denZapisuTxt = dateText;
                        var denZapisuNum = ParseCzechDate(dateText);

                        // Row 3: address (td[1])
                        var cells3 = row3.Descendants(ns + "td").ToList();
                        string city = "", addrCity = "", addrZip = "", addrStreetNr = "", addrFull = "";

                        if (cells3.Count > 0)
                        {
                            var addr = TrimQuotes(cells3[0].Value);

                            // Pattern 1: "Příborská 597, Místek, 738 01 Frýdek-Místek"
                            var match1 = Regex.Match(addr, @",\s*(\d{3}\s*\d{2})\s+(.+)$");
                            if (match1.Success)
                            {
                                addrZip = Regex.Replace(match1.Groups[1].Value, @"\s", "");
                                addrCity = match1.Groups[2].Value.Trim();
                                var parts = addr.Split(',');
                                addrStreetNr = parts.Length > 0 ? parts[0] : "";
                                city = ShortenCity(addrCity);
                                addrFull = addr;
                            }
                            // Pattern 2: "Řevnice, ČSLA 118, okres Praha-západ, PSČ 25230"
                            else if (addr.Contains("PSČ"))
                            {
                                var match2 = Regex.Match(addr, @",\s*PSČ\s+(\d{3}\s*\d{2})$");
                                if (match2.Success)
                                {
                                    addrZip = Regex.Replace(match2.Groups[1].Value, @"\s", "");
                                    var parts = addr.Split(',');
                                    city = parts.Length > 0 ? parts[0].Trim() : "";
                                    addrCity = city;
                                    addrStreetNr = parts.Length > 1 ? string.Join(", ", parts.Skip(1)).Trim() : "";
                                    city = ShortenCity(city);
                                    addrFull = addr;
                                }
                            }
                            // Pattern 3: Without PSC
                            else if (!Regex.IsMatch(addr, @"\d{3}\s*\d{2}"))
                            {
                                var parts = addr.Split(',');
                                if (parts.Length >= 2)
                                {
                                    city = parts[0].Trim();
                                    addrStreetNr = string.Join(", ", parts.Skip(1)).Trim();
                                    addrCity = city;
                                    city = ShortenCity(city);
                                }
                                else
                                {
                                    city = addr;
                                    addrCity = addr;
                                }
                                addrFull = addr;
                            }
                        }

                        // Look for detail links in ul/li/a structure (../../ul[1]/li/a)
                        string urlPlatnych = "", urlUplny = "", urlSbirkaListin = "";

                        // Find ul elements with links
                        var ulElements = row3.Parent?.Descendants(ns + "ul").FirstOrDefault();
                        if (ulElements != null)
                        {
                            var links = ulElements.Descendants(ns + "a").ToList();
                            if (links.Count >= 3)
                            {
                                urlPlatnych = NormalizeUrl(links[0].Attribute("href")?.Value ?? "");
                                urlUplny = NormalizeUrl(links[1].Attribute("href")?.Value ?? "");
                                urlSbirkaListin = NormalizeUrl(links[2].Attribute("href")?.Value ?? "");
                            }
                        }

                        // Build entity
                        var entity = new UnifiedEntity
                        {
                            IcoRegistry = ico,
                            CompanyNameRegistry = name,
                            Status = "active",
                            IncorporationDate = denZapisuNum,
                            RegisteredAddress = !string.IsNullOrEmpty(addrFull) ? new UnifiedAddress
                            {
                                FullAddress = addrFull,
                                StreetNumber = addrStreetNr,
                                City = addrCity,
                                PostalCode = addrZip,
                                Country = "Česká republika",
                                CountryCode = "CZ"
                            } : null
                        };

                        var registerUrl = !string.IsNullOrEmpty(urlPlatnych) ? urlPlatnych : $"{SearchUrl}?ico={ico}";

                        var metadata = new UnifiedMetadata
                        {
                            Source = Source,
                            RegisterName = OutputNormalizer.GetRegisterName(Source),
                            RegisterUrl = registerUrl,
                            RetrievedAt = DateTime.UtcNow.ToString("o"),
                            IsMock = false
                        };

                        var result = new UnifiedData
                        {
                            Entity = entity,
                            Holders = new List<UnifiedHolder>(),
                            Metadata = metadata
                        };

                        // Add additional data (from parser-justice-cz format)
                        result.AdditionalData = new Dictionary<string, object>
                        {
                            { "file_number", spisZnacka },
                            { "date_registered_text", denZapisuTxt },
                            { "url_platny", urlPlatnych },
                            { "url_uplny", urlUplny },
                            { "url_sbírka_listin", urlSbirkaListin }
                        };

                        results.Add(result);
                    }
                }
            }
            catch
            {
                // Return empty list on parse error
            }

            return results;
        }

        /// <summary>
        /// Parse Czech date format to ISO format.
        /// Matches parser-justice-cz numerizeMonth pattern: "30. ledna 2000" -> "2000-01-30"
        /// </summary>
        private string? ParseCzechDate(string text)
        {
            var match = Regex.Match(text, @"(\d{1,2})\.\s+([a-zA-ZáčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]+)\s+(\d{4})");
            if (match.Success)
            {
                var day = int.Parse(match.Groups[1].Value);
                var monthName = match.Groups[2].Value.ToLower();
                var year = int.Parse(match.Groups[3].Value);

                if (NumerizeMonth(monthName) is int month)
                {
                    try
                    {
                        return $"{year:0000}-{month:00}-{day:00}";
                    }
                    catch
                    {
                        // Invalid date
                    }
                }
            }

            return null;
        }

        /// <summary>
        /// Convert Czech month name to number.
        /// Matches parser-justice-cz numerizeMonth function.
        /// </summary>
        private int? NumerizeMonth(string month)
        {
            month = month.ToLower().Trim();

            foreach (var kvp in CzechMonths)
            {
                if (month.StartsWith(kvp.Key.Substring(0, Math.Min(4, kvp.Key.Length))))
                {
                    return kvp.Value;
                }
            }

            return null;
        }

        /// <summary>
        /// Shorten city name (e.g., "Praha 10" -> "Praha").
        /// Matches parser-justice-cz city shortening pattern.
        /// </summary>
        private string ShortenCity(string city)
        {
            if (string.IsNullOrEmpty(city))
                return city;

            // "Praha 10 - Dolní Měcholupy" -> "Praha 10"
            city = city.Split('-')[0].Trim();

            // "Praha 5" -> "Praha"
            city = Regex.Replace(city, @"\d+$", "").Trim();

            return city;
        }

        /// <summary>
        /// Normalize relative URL to absolute URL.
        /// Matches parser-justice-cz normalizeUrl function.
        /// </summary>
        private string NormalizeUrl(string url)
        {
            if (string.IsNullOrEmpty(url))
                return string.Empty;

            // Remove leading ./ or /
            if (url.StartsWith("./"))
                url = url.Substring(2);
            else if (url.StartsWith("/"))
                url = url.Substring(1);

            // Build absolute URL
            url = $"{BaseUrl}/ias/ui/{url}";

            // Remove session hash (&sp=...)
            url = url.Split("&sp=")[0];

            return url;
        }

        /// <summary>
        /// Remove quotes from text.
        /// Matches parser-justice-cz trimQuotes function.
        /// </summary>
        private string TrimQuotes(string text)
        {
            return text?.Trim().Trim('"').Trim('\'') ?? "";
        }

        /// <summary>
        /// Preprocess HTML for parsing.
        /// </summary>
        private string PreprocessHtml(string html)
        {
            // Remove script tags that might interfere with parsing
            html = Regex.Replace(html, @"<script[^>]*>.*?</script>", "", RegexOptions.Singleline | RegexOptions.IgnoreCase);
            // Replace &nbsp; with space
            html = html.Replace("&nbsp;", " ");
            // Normalize whitespace
            html = Regex.Replace(html, @"\s+", " ");
            return html;
        }

        private UnifiedData? GetMockData(string ico)
        {
            var mockData = new Dictionary<string, JusticeEntity>
            {
                {
                    "05984866", new JusticeEntity
                    {
                        Name = "DEVROCK a.s.",
                        Ico = "05984866",
                        City = "Praha",
                        AddrCity = "Praha 1",
                        AddrZip = "11000",
                        AddrStreetNr = "Václavské náměstí 2132/47",
                        AddrFull = "Václavské náměstí 2132/47, Nové Město, 11000 Praha 1",
                        DenZapisuNum = "2017-04-03",
                        DenZapisuTxt = "3. dubna 2017",
                        SpisZnacka = "B 22379/MSPH"
                    }
                },
                {
                    "44315945", new JusticeEntity
                    {
                        Name = "Jana Kudláčková",
                        Ico = "44315945",
                        City = "Praha",
                        AddrCity = "Praha 4",
                        AddrZip = "14900",
                        AddrStreetNr = "Filipova 2016",
                        AddrFull = "Filipova 2016, PSČ 14900",
                        DenZapisuNum = "1992-08-26",
                        DenZapisuTxt = "26. srpna 1992",
                        SpisZnacka = "A 6887 vedená u Městského soudu v Praze"
                    }
                },
                {
                    "06649114", new JusticeEntity
                    {
                        Name = "Prusa Research a.s.",
                        Ico = "06649114",
                        City = "Praha",
                        AddrCity = "Praha",
                        AddrZip = "17000",
                        AddrStreetNr = "Vlašská 344/15",
                        AddrFull = "Vlašská 344/15, 170 00 Praha 7",
                        DenZapisuNum = "2017-09-14",
                        DenZapisuTxt = "14. září 2017",
                        SpisZnacka = "B 28291"
                    }
                },
                {
                    "00216305", new JusticeEntity
                    {
                        Name = "Česká pošta, s.p.",
                        Ico = "00216305",
                        City = "Praha",
                        AddrCity = "Praha 1",
                        AddrZip = "11499",
                        AddrStreetNr = "Poštovní 959/9",
                        AddrFull = "Poštovní 959/9, 114 99 Praha 1",
                        DenZapisuNum = "1993-01-01",
                        SpisZnacka = "B 5678"
                    }
                },
                {
                    "00006947", new JusticeEntity
                    {
                        Name = "Ministerstvo financí",
                        Ico = "00006947",
                        City = "Praha",
                        AddrCity = "Praha 1",
                        AddrZip = "11100",
                        AddrStreetNr = "Letenská 15",
                        AddrFull = "Letenská 15, 111 00 Praha 1",
                        DenZapisuNum = "1993-01-01",
                        SpisZnacka = "A 123"
                    }
                }
            };

            if (mockData.TryGetValue(ico, out var data))
            {
                var entity = new UnifiedEntity
                {
                    IcoRegistry = data.Ico ?? ico,
                    CompanyNameRegistry = data.Name,
                    Status = "active",
                    IncorporationDate = data.DenZapisuNum,
                    RegisteredAddress = new UnifiedAddress
                    {
                        FullAddress = data.AddrFull,
                        StreetNumber = data.AddrStreetNr,
                        City = data.AddrCity,
                        PostalCode = data.AddrZip,
                        Country = "Česká republika",
                        CountryCode = "CZ"
                    }
                };

                var metadata = new UnifiedMetadata
                {
                    Source = Source,
                    RegisterName = OutputNormalizer.GetRegisterName(Source),
                    RegisterUrl = $"{SearchUrl}?ico={data.Ico}",
                    RetrievedAt = DateTime.UtcNow.ToString("o"),
                    IsMock = true
                };

                var result = new UnifiedData
                {
                    Entity = entity,
                    Holders = new List<UnifiedHolder>(),
                    Metadata = metadata
                };

                result.AdditionalData = new Dictionary<string, object>
                {
                    { "file_number", data.SpisZnacka },
                    { "date_registered_text", data.DenZapisuTxt }
                };

                return result;
            }

            return null;
        }

        private async Task ApplyRateLimitAsync()
        {
            await _rateLimiter.WaitAsync();
            try
            {
                lock (_lockObject)
                {
                    var elapsed = DateTime.Now - _lastRequestTime;
                    var intervalMs = 60000 / RequestsPerMinute;

                    if (elapsed.TotalMilliseconds < intervalMs)
                    {
                        var delay = intervalMs - (int)elapsed.TotalMilliseconds;
                        Thread.Sleep(delay);
                    }
                    _lastRequestTime = DateTime.Now;
                }
            }
            finally
            {
                _rateLimiter.Release();
            }
        }

        public void Dispose()
        {
            _httpClient.Dispose();
            _rateLimiter.Dispose();
        }
    }

    #endregion
}
