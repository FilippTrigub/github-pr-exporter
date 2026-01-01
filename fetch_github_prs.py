#!/usr/bin/env python3
"""
GitHub PR Fetcher and PDF Exporter
Fetches all PRs authored by a specific user in a repository and exports to PDF.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import argparse
import unicodedata
import re
import calendar
from fpdf import FPDF


def sanitize_text(text: str) -> str:
    """
    Remove or replace characters that can't be encoded in latin-1.

    Args:
        text: Input text that may contain Unicode characters

    Returns:
        Sanitized text safe for PDF generation
    """
    if not text:
        return ""

    # Remove emojis and other non-latin-1 characters
    # First, try to normalize Unicode characters
    text = unicodedata.normalize('NFKD', text)

    # Remove emojis and special Unicode characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)

    # Replace characters that can't be encoded in latin-1
    result = []
    for char in text:
        try:
            char.encode('latin-1')
            result.append(char)
        except UnicodeEncodeError:
            # Skip characters that can't be encoded
            continue

    return ''.join(result)


def parse_date_filter(date_str: str) -> Optional[datetime]:
    """
    Parse date filter string in various formats.

    Supports:
    - day.month.year (e.g., 01.12.2024)
    - month number (e.g., 12 for December of current year)
    - 'last-month' flag

    Args:
        date_str: Date string in supported format

    Returns:
        datetime object or None if invalid
    """
    if not date_str:
        return None

    date_str = date_str.strip().lower()

    # Handle 'last-month' flag
    if date_str == 'last-month':
        today = datetime.now()
        # Get first day of current month, then subtract one day to get last day of previous month
        first_day_current_month = today.replace(day=1)
        last_day_prev_month = first_day_current_month - timedelta(days=1)
        return last_day_prev_month.replace(day=1)  # First day of last month

    # Try day.month.year format (e.g., 01.12.2024)
    if '.' in date_str:
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected format: dd.mm.yyyy")

    # Try month number (1-12)
    try:
        month = int(date_str)
        if 1 <= month <= 12:
            current_year = datetime.now().year
            return datetime(current_year, month, 1)
        else:
            raise ValueError(f"Month must be between 1 and 12, got: {month}")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected: dd.mm.yyyy, month number (1-12), or 'last-month'")


def get_date_range_from_filters(start_date_str: str, end_date_str: str) -> tuple:
    """
    Convert date filter strings to datetime range.

    Args:
        start_date_str: Start date string
        end_date_str: End date string

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    start_date = None
    end_date = None

    if start_date_str:
        start_date = parse_date_filter(start_date_str)

        # For 'last-month' or month-only, set to first day of that month
        if start_date_str.strip().lower() == 'last-month' or (start_date_str.isdigit() and 1 <= int(start_date_str) <= 12):
            # Already set to first day of month
            pass

    if end_date_str:
        end_date = parse_date_filter(end_date_str)

        # For 'last-month' or month-only, set to last day of that month
        if end_date_str.strip().lower() == 'last-month':
            # Get last day of last month
            today = datetime.now()
            first_day_current_month = today.replace(day=1)
            end_date = first_day_current_month - timedelta(days=1)
        elif end_date_str.isdigit() and 1 <= int(end_date_str) <= 12:
            # Get last day of the specified month
            month = int(end_date_str)
            year = datetime.now().year
            last_day = calendar.monthrange(year, month)[1]
            end_date = datetime(year, month, last_day, 23, 59, 59)

    return start_date, end_date


def filter_prs_by_date(prs: List[Dict], start_date: Optional[datetime], end_date: Optional[datetime]) -> List[Dict]:
    """
    Filter PRs by date range.

    Args:
        prs: List of formatted PR dictionaries
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Filtered list of PRs
    """
    if not start_date and not end_date:
        return prs

    filtered_prs = []

    for pr in prs:
        # Use merge date if merged, otherwise use created date
        date_str = pr.get('merged_at') if pr.get('merged') else pr.get('created_at')
        pr_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

        # Check date range
        if start_date and pr_date < start_date:
            continue
        if end_date and pr_date > end_date:
            continue

        filtered_prs.append(pr)

    return filtered_prs


