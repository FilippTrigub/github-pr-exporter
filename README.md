# GitHub PR Exporter

Export your GitHub pull requests to HTML or PDF with a simple web interface or command line tool.

## Quick Start

### Web App (Recommended)

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Run the Streamlit app:**
   ```bash
   uv run streamlit run app.py
   ```

3. **Open your browser** to the URL shown (usually http://localhost:8501)

4. **Fill in the form** with your repository details and export!

### Command Line

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Generate HTML (default):**
   ```bash
   uv run python fetch_github_prs.py \
     --repos OWNER/REPO \
     --username YOUR_USERNAME
   ```

3. **Generate PDF:**
   ```bash
   uv run python fetch_github_prs.py \
     --repos OWNER/REPO \
     --username YOUR_USERNAME \
     --pdf
   ```

4. **Multiple repositories:**
   ```bash
   uv run python fetch_github_prs.py \
     --repos "owner1/repo1,owner2/repo2" \
     --username YOUR_USERNAME
   ```

## Features

- **Dual interface**: Web app (Streamlit) and command-line tool
- Fetches all PRs (open, closed, and merged) from any GitHub repository
- **Authored AND Reviewed PRs** - see both types of contributions
- **Multi-repository support** - analyze PRs across multiple repos
- **Detailed statistics** - commits, lines changed, files modified
- **Date filtering** with flexible formats (specific dates, months, or "last-month")
- Handles pagination automatically to fetch all PRs
- **HTML output by default** - clean, modern, single-column layout
- **PDF export** via WeasyPrint - same styling as HTML
- **Full customization**:
  - Colors (primary, background, text)
  - Font family
  - Custom report titles
  - Toggle descriptions and repo names
  - Sorting (by date, PR number, status)
  - Status filtering (MERGED/OPEN/CLOSED)
- Professionally formatted output with:
  - PR number and title
  - Prominent status badge (MERGED, OPEN, CLOSED)
  - PR type badge (Authored/Reviewed)
  - Repository name
  - Creation/merge date
  - Direct clickable links to PRs
  - PR description (Unicode-safe)
  - Statistics (commits, lines changed)
- Color-coded status indicators (green for merged, lighter green for open, gray for closed)
- Clean single-column layout - no tables, just pure vertical flow
- Responsive design (HTML) that works on all devices
- Easy to share and view in browsers

## Common Commands

### Last Month's PRs (HTML)
```bash
uv run python fetch_github_prs.py \
  --repos microsoft/vscode \
  --username yourusername \
  --last-month
```

### Specific Month as PDF (December 2024)
```bash
uv run python fetch_github_prs.py \
  --repos facebook/react \
  --username yourusername \
  --start-date 12 \
  --end-date 12 \
  --pdf
```

### Multiple Repos with Statistics
```bash
uv run python fetch_github_prs.py \
  --repos "owner1/repo1,owner2/repo2" \
  --username yourusername \
  --include-stats \
  --pdf
```

### Only Authored PRs (exclude reviewed)
```bash
uv run python fetch_github_prs.py \
  --repos owner/repo \
  --username yourusername \
  --authored-only
```

### Custom Styling
```bash
uv run python fetch_github_prs.py \
  --repos owner/repo \
  --username yourusername \
  --primary-color "#ff0000" \
  --bg-color "#ffffff" \
  --text-color "#000000" \
  --custom-title "My PR Report"
```

### With GitHub Token (Recommended for private repos)
```bash
uv run python fetch_github_prs.py \
  --repos owner/repo \
  --username yourusername \
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
uv run python fetch_github_prs.py --repos OWNER/REPO --username YOUR_USERNAME
```

This creates `github_prs.html` by default with both authored AND reviewed PRs.

### With PDF Export

```bash
uv run python fetch_github_prs.py --repos OWNER/REPO --username YOUR_USERNAME --pdf
```

This creates `github_prs.pdf` instead.

### Multiple Repositories

```bash
uv run python fetch_github_prs.py --repos "owner1/repo1,owner2/repo2,owner3/repo3" --username YOUR_USERNAME
```

Analyze PRs across multiple repositories at once.

### With Statistics

```bash
uv run python fetch_github_prs.py --repos OWNER/REPO --username YOUR_USERNAME --include-stats
```

Includes commits, lines changed, and files modified for each PR.

### With GitHub Token (Recommended)

Using a GitHub token prevents rate limiting and allows access to private repositories:

```bash
uv run python fetch_github_prs.py --repos OWNER/REPO --username YOUR_USERNAME --token YOUR_GITHUB_TOKEN
```

### Custom Output Filename

```bash
# HTML output with custom name
uv run python fetch_github_prs.py --repos OWNER/REPO --username YOUR_USERNAME --output my_prs.html

# PDF output with custom name
uv run python fetch_github_prs.py --repos OWNER/REPO --username YOUR_USERNAME --pdf --output my_prs.pdf
```

### With Date Filtering

Filter PRs by date range using flexible date formats:

```bash
# Filter PRs from last month (simple flag)
uv run python fetch_github_prs.py --repos OWNER/REPO --username USERNAME --last-month

# Filter PRs from December 2024 only
uv run python fetch_github_prs.py --repos OWNER/REPO --username USERNAME --start-date 12 --end-date 12

# Filter PRs from a specific date range
uv run python fetch_github_prs.py --repos OWNER/REPO --username USERNAME --start-date 01.12.2024 --end-date 31.12.2024

# Filter PRs from October 2024 onwards (no end date)
uv run python fetch_github_prs.py --repos OWNER/REPO --username USERNAME --start-date 10

# Filter PRs up to a specific date (no start date)
uv run python fetch_github_prs.py --repos OWNER/REPO --username USERNAME --end-date 15.11.2024
```

### Fetch Only Authored or Reviewed PRs

```bash
# Only authored PRs
uv run python fetch_github_prs.py --repos OWNER/REPO --username USERNAME --authored-only

# Only reviewed PRs
uv run python fetch_github_prs.py --repos OWNER/REPO --username USERNAME --reviewed-only
```

### Customization Options

```bash
uv run python fetch_github_prs.py \
  --repos OWNER/REPO \
  --username USERNAME \
  --primary-color "#2e7d32" \
  --bg-color "#fafafa" \
  --text-color "#212121" \
  --font-family "Georgia, serif" \
  --custom-title "Q4 2024 PR Summary" \
  --sort-by date-oldest \
  --filter-status MERGED OPEN \
  --no-descriptions
```

## Command-Line Arguments

### Required Arguments
| Argument | Description |
|----------|-------------|
| `--repos` | Repositories (format: owner/repo). Multiple: 'owner1/repo1,owner2/repo2' |
| `--username` | GitHub username (for both authored and reviewed PRs) |

### Optional Arguments
| Argument | Description |
|----------|-------------|
| `--token` | GitHub personal access token (recommended) |
| `--output` | Custom output filename |
| `--pdf` | Export to PDF instead of HTML |

### Filtering Options
| Argument | Description |
|----------|-------------|
| `--last-month` | Filter PRs from last month |
| `--start-date` | Start date (dd.mm.yyyy or 1-12) |
| `--end-date` | End date (dd.mm.yyyy or 1-12) |
| `--filter-status` | Include only these statuses (MERGED OPEN CLOSED) |
| `--authored-only` | Fetch only authored PRs |
| `--reviewed-only` | Fetch only reviewed PRs |

### Content Options
| Argument | Description |
|----------|-------------|
| `--include-stats` | Include detailed statistics (commits, lines changed) |
| `--no-descriptions` | Hide PR descriptions |
| `--no-repo-names` | Hide repository names |
| `--max-description-length` | Maximum description length (default: 500) |
| `--sort-by` | Sort by: date-newest, date-oldest, pr-number, status |

### Customization Options
| Argument | Description |
|----------|-------------|
| `--primary-color` | Primary color for merged PRs (default: #228b22) |
| `--bg-color` | Background color (default: #f5f5f5) |
| `--text-color` | Text color (default: #333333) |
| `--font-family` | Font family (default: Arial, sans-serif) |
| `--custom-title` | Custom report title |

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
# Fetch all your PRs as HTML (default) - both authored and reviewed
uv run python fetch_github_prs.py \
  --repos facebook/react \
  --username yourusername \
  --token ghp_yourtoken

# Fetch PRs as PDF with statistics
uv run python fetch_github_prs.py \
  --repos facebook/react \
  --username yourusername \
  --token ghp_yourtoken \
  --include-stats \
  --pdf

# Fetch PRs from November 2024 only
uv run python fetch_github_prs.py \
  --repos microsoft/vscode \
  --username yourusername \
  --start-date 11 \
  --end-date 11 \
  --token ghp_yourtoken \
  --output november_prs.html

# Fetch PRs from last month as PDF
uv run python fetch_github_prs.py \
  --repos google/material-design \
  --username yourusername \
  --last-month \
  --token ghp_yourtoken \
  --pdf \
  --output last_month_prs.pdf

# Multiple repos with custom styling
uv run python fetch_github_prs.py \
  --repos "owner1/repo1,owner2/repo2" \
  --username yourusername \
  --token ghp_yourtoken \
  --primary-color "#1976d2" \
  --custom-title "Q4 2024 Contributions" \
  --sort-by status \
  --filter-status MERGED
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
