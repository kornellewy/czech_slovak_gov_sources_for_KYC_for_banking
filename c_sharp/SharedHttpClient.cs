using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace SharedHttp
{
    #region Exceptions

    /// <summary>
    /// Exception thrown when HTTP request fails.
    /// </summary>
    public class ScraperHttpException : Exception
    {
        public HttpStatusCode StatusCode { get; }
        public string? Url { get; }

        public ScraperHttpException(string message, HttpStatusCode statusCode, string? url = null)
            : base(message)
        {
            StatusCode = statusCode;
            Url = url;
        }
    }

    #endregion

    #region HTTP Client

    /// <summary>
    /// Shared HTTP client with rate limiting for all scrapers.
    /// </summary>
    public class SharedHttpClient : IDisposable
    {
        private readonly HttpClient _httpClient;
        private readonly SemaphoreSlim _rateLimiter;
        private readonly int _requestIntervalMs;
        private DateTime _lastRequestTime = DateTime.MinValue;
        private readonly object _lockObject = new();

        public SharedHttpClient(int requestsPerMinute = 60, string userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        {
            _requestIntervalMs = 60000 / requestsPerMinute;
            _rateLimiter = new SemaphoreSlim(1, 1);

            var handler = new HttpClientHandler
            {
                AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate
            };

            _httpClient = new HttpClient(handler)
            {
                Timeout = TimeSpan.FromSeconds(30)
            };

            _httpClient.DefaultRequestHeaders.Add("User-Agent", userAgent);
            _httpClient.DefaultRequestHeaders.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        }

        /// <summary>
        /// Apply rate limiting before making a request.
        /// </summary>
        private async Task ApplyRateLimitAsync()
        {
            await _rateLimiter.WaitAsync();
            try
            {
                lock (_lockObject)
                {
                    var elapsed = DateTime.Now - _lastRequestTime;
                    if (elapsed.TotalMilliseconds < _requestIntervalMs)
                    {
                        var delay = _requestIntervalMs - (int)elapsed.TotalMilliseconds;
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

        /// <summary>
        /// Send GET request and return response as string.
        /// </summary>
        public async Task<string> GetStringAsync(string url, Dictionary<string, string>? headers = null)
        {
            await ApplyRateLimitAsync();

            using var request = new HttpRequestMessage(HttpMethod.Get, url);

            if (headers != null)
            {
                foreach (var header in headers)
                {
                    request.Headers.TryAddWithoutValidation(header.Key, header.Value);
                }
            }

            var response = await _httpClient.SendAsync(request);

            if (!response.IsSuccessStatusCode)
            {
                throw new ScraperHttpException(
                    $"HTTP request failed: {response.StatusCode}",
                    response.StatusCode,
                    url
                );
            }

            return await response.Content.ReadAsStringAsync();
        }

        /// <summary>
        /// Send GET request with Windows-1250 encoding support.
        /// </summary>
        public async Task<string> GetStringWindows1250Async(string url, Dictionary<string, string>? headers = null)
        {
            await ApplyRateLimitAsync();

            using var request = new HttpRequestMessage(HttpMethod.Get, url);

            if (headers != null)
            {
                foreach (var header in headers)
                {
                    request.Headers.TryAddWithoutValidation(header.Key, header.Value);
                }
            }

            var response = await _httpClient.SendAsync(request);

            if (!response.IsSuccessStatusCode)
            {
                throw new ScraperHttpException(
                    $"HTTP request failed: {response.StatusCode}",
                    response.StatusCode,
                    url
                );
            }

            var bytes = await response.Content.ReadAsByteArrayAsync();

            // Register Windows-1250 encoding
            Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);
            var encoding = Encoding.GetEncoding("windows-1250");

            return encoding.GetString(bytes);
        }

        /// <summary>
        /// Send GET request and return bytes.
        /// </summary>
        public async Task<byte[]> GetBytesAsync(string url, Dictionary<string, string>? headers = null)
        {
            await ApplyRateLimitAsync();

            using var request = new HttpRequestMessage(HttpMethod.Get, url);

            if (headers != null)
            {
                foreach (var header in headers)
                {
                    request.Headers.TryAddWithoutValidation(header.Key, header.Value);
                }
            }

            var response = await _httpClient.SendAsync(request);

            if (!response.IsSuccessStatusCode)
            {
                throw new ScraperHttpException(
                    $"HTTP request failed: {response.StatusCode}",
                    response.StatusCode,
                    url
                );
            }

            return await response.Content.ReadAsByteArrayAsync();
        }

        public void Dispose()
        {
            _httpClient.Dispose();
            _rateLimiter.Dispose();
        }
    }

    #endregion
}
