"""JSON file handler for saving and loading scraper data."""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from config.constants import (
    OUTPUT_DIR, ARES_OUTPUT_DIR, ORSR_OUTPUT_DIR, STATS_OUTPUT_DIR,
    JUSTICE_OUTPUT_DIR, RPO_OUTPUT_DIR, RPVS_OUTPUT_DIR,
    FINANCNA_OUTPUT_DIR, ESM_OUTPUT_DIR
)


class JSONHandler:
    """Handles JSON file operations for scraper output.

    Example:
        handler = JSONHandler()
        handler.save(data, "company.json", "ares")
        loaded = handler.load("company.json")
    """

    # Mapping of source names to output directories
    SOURCE_DIRS = {
        "ares": ARES_OUTPUT_DIR,
        "orsr": ORSR_OUTPUT_DIR,
        "stats": STATS_OUTPUT_DIR,
        "justice": JUSTICE_OUTPUT_DIR,
        "rpo": RPO_OUTPUT_DIR,
        "rpvs": RPVS_OUTPUT_DIR,
        "financna": FINANCNA_OUTPUT_DIR,
        "esm": ESM_OUTPUT_DIR,
    }

    def __init__(self, base_output_dir: Optional[Path] = None):
        """Initialize JSON handler.

        Args:
            base_output_dir: Custom base output directory
        """
        self.base_output_dir = base_output_dir or OUTPUT_DIR
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create output directories if they don't exist."""
        for dir_path in self.SOURCE_DIRS.values():
            dir_path.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        data: Dict[str, Any],
        filename: str,
        source: Optional[str] = None
    ) -> str:
        """Save data to JSON file.

        Args:
            data: Data to save
            filename: Output filename
            source: Source name for directory selection

        Returns:
            Absolute path to saved file
        """
        # Determine output directory
        if source and source.lower() in self.SOURCE_DIRS:
            output_dir = self.SOURCE_DIRS[source.lower()]
        else:
            output_dir = self.base_output_dir

        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename

        # Add timestamp if not present
        if "scraped_at" not in data and "retrieved_at" not in data:
            data["scraped_at"] = datetime.utcnow().isoformat() + "Z"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str, ensure_ascii=False, indent=2)

        return str(filepath)

    def load(self, filepath: str) -> Dict[str, Any]:
        """Load data from JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            Loaded data dictionary
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_all(self, source: str, pattern: str = "*.json") -> List[Dict[str, Any]]:
        """Load all JSON files from a source directory.

        Args:
            source: Source name
            pattern: File pattern to match

        Returns:
            List of loaded data dictionaries
        """
        if source.lower() not in self.SOURCE_DIRS:
            return []

        output_dir = self.SOURCE_DIRS[source.lower()]
        results = []

        for filepath in output_dir.glob(pattern):
            try:
                results.append(self.load(str(filepath)))
            except (json.JSONDecodeError, IOError):
                continue

        return results
