"""
US Tariff Calculator - CSMS & Federal Register Monitor
Checks for new tariff-related CSMS messages and Federal Register notices.
Stores alerts in database for admin review.
"""

import sqlite3
import os
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "us_tariff_calculator.db")

# Tariff-related keywords for relevance scoring
TARIFF_KEYWORDS = {
    'high': ['IEEPA', 'reciprocal tariff', 'Section 232', 'Section 301',
             'Chapter 99', '9903', 'duty rate change', 'tariff modification',
             'presidential proclamation'],
    'medium': ['tariff', 'duty', 'HTS', 'customs', 'import duty', 'trade remedy',
               'antidumping', 'countervailing', 'exclusion', 'exemption'],
    'low': ['trade', 'import', 'export', 'commerce', 'CBP', 'customs and border'],
}

# Country keywords
COUNTRY_KEYWORDS = [
    'China', 'Mexico', 'Canada', 'Japan', 'India', 'Brazil', 'South Korea',
    'Vietnam', 'Taiwan', 'Germany', 'Switzerland', 'Liechtenstein',
]


def calculate_relevance(title: str, summary: str) -> float:
    """Score relevance 0-100 based on keyword matches"""
    text = f"{title} {summary}".lower()
    score = 0

    for keyword in TARIFF_KEYWORDS['high']:
        if keyword.lower() in text:
            score += 25

    for keyword in TARIFF_KEYWORDS['medium']:
        if keyword.lower() in text:
            score += 10

    for keyword in TARIFF_KEYWORDS['low']:
        if keyword.lower() in text:
            score += 3

    for country in COUNTRY_KEYWORDS:
        if country.lower() in text:
            score += 5

    # Check for rate numbers (e.g., "25%", "10 percent")
    if re.search(r'\d+(\.\d+)?\s*(%|percent)', text):
        score += 15

    # Check for CSMS reference numbers
    if re.search(r'csms\s*#?\s*\d{7,8}', text):
        score += 20

    return min(score, 100)


def generate_suggested_change(title: str, summary: str) -> Optional[str]:
    """Try to generate a natural language rule change suggestion from alert content"""
    text = f"{title} {summary}"

    # Look for country + rate patterns
    rate_match = re.search(r'(\w+)\s+(?:IEEPA|reciprocal|tariff).*?(\d+(?:\.\d+)?)\s*(%|percent)', text, re.IGNORECASE)
    if rate_match:
        country = rate_match.group(1)
        rate = rate_match.group(2)
        return f"Set {country} IEEPA to {rate}%"

    # Look for CSMS references
    csms_match = re.search(r'CSMS\s*#?\s*(\d{7,8})', text, re.IGNORECASE)
    if csms_match:
        csms = csms_match.group(1)
        return f"Review changes per CSMS {csms}"

    return None


