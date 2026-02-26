using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace UnifiedOutput
{
    /// <summary>
    /// Enhanced logger for scrapers with structured logging support.
    /// Provides consistent logging format across all scrapers.
    /// </summary>
    public class ScraperLogger
    {
        private readonly string _sourceName;
        private readonly bool _enableConsole;
        private readonly bool _enableDebug;

        // Custom log level for maintenance
        public const int MaintenanceLevel = 25;  // Between Warning and Info

        public ScraperLogger(string sourceName, bool enableConsole = true, bool enableDebug = false)
        {
            _sourceName = sourceName;
            _enableConsole = enableConsole;
            _enableDebug = enableDebug;
        }

        public void Debug(string message)
        {
            if (_enableDebug)
                Log("DEBUG", message);
        }

        public void Info(string message)
        {
            Log("INFO", message);
        }

        public void Warning(string message)
        {
            Log("WARNING", message);
        }

        public void Error(string message, Exception? ex = null)
        {
            if (ex != null)
            {
                Log("ERROR", $"{message}: {ex.Message}");
            }
            else
            {
                Log("ERROR", message);
            }
        }

        public void Maintenance(string message)
        {
            Log("MAINTENANCE", message);
        }

        public void Critical(string message)
        {
            Log("CRITICAL", message);
        }

        private void Log(string level, string message)
        {
            if (_enableConsole)
            {
                var timestamp = DateTime.UtcNow.ToString("HH:mm:ss.fff");
                Console.WriteLine($"[{timestamp}] {_sourceName} | {level,-5} | {message}");
            }
        }

        // Context-specific logging methods

        /// <summary>
        /// Log HTTP request.
        /// </summary>
        public void LogRequest(string method, string url, Dictionary<string, object>? context = null)
        {
            Debug($"{method} {url}");
            if (context != null && _enableDebug)
            {
                foreach (var kvp in context)
                {
                    Debug($"  {kvp.Key}: {kvp.Value}");
                }
            }
        }

        /// <summary>
        /// Log HTTP response with timing.
        /// </summary>
        public void LogResponse(string url, int statusCode, double durationMs)
        {
            string statusIcon = statusCode >= 400 ? "❌" : "✅";
            Debug($"{statusIcon} {statusCode} from {url} ({durationMs:F0}ms)");
        }

        /// <summary>
        /// Log parse operation.
        /// </summary>
        public void LogParseStart(string dataSource)
        {
            Debug($"Parsing {dataSource}...");
        }

        /// <summary>
        /// Log parse completion.
        /// </summary>
        public void LogParseComplete(string dataSource, int itemsFound = 0)
        {
            Info($"Parsed {dataSource}: {itemsFound} item(s)");
        }

        /// <summary>
        /// Log maintenance detected.
        /// </summary>
        public void LogMaintenance(string source = null)
        {
            var src = source ?? _sourceName;
            Maintenance($"{src} is under maintenance");
        }

        /// <summary>
        /// Log rate limit delay.
        /// </summary>
        public void LogRateLimit(double delaySeconds)
        {
            Debug($"Rate limit: waiting {delaySeconds:F1}s");
        }

        /// <summary>
        /// Log mock data fallback.
        /// </summary>
        public void LogMockFallback(string reason)
        {
            Warning($"Using mock data: {reason}");
        }

        /// <summary>
        /// Log search start.
        /// </summary>
        public void LogSearchStart(string identifier = null, string searchType = "by_id")
        {
            Info($"Search started: {searchType} = {identifier ?? "N/A"}");
        }

        /// <summary>
        /// Log search complete.
        /// </summary>
        public void LogSearchComplete(int resultsCount, string identifier = null)
        {
            if (identifier != null)
            {
                Info($"Search complete for {identifier}: {resultsCount} result(s)");
            }
            else
            {
                Info($"Search complete: {resultsCount} result(s)");
            }
        }

        /// <summary>
        /// Log error with context.
        /// </summary>
        public void LogError(string operation, Exception ex, object context = null)
        {
            Error($"[{operation}] {ex.Message}");
            if (context != null && _enableDebug)
            {
                Error($"  Context: {context}");
            }
        }

        /// <summary>
        /// Log save operation.
        /// </summary>
        public void LogSaveResult(string filename)
        {
            Info($"Saved result: {filename}");
        }

        /// <summary>
        /// Create a timed operation context.
        /// </summary>
        public TimedOperation BeginTimedOperation(string operationName)
        {
            return new TimedOperation(this, operationName);
        }
    }

    /// <summary>
    /// Context manager for timing operations.
    /// </summary>
    public class TimedOperation : IDisposable
    {
        private readonly ScraperLogger _logger;
        private readonly string _operationName;
        private readonly Stopwatch _stopwatch;
        private bool _disposed = false;

        public TimedOperation(ScraperLogger logger, string operationName)
        {
            _logger = logger;
            _operationName = operationName;
            _stopwatch = Stopwatch.StartNew();
            _logger.Debug($"{operationName} started");
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                _stopwatch.Stop();
                var durationMs = _stopwatch.Elapsed.TotalMilliseconds;
                _logger.Debug($"{_operationName} completed ({durationMs:F0}ms)");
                _disposed = true;
            }
        }
    }
}
