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
from weasyprint import HTML
import tempfile


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

    def fetch_reviewed_prs(self, owner: str, repo: str, reviewer: str) -> List[Dict]:
        """
        Fetch all PRs reviewed by a specific user.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            reviewer: PR reviewer username

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
                "state": "all",
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

            # Check each PR for reviews by the user
            for pr in prs:
                reviews_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr['number']}/reviews"
                reviews_response = requests.get(reviews_url, headers=self.headers)

                if reviews_response.status_code == 200:
                    reviews = reviews_response.json()
                    # Check if user has reviewed this PR
                    if any(review["user"]["login"] == reviewer for review in reviews):
                        all_prs.append(pr)

            page += 1

            if len(prs) < per_page:
                break

        return all_prs

    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Dict:
        """
        Get detailed statistics for a specific PR.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            Dictionary with detailed PR stats
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            return {
                "commits": 0,
                "additions": 0,
                "deletions": 0,
                "changed_files": 0
            }

        pr_data = response.json()
        return {
            "commits": pr_data.get("commits", 0),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0),
            "changed_files": pr_data.get("changed_files", 0)
        }

    def format_pr_data(self, prs: List[Dict], owner: str = None, repo: str = None, include_stats: bool = False) -> List[Dict]:
        """
        Format PR data for display.

        Args:
            prs: List of raw PR data from GitHub API
            owner: Repository owner (required if include_stats is True)
            repo: Repository name (required if include_stats is True)
            include_stats: Whether to fetch detailed stats for each PR

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
                ).strftime("%Y-%m-%d %H:%M:%S") if pr.get("merged_at") else None,
                "repo": f"{owner}/{repo}" if owner and repo else "Unknown"
            }

            # Add detailed stats if requested
            if include_stats and owner and repo:
                details = self.get_pr_details(owner, repo, pr["number"])
                formatted_pr.update(details)
            else:
                formatted_pr.update({
                    "commits": 0,
                    "additions": 0,
                    "deletions": 0,
                    "changed_files": 0
                })

            formatted_prs.append(formatted_pr)

        return formatted_prs


def export_to_html(prs: List[Dict], filename: str, repo_name: str, author: str, customization: Dict = None):
    """
    Export PRs to HTML.

    Args:
        prs: List of formatted PR dictionaries
        filename: Output HTML filename
        repo_name: Repository name for the header
        author: Author name for the header
        customization: Optional customization settings dict
    """
    # Default customization values
    if customization is None:
        customization = {}

    show_description = customization.get('show_description', True)
    show_repo_name = customization.get('show_repo_name', True)
    max_description_length = customization.get('max_description_length', 500)
    sort_by = customization.get('sort_by', 'Date (newest first)')
    filter_status = customization.get('filter_status', ['MERGED', 'OPEN', 'CLOSED'])
    primary_color = customization.get('primary_color', '#228b22')
    bg_color = customization.get('bg_color', '#f5f5f5')
    text_color = customization.get('text_color', '#333333')
    font_family = customization.get('font_family', 'Arial, sans-serif')
    custom_title = customization.get('custom_title', '')

    # Apply sorting
    if sort_by == 'Date (oldest first)':
        prs = sorted(prs, key=lambda x: x.get('merged_at') or x.get('created_at'))
    elif sort_by == 'PR Number':
        prs = sorted(prs, key=lambda x: x['number'])
    elif sort_by == 'Status':
        prs = sorted(prs, key=lambda x: (0 if x['merged'] else (1 if x['state'] == 'open' else 2)))
    else:  # Date (newest first) - default
        prs = sorted(prs, key=lambda x: x.get('merged_at') or x.get('created_at'), reverse=True)

    # Apply status filtering
    filtered_prs = []
    for pr in prs:
        status = "MERGED" if pr['merged'] else pr['state'].upper()
        if status in filter_status:
            filtered_prs.append(pr)
    prs = filtered_prs

    # Use custom title if provided
    title_text = custom_title if custom_title else f"Pull Requests by {sanitize_text(author)}"
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_text}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: {font_family};
            line-height: 1.6;
            color: {text_color};
            background: {bg_color};
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
            color: {text_color};
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
            background-color: {primary_color};
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
            color: {text_color};
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
            color: {primary_color};
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
        .pr-repo {{
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
            font-weight: 500;
        }}
        .pr-stats {{
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
            font-family: 'Courier New', monospace;
        }}
        .pr-type {{
            display: inline-block;
            font-size: 11px;
            color: #666;
            font-style: italic;
            margin-bottom: 4px;
            padding: 2px 8px;
            background: #f0f0f0;
            border-radius: 3px;
        }}
        .stats-summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 12px 16px;
            border-radius: 6px;
            text-align: center;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 4px;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: 600;
            color: {text_color};
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
            <h1>{title_text}</h1>
            <div class="repo">Repository: {sanitize_text(repo_name)}</div>
        </div>

        <div class="stats-summary">
            <div class="stat-card">
                <div class="stat-label">Total PRs</div>
                <div class="stat-value">{len(prs)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Commits</div>
                <div class="stat-value">{sum(pr.get('commits', 0) for pr in prs):,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Lines Added</div>
                <div class="stat-value">{sum(pr.get('additions', 0) for pr in prs):,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Lines Deleted</div>
                <div class="stat-value">{sum(pr.get('deletions', 0) for pr in prs):,}</div>
            </div>
        </div>
"""

    for pr in prs:
        status = "MERGED" if pr['merged'] else pr['state'].upper()
        status_class = "merged" if pr['merged'] else pr['state'].lower()
        date = pr['merged_at'] if pr['merged'] else pr['created_at']

        pr_type_html = f'<div class="pr-type">{pr.get("pr_type", "Unknown")}</div>' if pr.get('pr_type') else ''
        repo_html = f'<div class="pr-repo">Repository: {sanitize_text(pr.get("repo", "Unknown"))}</div>' if (show_repo_name and pr.get('repo')) else ''
        stats_html = ''
        if pr.get('commits', 0) > 0 or pr.get('additions', 0) > 0:
            stats_html = f'<div class="pr-stats">Commits: {pr.get("commits", 0)} | +{pr.get("additions", 0)} -{pr.get("deletions", 0)} lines</div>'

        description_html = ''
        if show_description:
            description_html = f'<div class="pr-description">{sanitize_text(pr["description"][:max_description_length])}</div>'

        html_content += f"""
        <div class="pr-item">
            <div class="status-badge status-{status_class}">{status}</div>
            {pr_type_html}
            <div class="pr-title">#{pr['number']} - {sanitize_text(pr['title'])}</div>
            <div class="pr-date">{date}</div>
            {repo_html}
            {stats_html}
            <div class="pr-url"><a href="{pr['url']}" target="_blank">{pr['url']}</a></div>
            {description_html}
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


def export_to_pdf(prs: List[Dict], filename: str, repo_name: str, author: str, customization: Dict = None):
    """
    Export PRs to PDF using WeasyPrint.

    Args:
        prs: List of formatted PR dictionaries
        filename: Output PDF filename
        repo_name: Repository name for the header
        author: Author name for the header
        customization: Optional customization settings dict
    """
    # Generate HTML first
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_html:
        export_to_html(prs, tmp_html.name, repo_name, author, customization)
        html_file = tmp_html.name

    try:
        # Convert HTML to PDF using WeasyPrint
        HTML(filename=html_file).write_pdf(filename)
        print(f"PDF exported successfully: {filename}")
    finally:
        # Clean up temp HTML file
        import os
        os.unlink(html_file)


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description="Fetch GitHub PRs and export to HTML or PDF"
    )
    parser.add_argument(
        "--repos",
        required=True,
        help="Repositories (format: owner/repo). Multiple repos: 'owner1/repo1,owner2/repo2'"
    )
    parser.add_argument(
        "--username",
        required=True,
        help="GitHub username (for both authored and reviewed PRs)"
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
    parser.add_argument(
        "--include-stats",
        action="store_true",
        help="Include detailed statistics (commits, lines changed)"
    )
    parser.add_argument(
        "--authored-only",
        action="store_true",
        help="Fetch only authored PRs (default: both authored and reviewed)"
    )
    parser.add_argument(
        "--reviewed-only",
        action="store_true",
        help="Fetch only reviewed PRs (default: both authored and reviewed)"
    )

    # Customization options
    parser.add_argument(
        "--primary-color",
        default="#228b22",
        help="Primary color for merged PRs (default: #228b22)"
    )
    parser.add_argument(
        "--bg-color",
        default="#f5f5f5",
        help="Background color (default: #f5f5f5)"
    )
    parser.add_argument(
        "--text-color",
        default="#333333",
        help="Text color (default: #333333)"
    )
    parser.add_argument(
        "--font-family",
        default="Arial, sans-serif",
        help="Font family (default: Arial, sans-serif)"
    )
    parser.add_argument(
        "--custom-title",
        default="",
        help="Custom report title (default: auto-generated)"
    )
    parser.add_argument(
        "--no-descriptions",
        action="store_true",
        help="Hide PR descriptions"
    )
    parser.add_argument(
        "--no-repo-names",
        action="store_true",
        help="Hide repository names"
    )
    parser.add_argument(
        "--max-description-length",
        type=int,
        default=500,
        help="Maximum description length (default: 500)"
    )
    parser.add_argument(
        "--sort-by",
        choices=["date-newest", "date-oldest", "pr-number", "status"],
        default="date-newest",
        help="Sort PRs by (default: date-newest)"
    )
    parser.add_argument(
        "--filter-status",
        nargs="+",
        choices=["MERGED", "OPEN", "CLOSED"],
        default=["MERGED", "OPEN", "CLOSED"],
        help="Include only these statuses (default: all)"
    )

    args = parser.parse_args()

    # Parse repositories
    repos = [repo.strip() for repo in args.repos.replace(',', ' ').split() if '/' in repo]

    if not repos:
        print("Error: No valid repositories provided (format: owner/repo)")
        return

    # Determine output format and filename
    output_format = "pdf" if args.pdf else "html"
    if args.output:
        output_filename = args.output
    else:
        output_filename = f"github_prs.{output_format}"

    # Build customization dict
    sort_by_map = {
        "date-newest": "Date (newest first)",
        "date-oldest": "Date (oldest first)",
        "pr-number": "PR Number",
        "status": "Status"
    }

    customization = {
        'show_description': not args.no_descriptions,
        'show_repo_name': not args.no_repo_names,
        'max_description_length': args.max_description_length,
        'sort_by': sort_by_map[args.sort_by],
        'filter_status': args.filter_status,
        'primary_color': args.primary_color,
        'bg_color': args.bg_color,
        'text_color': args.text_color,
        'font_family': args.font_family,
        'custom_title': args.custom_title
    }

    repo_names = ", ".join(repos) if len(repos) <= 3 else f"{len(repos)} repositories"
    print(f"Fetching PRs by {args.username} from {repo_names}...")
    print(f"Output format: {output_format.upper()}")

    # Determine what to fetch
    fetch_authored = not args.reviewed_only
    fetch_reviewed = not args.authored_only

    # Fetch PRs from all repositories
    fetcher = GitHubPRFetcher(token=args.token)
    all_prs = []

    for repo in repos:
        try:
            owner, repo_name = repo.split('/')

            # Fetch authored PRs
            if fetch_authored:
                print(f"Fetching authored PRs from {repo}...")
                authored_prs = fetcher.fetch_user_prs(owner, repo_name, args.username)
                if authored_prs:
                    formatted_authored = fetcher.format_pr_data(authored_prs, owner, repo_name, args.include_stats)
                    for pr in formatted_authored:
                        pr['pr_type'] = 'Authored'
                    all_prs.extend(formatted_authored)
                    print(f"  Found {len(authored_prs)} authored PR(s)")

            # Fetch reviewed PRs
            if fetch_reviewed:
                print(f"Fetching reviewed PRs from {repo}...")
                reviewed_prs = fetcher.fetch_reviewed_prs(owner, repo_name, args.username)
                if reviewed_prs:
                    formatted_reviewed = fetcher.format_pr_data(reviewed_prs, owner, repo_name, args.include_stats)
                    for pr in formatted_reviewed:
                        pr['pr_type'] = 'Reviewed'
                    all_prs.extend(formatted_reviewed)
                    print(f"  Found {len(reviewed_prs)} reviewed PR(s)")

        except Exception as e:
            print(f"Error fetching from {repo}: {e}")

    if not all_prs:
        print("No PRs found")
        return

    # Count by type
    authored_count = sum(1 for pr in all_prs if pr.get('pr_type') == 'Authored')
    reviewed_count = sum(1 for pr in all_prs if pr.get('pr_type') == 'Reviewed')
    print(f"\nFound {len(all_prs)} total PR(s): {authored_count} authored, {reviewed_count} reviewed")

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

            all_prs = filter_prs_by_date(all_prs, start_date, end_date)
            print(f"After filtering: {len(all_prs)} PRs")

            if not all_prs:
                print("No PRs found matching the date filter")
                return
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return

    # Export to chosen format
    print(f"\nExporting to {output_format.upper()}...")
    if args.pdf:
        export_to_pdf(all_prs, output_filename, repo_names, args.username, customization)
    else:
        export_to_html(all_prs, output_filename, repo_names, args.username, customization)

    print(f"Done! Check {output_filename}")


if __name__ == "__main__":
    main()