def check_already_stored(conn, source: str, reference: str) -> bool:
    """Check if an alert with this reference already exists"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM monitor_alerts WHERE source = ? AND reference_number = ?",
        (source, reference)
    )
    return cursor.fetchone() is not None


def fetch_federal_register_notices() -> List[Dict]:
    """
    Fetch recent tariff-related notices from the Federal Register API.
    Uses the free federalregister.gov API (no auth required).
    """
    alerts = []

    try:
        import httpx

        # Search for tariff-related documents in the last 30 days
        today = datetime.now().strftime('%Y-%m-%d')
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        # Multiple searches for different tariff-related terms
        search_terms = [
            'IEEPA tariff',
            'Section 232 tariff',
            'Section 301 tariff',
            'reciprocal tariff',
            'Chapter 99 customs',
        ]

        seen_refs = set()

        for term in search_terms:
            try:
                url = 'https://www.federalregister.gov/api/v1/documents.json'
                params = {
                    'conditions[term]': term,
                    'conditions[publication_date][gte]': thirty_days_ago,
                    'conditions[publication_date][lte]': today,
                    'per_page': 10,
                    'order': 'newest',
                    'fields[]': ['title', 'abstract', 'publication_date',
                                 'document_number', 'type', 'agencies'],
                }

                response = httpx.get(url, params=params, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    for doc in data.get('results', []):
                        ref = doc.get('document_number', '')
                        if ref in seen_refs:
                            continue
                        seen_refs.add(ref)

                        title = doc.get('title', '')
                        abstract = doc.get('abstract', '') or ''
                        pub_date = doc.get('publication_date', '')

                        relevance = calculate_relevance(title, abstract)
                        if relevance >= 15:  # Minimum threshold
                            alerts.append({
                                'source': 'Federal Register',
                                'reference_number': ref,
                                'title': title[:200],
                                'published_date': pub_date,
                                'summary': abstract[:500],
                                'raw_content': json.dumps(doc),
                                'relevance_score': relevance,
                                'suggested_changes': generate_suggested_change(title, abstract),
                            })

            except Exception as e:
                print(f"  FR search error for '{term}': {e}")

    except ImportError:
        print("  httpx not installed - skipping Federal Register check")
        print("  Install with: pip install httpx")

    return alerts


def fetch_csms_messages() -> List[Dict]:
    """
    Fetch recent CSMS messages from CBP.
    CSMS uses a web interface that may require scraping.
    Falls back to a simulated check if scraping fails.
    """
    alerts = []

    try:
        import httpx
        from bs4 import BeautifulSoup

        # CSMS search page
        url = 'https://csms.cbp.gov/search'

        # Try searching for tariff-related messages
        search_terms = ['IEEPA', 'tariff', 'Section 232', 'reciprocal']

        for term in search_terms:
            try:
                response = httpx.get(
                    url,
                    params={'search': term, 'page': 1},
                    timeout=15.0,
                    follow_redirects=True,
                )

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Parse CSMS message listings
                    # The actual structure depends on the CSMS website layout
                    messages = soup.find_all('div', class_='message') or soup.find_all('tr')

                    for msg in messages[:5]:  # Limit per search
                        # Try to extract title and reference
                        title_el = msg.find('a') or msg.find('td')
                        if title_el:
                            title = title_el.get_text(strip=True)[:200]

                            # Extract CSMS number from link or text
                            csms_match = re.search(r'(\d{7,8})', str(msg))
                            ref = csms_match.group(1) if csms_match else ''

                            # Extract date
                            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', str(msg))
                            pub_date = date_match.group(1) if date_match else ''

                            if ref:
                                relevance = calculate_relevance(title, '')
                                if relevance >= 15:
                                    alerts.append({
                                        'source': 'CSMS',
                                        'reference_number': ref,
                                        'title': title,
                                        'published_date': pub_date,
                                        'summary': title,
                                        'raw_content': str(msg)[:1000],
                                        'relevance_score': relevance,
                                        'suggested_changes': generate_suggested_change(title, ''),
                                    })

            except Exception as e:
                print(f"  CSMS search error for '{term}': {e}")

    except ImportError:
        print("  httpx/beautifulsoup4 not installed - skipping CSMS check")
        print("  Install with: pip install httpx beautifulsoup4")

    return alerts


def store_alerts(alerts: List[Dict]) -> Dict:
    """Store new alerts in the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    stored = 0
    skipped = 0

    for alert in alerts:
        ref = alert.get('reference_number', '')
        source = alert.get('source', '')

        if ref and check_already_stored(conn, source, ref):
            skipped += 1
            continue

        cursor.execute("""
            INSERT INTO monitor_alerts
            (source, reference_number, title, published_date, summary, raw_content,
             relevance_score, suggested_changes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source,
            ref,
            alert.get('title', ''),
            alert.get('published_date', ''),
            alert.get('summary', ''),
            alert.get('raw_content', ''),
            alert.get('relevance_score', 0),
            alert.get('suggested_changes'),
        ))
        stored += 1

    conn.commit()
    conn.close()

    return {'stored': stored, 'skipped': skipped}


def run_check() -> Dict:
    """
    Run a full check for new CSMS and Federal Register notices.
    Returns summary of results.
    """
    print(f"\n=== MONITOR CHECK: {datetime.now().isoformat()} ===")

    results = {
        'timestamp': datetime.now().isoformat(),
        'csms_found': 0,
        'fr_found': 0,
        'stored': 0,
        'skipped': 0,
    }

    # Check CSMS
    print("  Checking CSMS...")
    csms_alerts = fetch_csms_messages()
    results['csms_found'] = len(csms_alerts)
    print(f"  Found {len(csms_alerts)} relevant CSMS messages")

    # Check Federal Register
    print("  Checking Federal Register...")
    fr_alerts = fetch_federal_register_notices()
    results['fr_found'] = len(fr_alerts)
    print(f"  Found {len(fr_alerts)} relevant FR notices")

    # Store all alerts
    all_alerts = csms_alerts + fr_alerts
    if all_alerts:
        store_result = store_alerts(all_alerts)
        results['stored'] = store_result['stored']
        results['skipped'] = store_result['skipped']
        print(f"  Stored {store_result['stored']} new alerts, {store_result['skipped']} duplicates skipped")
    else:
        print("  No new alerts to store")

    print(f"=== CHECK COMPLETE ===\n")
    return results


if __name__ == "__main__":
    print("Manual monitor check...")
    results = run_check()
    print(f"\nResults: {json.dumps(results, indent=2)}")
