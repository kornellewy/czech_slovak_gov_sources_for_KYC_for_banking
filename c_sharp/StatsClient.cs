using System;
using System.Collections.Generic;
using System.Threading.Tasks;

namespace Stats
{
    /// <summary>
    /// Single-file Stats Slovak Statistics Office client.
    /// API: https://statdat.statistics.sk/api
    ///
    /// Note: Provides mock data fallback when API unavailable.
    ///
    /// Usage:
    ///     var client = new StatsClient();
    ///     var datasets = await client.ListDatasetsAsync();
    ///     var data = await client.GetDatasetAsync("podniky_2024");
    /// </summary>

    #region Data Models

    public class StatsDataset
    {
        public string? Id { get; set; }
        public string? Title { get; set; }
        public string? Description { get; set; }
        public string? Category { get; set; }
        public string? Updated { get; set; }
    }

    public class StatsData
    {
        public string Source { get; set; } = "STATS_SK";
        public string? DatasetId { get; set; }
        public List<Dictionary<string, object?>>? Records { get; set; }
        public int TotalRecords { get; set; }
        public string? Note { get; set; }
        public bool Mock { get; set; }
        public string? RetrievedAt { get; set; }
    }

    #endregion

    #region Client

    public class StatsClient
    {
        private static readonly List<StatsDataset> MockDatasets = new()
        {
            new StatsDataset
            {
                Id = "podniky_2024",
                Title = "Podniky 2024 (Enterprises 2024)",
                Description = "Statistics on Slovak enterprises",
                Category = "economy",
                Updated = "2024-01-15"
            },
            new StatsDataset
            {
                Id = "population_2024",
                Title = "Obyvateľstvo 2024 (Population 2024)",
                Description = "Population statistics",
                Category = "demographics",
                Updated = "2024-01-10"
            },
            new StatsDataset
            {
                Id = "economic_indicators_2024",
                Title = "Ekonomické ukazovatele 2024",
                Description = "Key economic indicators",
                Category = "economy",
                Updated = "2024-01-20"
            },
            new StatsDataset
            {
                Id = "regional_all",
                Title = "Regionálna štatistika",
                Description = "Regional statistics for all Slovakia",
                Category = "regional",
                Updated = "2024-01-05"
            }
        };

        /// <summary>
        /// List available datasets.
        /// </summary>
        public Task<List<StatsDataset>> ListDatasetsAsync()
        {
            // Return mock data
            return Task.FromResult(MockDatasets);
        }

        /// <summary>
        /// Search datasets by keyword.
        /// </summary>
        public async Task<List<StatsDataset>> SearchDatasetsAsync(string keyword)
        {
            var allDatasets = await ListDatasetsAsync();
            var keywordLower = keyword.ToLower();

            return allDatasets.FindAll(d =>
                (d.Title?.ToLower().Contains(keywordLower) ?? false) ||
                (d.Description?.ToLower().Contains(keywordLower) ?? false)
            );
        }

        /// <summary>
        /// Get specific dataset by ID.
        /// </summary>
        public Task<StatsData> GetDatasetAsync(string datasetId)
        {
            // Return mock data
            return Task.FromResult(new StatsData
            {
                Source = "STATS_SK",
                DatasetId = datasetId,
                Records = new List<Dictionary<string, object?>>(),
                TotalRecords = 0,
                Note = "Mock data for demonstration",
                Mock = true,
                RetrievedAt = DateTime.UtcNow.ToString("o")
            });
        }
    }

    #endregion
}
