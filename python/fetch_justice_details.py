#!/usr/bin/env python3
"""
Justice.cz Detail Page Fetcher - Correct Implementation

This script demonstrates the proper way to fetch Justice.cz detail pages:
1. Search for a company by ICO (generates session token)
2. Extract detail page links from search results (contain valid session tokens)
3. Fetch detail pages using extracted URLs

Usage:
    python fetch_justice_details.py 05984866
    python fetch_justice_details.py --file icos.txt
"""

import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.justice_czech import JusticeCzechScraper


def fetch_detail_pages_for_ico(ico, output_dir, scraper):
    """Fetch all detail pages for a given ICO."""
    print(f"\n{'='*70}")
    print(f"Processing ICO: {ico}")
    print(f"{'='*70}")

    # Step 1: Search to get session token
    search_url = f"{scraper.SEARCH_URL}?ico={ico}"
    print(f"Step 1: Searching - {search_url}")

    try:
        search_html = scraper.http_client.get_html(search_url)
        print("  ✓ Search successful")
    except Exception as e:
        print(f"  ✗ Search failed: {e}")
        return []

    # Step 2: Extract detail links with session tokens
    soup = BeautifulSoup(search_html, 'lxml')
    detail_links = []

    for link in soup.find_all('a', href=True):
        href = link.get('href')
        text = link.get_text(strip=True)

        if 'vysledky' in href and 'subjektId' in href:
            full_url = urljoin('https://or.justice.cz/ias/ui/', href)
            detail_links.append({
                'type': text,
                'url': full_url
            })

    print(f"  ✓ Found {len(detail_links)} detail links")

    if not detail_links:
        return []

    # Step 3: Fetch each detail page
    results = []

    for i, link in enumerate(detail_links):
        link_type = link['type']
        url = link['url']

        print(f"\n  [{i+1}/{len(detail_links)}] Fetching: {link_type[:60]}")

        try:
            detail_html = scraper.http_client.get_html(url)

            # Parse detail page
            detail_soup = BeautifulSoup(detail_html, 'lxml')

            # Extract data
            title_tag = detail_soup.find('title')
            title = title_tag.get_text() if title_tag else 'No title'

            # Get all text content
            for script in detail_soup(['script', 'style']):
                script.decompose()
            text_content = detail_soup.get_text(separator='\n', strip=True)

            result = {
                'ico': ico,
                'link_type': link_type,
                'url': url,
                'title': title,
                'html_length': len(detail_html),
                'fetched_at': datetime.now().isoformat(),
                'text_content': text_content[:10000]  # First 10k chars
            }

            # Save to file
            safe_type = link_type.replace('/', '-').replace(' ', '_')[:30]
            filename = output_dir / f"ico_{ico}_{i+1}_{safe_type}.json"

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Also save raw HTML
            html_filename = output_dir / f"ico_{ico}_{i+1}_{safe_type}.html"
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(detail_html)

            print(f"    ✓ Saved: {filename.name}")

            results.append(result)

            # Small delay between detail pages
            if i < len(detail_links) - 1:
                time.sleep(2)

        except Exception as e:
            print(f"    ✗ Error: {e}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Fetch Justice.cz detail pages using correct session-aware approach'
    )
    parser.add_argument(
        'ico',
        nargs='?',
        help='Company ICO (8 digits)'
    )
    parser.add_argument(
        '--file',
        help='File containing list of ICOS (one per line)'
    )
    parser.add_argument(
        '--output-dir',
        default='justice_detail_pages',
        help='Output directory for fetched data'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=5,
        help='Delay between ICOS in seconds (default: 5)'
    )

    args = parser.parse_args()

    # Get ICOS to process
    if args.file:
        with open(args.file, 'r') as f:
            icos = [line.strip() for line in f if line.strip()]
    elif args.ico:
        icos = [args.ico]
    else:
        parser.print_help()
        return 1

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize scraper
    scraper = JusticeCzechScraper(use_playwright=False)

    # Process each ICO
    print("="*70)
    print("Justice.cz Detail Page Fetcher")
    print("="*70)
    print(f"Output directory: {output_dir.absolute()}")
    print(f"ICOs to process: {len(icos)}")
    print(f"Delay between ICOS: {args.delay} seconds")

    all_results = []

    for i, ico in enumerate(icos):
        print(f"\n[{i+1}/{len(icos)}] Processing {ico}...")

        results = fetch_detail_pages_for_ico(ico, output_dir, scraper)
        all_results.extend(results)

        # Delay between different ICOS (to avoid rate limiting)
        if i < len(icos) - 1:
            print(f"\n  Waiting {args.delay} seconds before next ICO...")
            time.sleep(args.delay)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"ICOs processed: {len(icos)}")
    print(f"Detail pages fetched: {len(all_results)}")
    print(f"Output directory: {output_dir.absolute()}")
    print("="*70)

    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
