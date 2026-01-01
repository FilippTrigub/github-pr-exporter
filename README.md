# GitHub PR Fetcher and Exporter

A Python script that fetches all pull requests authored by you from a specific GitHub repository and exports them to a clean, formatted HTML file (or PDF if desired).

## Quick Start

1. **Install with uv:**
   ```bash
   uv sync
   ```

2. **Generate HTML (default):**
   ```bash
   uv run python fetch_github_prs.py \
     --owner REPO_OWNER \
     --repo REPO_NAME \
     --author YOUR_USERNAME
   ```

3. **Generate PDF:**
   ```bash
   uv run python fetch_github_prs.py \
     --owner REPO_OWNER \
     --repo REPO_NAME \
     --author YOUR_USERNAME \
     --pdf
   ```

## Features

- Fetches all PRs (open, closed, and merged) from any GitHub repository
- Filters PRs by author
- **Date filtering** with flexible formats (specific dates, months, or "last-month")
- Handles pagination automatically to fetch all PRs
- **HTML output by default** - clean, modern, single-column layout
- **Optional PDF export** with `--pdf` flag
- Professionally formatted output with:
  - PR number and title
  - Prominent status badge (MERGED, OPEN, CLOSED)
  - Creation/merge date
  - Direct clickable links to PRs
  - PR description (Unicode-safe)
- Color-coded status indicators (green for merged, lighter green for open, gray for closed)
- Clean single-column layout - no tables, just pure vertical flow
- Responsive design (HTML) that works on all devices
- Easy to share and view in browsers

## Common Commands

### Last Month's PRs (HTML)
```bash
uv run python fetch_github_prs.py \
  --owner microsoft \
  --repo vscode \
  --author yourusername \
  --last-month
```

### Specific Month as PDF (December 2024)
```bash
uv run python fetch_github_prs.py \
  --owner facebook \
  --repo react \
  --author yourusername \
  --start-date 12 \
  --end-date 12 \
  --pdf
```

### Custom Date Range
```bash
uv run python fetch_github_prs.py \
  --owner google \
  --repo angular \
  --author yourusername \
  --start-date 01.11.2024 \
  --end-date 30.11.2024 \
  --output november_prs.html
```

### With GitHub Token (Recommended for private repos)
```bash
uv run python fetch_github_prs.py \
  --owner owner \
  --repo repo \
  --author yourusername \
  --token ghp_yourtoken \
  --pdf
```

## Installation

1. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Sync dependencies:
   ```bash
   uv sync
   ```

That's it! uv will handle Python version and all dependencies automatically.

## Usage

### Basic Usage (HTML output)

```bash
uv run python fetch_github_prs.py --owner REPO_OWNER --repo REPO_NAME --author YOUR_USERNAME
```

This creates `github_prs.html` by default.

### With PDF Export

```bash
uv run python fetch_github_prs.py --owner REPO_OWNER --repo REPO_NAME --author YOUR_USERNAME --pdf
```

This creates `github_prs.pdf` instead.

### With GitHub Token (Recommended)

Using a GitHub token prevents rate limiting and allows access to private repositories:

```bash
uv run python fetch_github_prs.py --owner REPO_OWNER --repo REPO_NAME --author YOUR_USERNAME --token YOUR_GITHUB_TOKEN
```

### Custom Output Filename

```bash
# HTML output with custom name
uv run python fetch_github_prs.py --owner REPO_OWNER --repo REPO_NAME --author YOUR_USERNAME --output my_prs.html

# PDF output with custom name
uv run python fetch_github_prs.py --owner REPO_OWNER --repo REPO_NAME --author YOUR_USERNAME --pdf --output my_prs.pdf
```

### With Date Filtering

Filter PRs by date range using flexible date formats:

```bash
# Filter PRs from last month (simple flag)
uv run python fetch_github_prs.py --owner OWNER --repo REPO --author USERNAME --last-month

# Filter PRs from December 2024 only
uv run python fetch_github_prs.py --owner OWNER --repo REPO --author USERNAME --start-date 12 --end-date 12

# Filter PRs from a specific date range
uv run python fetch_github_prs.py --owner OWNER --repo REPO --author USERNAME --start-date 01.12.2024 --end-date 31.12.2024

# Filter PRs from October 2024 onwards (no end date)
uv run python fetch_github_prs.py --owner OWNER --repo REPO --author USERNAME --start-date 10

# Filter PRs up to a specific date (no start date)
uv run python fetch_github_prs.py --owner OWNER --repo REPO --author USERNAME --end-date 15.11.2024
```