class GitHubPRFetcher:
    """Fetches PRs from GitHub API."""

    def __init__(self, token: str = None):
        """
        Initialize the fetcher.

        Args:
            token: GitHub personal access token (optional, but recommended to avoid rate limits)
        """
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            self.headers["Authorization"] = f"token {token}"

    def fetch_user_prs(self, owner: str, repo: str, author: str) -> List[Dict]:
        """
        Fetch all PRs authored by a specific user.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            author: PR author username

        Returns:
            List of PR dictionaries
        """
        all_prs = []
        page = 1
        per_page = 100

        while True:
            # Fetch PRs with pagination
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
            params = {
                "state": "all",  # Get both open and closed PRs
                "per_page": per_page,
                "page": page,
                "sort": "created",
                "direction": "desc"
            }

            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                raise Exception(f"GitHub API error: {response.status_code} - {response.text}")

            prs = response.json()

            if not prs:
                break

            # Filter PRs by author
            user_prs = [pr for pr in prs if pr["user"]["login"] == author]
            all_prs.extend(user_prs)

            page += 1

            # Stop if we got fewer results than requested (last page)
            if len(prs) < per_page:
                break

        return all_prs

    def format_pr_data(self, prs: List[Dict]) -> List[Dict]:
        """
        Format PR data for display.

        Args:
            prs: List of raw PR data from GitHub API

        Returns:
            List of formatted PR dictionaries
        """
        formatted_prs = []

        for pr in prs:
            formatted_pr = {
                "number": pr["number"],
                "title": pr["title"],
                "description": pr["body"] or "No description provided",
                "state": pr["state"],
                "created_at": datetime.strptime(
                    pr["created_at"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "url": pr["html_url"],
                "merged": pr.get("merged_at") is not None,
                "merged_at": datetime.strptime(
                    pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%Y-%m-%d %H:%M:%S") if pr.get("merged_at") else None
            }
            formatted_prs.append(formatted_pr)

        return formatted_prs


class PDFExporter(FPDF):
    """Custom PDF class for exporting PR data."""

    def __init__(self, repo_name: str, author: str):
        super().__init__()
        self.repo_name = repo_name
        self.author = author

    def header(self):
        """Add header to each page."""
        self.set_font('Arial', 'B', 12)
        self.cell(0, 8, sanitize_text(f'Pull Requests by {self.author}'), 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, sanitize_text(f'Repository: {self.repo_name}'), 0, 1, 'C')
        self.ln(4)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def add_pr(self, pr: Dict):
        """
        Add a PR to the PDF.

        Args:
            pr: Formatted PR dictionary
        """
        # Status Badge (Prominent) - Left side only
        status = "MERGED" if pr['merged'] else pr['state'].upper()
        self.set_font('Arial', 'B', 9)

        # Set status badge colors
        if pr['merged']:
            self.set_fill_color(34, 139, 34)  # Green for merged
            self.set_text_color(255, 255, 255)
        elif pr['state'] == 'open':
            self.set_fill_color(40, 167, 69)  # Lighter green for open
            self.set_text_color(255, 255, 255)
        else:
            self.set_fill_color(108, 117, 125)  # Gray for closed
            self.set_text_color(255, 255, 255)

        # Draw status badge - text only, no background box
        # Reset to ensure we're at left margin
        self.set_x(self.l_margin)
        status_text = f"[{status}]"
        self.multi_cell(0, 6, status_text, 0, 'L')
        self.set_text_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)

        # PR Number and Title - ensure at left margin
        self.set_x(self.l_margin)
        self.set_font('Arial', 'B', 10)
        title_text = f"#{pr['number']} - {sanitize_text(pr['title'])}"
        self.multi_cell(0, 5, title_text, 0, 'L')

        # Date - ensure at left margin
        self.set_x(self.l_margin)
        self.set_font('Arial', '', 8)
        date = pr['merged_at'] if pr['merged'] else pr['created_at']
        self.set_text_color(100, 100, 100)
        self.multi_cell(0, 4, date, 0, 'L')
        self.set_text_color(0, 0, 0)

        # URL - ensure at left margin
        self.set_x(self.l_margin)
        self.set_font('Arial', '', 7)
        self.set_text_color(0, 0, 255)
        self.multi_cell(0, 4, sanitize_text(pr['url']), 0, 'L')
        self.set_text_color(0, 0, 0)

        # Description - ensure at left margin
        self.ln(1)
        self.set_x(self.l_margin)
        self.set_font('Arial', '', 8)
        description = sanitize_text(pr['description'][:500])
        if description:
            self.multi_cell(0, 4, description, 0, 'L')

        # Separator
        self.ln(2)
        self.set_draw_color(220, 220, 220)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)


def export_to_html(prs: List[Dict], filename: str, repo_name: str, author: str):
    """
    Export PRs to HTML.

    Args:
        prs: List of formatted PR dictionaries
        filename: Output HTML filename
        repo_name: Repository name for the header
        author: Author name for the header
    """
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pull Requests by {sanitize_text(author)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 20px;
        }}
        .header h1 {{
            font-size: 24px;
            color: #333;
            margin-bottom: 8px;
        }}
        .header .repo {{
            font-size: 14px;
            color: #666;
        }}
        .summary {{
            background: #f8f9fa;
            padding: 12px 16px;
            border-radius: 6px;
            margin-bottom: 24px;
            font-weight: 600;
            color: #555;
        }}
        .pr-item {{
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .pr-item:last-child {{
            border-bottom: none;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}
        .status-merged {{
            background-color: #228b22;
        }}
        .status-open {{
            background-color: #28a745;
        }}
        .status-closed {{
            background-color: #6c757d;
        }}
        .pr-title {{
            font-size: 16px;
            font-weight: 600;
            color: #333;
            margin-bottom: 6px;
            line-height: 1.4;
        }}
        .pr-date {{
            font-size: 13px;
            color: #666;
            margin-bottom: 6px;
        }}
        .pr-url {{
            font-size: 12px;
            margin-bottom: 10px;
        }}
        .pr-url a {{
            color: #0366d6;
            text-decoration: none;
        }}
        .pr-url a:hover {{
            text-decoration: underline;
        }}
        .pr-description {{
            font-size: 14px;
            color: #555;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Pull Requests by {sanitize_text(author)}</h1>
            <div class="repo">Repository: {sanitize_text(repo_name)}</div>
        </div>

        <div class="summary">Total PRs: {len(prs)}</div>
"""

    for pr in prs:
        status = "MERGED" if pr['merged'] else pr['state'].upper()
        status_class = "merged" if pr['merged'] else pr['state'].lower()
        date = pr['merged_at'] if pr['merged'] else pr['created_at']

        html_content += f"""
        <div class="pr-item">
            <div class="status-badge status-{status_class}">{status}</div>
            <div class="pr-title">#{pr['number']} - {sanitize_text(pr['title'])}</div>
            <div class="pr-date">{date}</div>
            <div class="pr-url"><a href="{pr['url']}" target="_blank">{pr['url']}</a></div>
            <div class="pr-description">{sanitize_text(pr['description'][:500])}</div>
        </div>
"""

    html_content += """
        <div class="footer">
            Generated with GitHub PR Fetcher
        </div>
    </div>
</body>
</html>
"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML exported successfully: {filename}")


def export_to_pdf(prs: List[Dict], filename: str, repo_name: str, author: str):
    """
    Export PRs to PDF.

    Args:
        prs: List of formatted PR dictionaries
        filename: Output PDF filename
        repo_name: Repository name for the header
        author: Author name for the header
    """
    pdf = PDFExporter(repo_name, author)
    pdf.add_page()

    # Add summary
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 6, f'Total PRs: {len(prs)}', 0, 1)
    pdf.ln(2)

    # Add each PR
    for pr in prs:
        # Check if we need a new page
        if pdf.get_y() > 250:
            pdf.add_page()

        pdf.add_pr(pr)

    pdf.output(filename)
    print(f"PDF exported successfully: {filename}")


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Fetch GitHub PRs and export to PDF"
    )
    parser.add_argument(
        "--owner",
        required=True,
        help="Repository owner (username or organization)"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository name"
    )
    parser.add_argument(
        "--author",
        required=True,
        help="PR author username"
    )
    parser.add_argument(
        "--token",
        help="GitHub personal access token (optional, but recommended)"
    )
    parser.add_argument(
        "--output",
        help="Output filename (default: github_prs.html or github_prs.pdf depending on format)"
    )
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Export to PDF instead of HTML (default: HTML)"
    )
    parser.add_argument(
        "--start-date",
        help="Start date filter. Formats: dd.mm.yyyy (01.12.2024) or month number (12)"
    )
    parser.add_argument(
        "--end-date",
        help="End date filter. Formats: dd.mm.yyyy (31.12.2024) or month number (12)"
    )
    parser.add_argument(
        "--last-month",
        action="store_true",
        help="Filter PRs from last month only (shortcut for setting both start and end dates)"
    )

    args = parser.parse_args()

    # Determine output format and filename
    output_format = "pdf" if args.pdf else "html"
    if args.output:
        output_filename = args.output
    else:
        output_filename = f"github_prs.{output_format}"

    print(f"Fetching PRs by {args.author} from {args.owner}/{args.repo}...")
    print(f"Output format: {output_format.upper()}")

    # Fetch PRs
    fetcher = GitHubPRFetcher(token=args.token)
    prs = fetcher.fetch_user_prs(args.owner, args.repo, args.author)

    if not prs:
        print(f"No PRs found for author {args.author}")
        return

    print(f"Found {len(prs)} PRs")

    # Format PRs
    formatted_prs = fetcher.format_pr_data(prs)

    # Apply date filtering
    start_date_str = args.start_date
    end_date_str = args.end_date

    # Handle --last-month flag
    if args.last_month:
        start_date_str = "last-month"
        end_date_str = "last-month"
        print("Filtering PRs from last month")

    if start_date_str or end_date_str:
        try:
            start_date, end_date = get_date_range_from_filters(start_date_str, end_date_str)

            if start_date:
                print(f"Filtering PRs from: {start_date.strftime('%Y-%m-%d')}")
            if end_date:
                print(f"Filtering PRs until: {end_date.strftime('%Y-%m-%d')}")

            formatted_prs = filter_prs_by_date(formatted_prs, start_date, end_date)
            print(f"After filtering: {len(formatted_prs)} PRs")

            if not formatted_prs:
                print("No PRs found matching the date filter")
                return
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return

    # Export to chosen format
    repo_full_name = f"{args.owner}/{args.repo}"
    if args.pdf:
        export_to_pdf(formatted_prs, output_filename, repo_full_name, args.author)
    else:
        export_to_html(formatted_prs, output_filename, repo_full_name, args.author)

    print(f"Done! Check {output_filename}")


if __name__ == "__main__":
    main()
