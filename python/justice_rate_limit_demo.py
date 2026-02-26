#!/usr/bin/env python3
"""
Justice.cz Rate Limiting Demo

This script demonstrates the configurable rate limiting feature for Justice.cz scraping.
You can set delays between requests to avoid IP blocking.

Usage:
    # Safe scraping (10 seconds between requests - default)
    python justice_rate_limit_demo.py 05984866 06649114 00216305

    # Fast scraping (1 second between requests - may trigger rate limiting)
    python justice_rate_limit_demo.py --delay 1 05984866 06649114

    # No delay (not recommended - will likely get blocked)
    python justice_rate_limit_demo.py --delay 0 05984866
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.justice_czech import JusticeCzechScraper
import time


def demo_rate_limits(icos, delay):
    """Demonstrate rate limiting with different delay settings."""
    print("="*70)
    print("Justice.cz Rate Limiting Demo")
    print("="*70)
    print(f"Delay between requests: {delay} second(s)")
    print(f"Number of ICOS to process: {len(icos)}")
    print(f"Estimated time: {len(icos) * delay} seconds ({len(icos) * delay // 60} minutes)")
    print("="*70)
    print()

    # Create scraper with configured delay
    scraper = JusticeCzechScraper(
        enable_snapshots=False,
        use_playwright=False,
        delay_between_requests=delay
    )

    print(f"Starting requests at {time.strftime('%H:%M:%S')}")
    print()

    results = []
    for i, ico in enumerate(icos):
        start_time = time.time()

        print(f"[{i+1}/{len(icos)}] Fetching ICO: {ico}...")

        result = scraper.search_by_id(ico)

        elapsed = time.time() - start_time

        if result:
            entity = result.get('entity', {})
            name = entity.get('company_name_registry', 'Unknown')
            is_mock = result.get('metadata', {}).get('is_mock', False)
            mock_status = 'MOCK' if is_mock else 'REAL'
            print(f"  ✓ {name} ({mock_status})")
            results.append(result)
        else:
            print(f"  ✗ Not found")

        # Show timing info
        if i < len(icos) - 1 and delay > 0:
            remaining = (len(icos) - i - 1) * delay
            print(f"  Time elapsed: {elapsed:.1f}s | Remaining: ~{remaining}s")

    print()
    print("="*70)
    print(f"Completed at {time.strftime('%H:%M:%S')}")
    print(f"Successfully fetched: {len(results)}/{len(icos)}")
    print("="*70)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Demonstrate Justice.cz rate limiting'
    )
    parser.add_argument(
        'icos',
        nargs='*',
        help='Company ICOs to fetch (default: test ICOS)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=10,
        help='Delay between requests in seconds (default: 10)'
    )
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Fast mode: 1 second between requests (may trigger rate limiting)'
    )
    parser.add_argument(
        '--unsafe',
        action='store_true',
        help='Unsafe mode: no delay between requests (will likely get blocked)'
    )

    args = parser.parse_args()

    # Determine delay
    if args.unsafe:
        delay = 0
    elif args.fast:
        delay = 1
    else:
        delay = args.delay

    # Default test ICOS if none provided
    if not args.icos:
        icos = ['05984866', '06649114', '00216305']
        print(f"Using default test ICOS: {icos}")
    else:
        icos = args.icos

    # Validate delay
    if delay < 0:
        print("Error: Delay cannot be negative")
        return 1

    # Show warning for fast modes
    if delay == 0:
        print("⚠️  WARNING: No delay configured - this will likely trigger rate limiting!")
    elif delay < 5:
        print(f"⚠️  WARNING: Short delay ({delay}s) - may trigger rate limiting!")
        print("   Recommended: 10 seconds or more for safe scraping")
    print()

    try:
        demo_rate_limits(icos, delay)
        return 0
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
