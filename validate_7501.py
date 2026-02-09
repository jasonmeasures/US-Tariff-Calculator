#!/usr/bin/env python3
"""
7501 Entry Summary Validator
Uploads Excel file and generates detailed validation report
"""

import requests
import pandas as pd
import sys
from pathlib import Path

API_URL = 'http://localhost:8000/api/validate-entry'

def validate_7501(file_path, output_excel='validation_report.xlsx'):
    """Upload 7501 and generate detailed validation report"""

    file_path = Path(file_path)

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    print(f"📤 Uploading: {file_path.name}")
    print(f"   Size: {file_path.stat().st_size:,} bytes")
    print()

    # Upload file
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(API_URL, files={'file': f}, timeout=120)

        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            return

        results = response.json()

    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Is the backend API running?")
        print("   Start with: python backend/api.py")
        return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Process results
    print("✅ Validation complete!")
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Lines:     {results['total_lines']}")
    print(f"Processed:       {results['processed_lines']}")
    print(f"Total Variance:  ${results['total_variance']:,.2f}")
    print()

    if not results['results']:
        print("No results to process")
        return

    df_results = pd.DataFrame(results['results'])

    # Add status column
    df_results['status'] = df_results.apply(lambda r:
        '✅ MATCH' if 'error' in r else
        '✅ MATCH' if abs(r.get('variance', 0)) < 1 else
        '⚠️ MINOR' if abs(r.get('variance_percent', 0)) < 5 else
        '❌ MAJOR', axis=1
    )

    # Count by status
    matches = len(df_results[df_results['status'] == '✅ MATCH'])
    minor = len(df_results[df_results['status'] == '⚠️ MINOR'])
    major = len(df_results[df_results['status'] == '❌ MAJOR'])

    print(f"✅ Matches:      {matches}")
    print(f"⚠️  Minor (<5%):  {minor}")
    print(f"❌ Major (≥5%):  {major}")
    print()

    # Show major variances
    if major > 0:
        print("=" * 80)
        print("MAJOR VARIANCES (≥5%)")
        print("=" * 80)
        major_df = df_results[df_results['status'] == '❌ MAJOR'].head(10)

        for idx, row in major_df.iterrows():
            print(f"\nLine {row.get('line', idx+1)}: HTS {row.get('hts_code', 'N/A')} - {row.get('country', 'N/A')}")
            print(f"  Declared:   ${row.get('declared_duty', 0):>10,.2f}")
            print(f"  Calculated: ${row.get('calculated_duty', 0):>10,.2f}")
            print(f"  Variance:   ${row.get('variance', 0):>10,.2f} ({row.get('variance_percent', 0):.1f}%)")

        if major > 10:
            print(f"\n... and {major - 10} more variances")

    print()

    # Create Excel report
    print("=" * 80)
    print("GENERATING EXCEL REPORT")
    print("=" * 80)

    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        # Summary sheet
        summary = pd.DataFrame({
            'Metric': [
                'Total Lines',
                'Processed Lines',
                'Matches',
                'Minor Variances (<5%)',
                'Major Variances (≥5%)',
                'Total Variance ($)',
                'Match Rate (%)'
            ],
            'Value': [
                results['total_lines'],
                results['processed_lines'],
                matches,
                minor,
                major,
                f"${results['total_variance']:,.2f}",
                f"{(matches / results['processed_lines'] * 100):.1f}%" if results['processed_lines'] > 0 else "0%"
            ]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

        # All results
        df_results.to_excel(writer, sheet_name='All Entries', index=False)

        # Major variances only
        major_only = df_results[df_results['status'] == '❌ MAJOR']
        if len(major_only) > 0:
            major_only.to_excel(writer, sheet_name='Major Variances', index=False)

        # Minor variances
        minor_only = df_results[df_results['status'] == '⚠️ MINOR']
        if len(minor_only) > 0:
            minor_only.to_excel(writer, sheet_name='Minor Variances', index=False)

    print(f"✅ Report saved: {output_excel}")
    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("1. Open the Excel report to review all variances")
    print("2. For major variances, check:")
    print("   • IEEPA reciprocal tariffs (Mexico, China, etc.)")
    print("   • Section 232 material content (steel, aluminum, copper)")
    print("   • Implementation dates vs entry dates")
    print("   • Chapter 99 codes used")
    print("3. Re-run validation after fixing issues")
    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python validate_7501.py <path_to_7501_excel>")
        print()
        print("Example:")
        print("  python validate_7501.py data/7501_entry_summary.xlsx")
        sys.exit(1)

    file_path = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else 'validation_report.xlsx'

    validate_7501(file_path, output)