## Command-Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--owner` | Yes | Repository owner (username or org) |
| `--repo` | Yes | Repository name |
| `--author` | Yes | Your GitHub username |
| `--token` | No | GitHub personal access token |
| `--pdf` | No | Export to PDF instead of HTML |
| `--output` | No | Custom output filename |
| `--last-month` | No | Filter PRs from last month |
| `--start-date` | No | Start date (dd.mm.yyyy or 1-12) |
| `--end-date` | No | End date (dd.mm.yyyy or 1-12) |

### Date Filtering Details

- `--last-month` (optional): Filter PRs from last month only (simple flag, no value needed)
- `--start-date` (optional): Start date for filtering PRs
  - **Formats**:
    - `dd.mm.yyyy` (e.g., `01.12.2024` for December 1, 2024)
    - Month number `1-12` (e.g., `12` for December of current year)
- `--end-date` (optional): End date for filtering PRs
  - **Formats**: Same as `--start-date`

**Date filtering behavior:**
- Filters based on merge date for merged PRs, creation date for others
- Month numbers automatically expand to full date ranges:
  - For `--start-date`: First day of that month (00:00:00)
  - For `--end-date`: Last day of that month (23:59:59)
- `--last-month` flag automatically sets both start and end dates to cover the entire previous month

**Output format:**
- Default: HTML (clean, modern, single-column layout)
- With `--pdf`: PDF format (requires fpdf2 library)

## Creating a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token"
3. Give it a descriptive name
4. Select scopes:
   - For public repos: `public_repo`
   - For private repos: `repo`
5. Click "Generate token" and copy it

**Note:** Keep your token secure and never commit it to your repository!

## Examples

```bash
# Fetch all your PRs as HTML (default)
uv run python fetch_github_prs.py \
  --owner facebook \
  --repo react \
  --author yourusername \
  --token ghp_yourtoken

# Fetch PRs as PDF
uv run python fetch_github_prs.py \
  --owner facebook \
  --repo react \
  --author yourusername \
  --token ghp_yourtoken \
  --pdf

# Fetch PRs from November 2024 only
uv run python fetch_github_prs.py \
  --owner microsoft \
  --repo vscode \
  --author yourusername \
  --start-date 11 \
  --end-date 11 \
  --token ghp_yourtoken \
  --output november_prs.html

# Fetch PRs from last month as PDF
uv run python fetch_github_prs.py \
  --owner google \
  --repo material-design \
  --author yourusername \
  --last-month \
  --token ghp_yourtoken \
  --pdf \
  --output last_month_prs.pdf
```

## Output Format

### HTML Output (Default)

The generated HTML file includes:

- **Clean, modern single-column layout** - no tables or complex structures
- **Responsive design** - works on all devices and screen sizes
- **Header**: Your username and repository name
- **Summary**: Total number of PRs found
- **For each PR** (in a single vertical flow):
  - **Prominent status badge**: Color-coded label (MERGED/OPEN/CLOSED)
    - Green badge for merged PRs
    - Light green badge for open PRs
    - Gray badge for closed PRs
  - PR number and title
  - Date (merge date for merged PRs, creation date otherwise)
  - Clickable link to the PR on GitHub
  - Description (first 500 characters, Unicode-safe)
- **Professional styling**: Clean typography, proper spacing, and visual hierarchy
- **Easy to share**: Just send the HTML file or host it anywhere

### PDF Output (with --pdf flag)

The generated PDF includes:

- **Single-column layout** - everything flows vertically
- **Header**: Your username and repository name on every page
- **Summary**: Total number of PRs found
- **For each PR**:
  - Status badge (MERGED/OPEN/CLOSED) with color coding
  - PR number and title
  - Date
  - URL
  - Description (first 500 characters)
- **Footer**: Page numbers
- **Compact formatting** for print-friendly output

## Rate Limiting

- Without a token: 60 requests per hour
- With a token: 5,000 requests per hour

For repositories with many PRs, using a token is highly recommended.

## Troubleshooting

**"GitHub API error: 403"**: You've hit the rate limit. Use a GitHub token or wait an hour.

**"GitHub API error: 404"**: Check that the owner and repo names are correct and that you have access to the repository.

**"No PRs found"**: Verify that the author username is correct and matches your GitHub username exactly.

**"No PRs found matching the date filter"**: Check your date range. The filter uses merge date for merged PRs and creation date for others.

**"Invalid date format"**: Ensure your dates match the supported formats: `dd.mm.yyyy` or `1-12` (month number).

**Unicode/Emoji errors**: The script automatically removes emojis and non-latin-1 characters from PR titles and descriptions to ensure PDF compatibility.

## Quick Tips

💡 **Use a GitHub token** to avoid rate limits (60 requests/hour → 5000 requests/hour)
💡 **HTML is better for sharing** - just send the file or view in browser
💡 **PDF is better for printing** - clean single-column format
💡 **No emojis in PDF** - they're automatically removed for compatibility
💡 **Month numbers are easy** - Just use `12` for December, no need for full dates

## License

Free to use and modify.
