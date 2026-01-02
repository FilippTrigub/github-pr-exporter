#!/usr/bin/env python3
"""
Streamlit app for GitHub PR Exporter
"""

import streamlit as st
from datetime import datetime, timedelta
import tempfile
import os
import time
from fetch_github_prs import GitHubPRFetcher, export_to_html, export_to_pdf, filter_prs_by_date, parse_date_filter

st.set_page_config(
    page_title="GitHub PR Exporter",
    page_icon="📊",
    layout="centered"
)

# Initialize session state for PR data
if 'pr_data' not in st.session_state:
    st.session_state.pr_data = None
if 'fetch_params' not in st.session_state:
    st.session_state.fetch_params = None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_prs_cached(repos_tuple, username, token, include_stats, fetch_authored, fetch_reviewed):
    """
    Cached function to fetch PRs. Results are cached for 5 minutes.

    Args:
        repos_tuple: Tuple of repository strings (tuples are hashable for caching)
        username: GitHub username
        token: GitHub token (optional)
        include_stats: Whether to include detailed statistics
        fetch_authored: Whether to fetch authored PRs
        fetch_reviewed: Whether to fetch reviewed PRs

    Returns:
        List of PR dictionaries
    """
    repos = list(repos_tuple)
    fetcher = GitHubPRFetcher(token if token else None)
    all_prs = []

    for repo in repos:
        try:
            owner, repo_name = repo.split('/')

            # Fetch authored PRs
            if fetch_authored:
                authored_prs = fetcher.fetch_user_prs(owner, repo_name, username)
                if authored_prs:
                    formatted_authored = fetcher.format_pr_data(authored_prs, owner, repo_name, include_stats)
                    for pr in formatted_authored:
                        pr['pr_type'] = 'Authored'
                    all_prs.extend(formatted_authored)

            # Fetch reviewed PRs
            if fetch_reviewed:
                reviewed_prs = fetcher.fetch_reviewed_prs(owner, repo_name, username)
                if reviewed_prs:
                    formatted_reviewed = fetcher.format_pr_data(reviewed_prs, owner, repo_name, include_stats)
                    for pr in formatted_reviewed:
                        pr['pr_type'] = 'Reviewed'
                    all_prs.extend(formatted_reviewed)

        except Exception as e:
            # Store error in the result
            st.warning(f"Error fetching from {repo}: {str(e)}")

    return all_prs

st.title("📊 GitHub PR Exporter")
st.markdown("Export your GitHub pull requests to HTML or PDF")

# Create tabs
tab1, tab2 = st.tabs(["📋 Fetch PRs", "🎨 Customize"])

with tab1:
    # Input fields
    st.subheader("Repository Details")

    repos_input = st.text_area(
        "Repositories *",
        placeholder="owner/repo (e.g., facebook/react)\nOne per line or comma-separated",
        help="Enter one or more repositories in the format: owner/repo"
    )

    username = st.text_input("Username *", placeholder="e.g., yourusername")

    token = st.text_input(
        "GitHub Token (optional)",
        type="password",
        help="Required for private repos. Increases rate limit from 60 to 5000 requests/hour"
    )

    st.subheader("Date Filtering (optional)")

    date_filter_type = st.radio(
        "Filter by:",
        ["All PRs", "Last Month", "Specific Month", "Custom Date Range"],
        horizontal=True
    )

    start_date = None
    end_date = None

    if date_filter_type == "Specific Month":
        col1, col2 = st.columns(2)
        with col1:
            month = st.selectbox("Month", range(1, 13), format_func=lambda x: datetime(2000, x, 1).strftime("%B"))
        with col2:
            year = st.number_input("Year", min_value=2000, max_value=datetime.now().year, value=datetime.now().year)
        start_date = f"{month:02d}.{year}"
        end_date = start_date

    elif date_filter_type == "Custom Date Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date_input = st.date_input("Start Date")
            start_date = start_date_input.strftime("%d.%m.%Y") if start_date_input else None
        with col2:
            end_date_input = st.date_input("End Date")
            end_date = end_date_input.strftime("%d.%m.%Y") if end_date_input else None

    elif date_filter_type == "Last Month":
        today = datetime.now()
        first_day_current = today.replace(day=1)
        last_day_prev = first_day_current - timedelta(days=1)
        start_date = last_day_prev.replace(day=1).strftime("%d.%m.%Y")
        end_date = last_day_prev.strftime("%d.%m.%Y")

    st.subheader("Output Options")

    include_stats = st.checkbox("Include detailed statistics", value=True)

    output_format = st.radio("Export as:", ["HTML", "PDF"], horizontal=True)

    submitted = st.button("Fetch PRs", type="primary", use_container_width=True)

    if submitted:
        # Parse repositories
        repos = []
        if repos_input:
            # Split by newlines and commas, strip whitespace
            for line in repos_input.replace(',', '\n').split('\n'):
                line = line.strip()
                if line and '/' in line:
                    repos.append(line)

        # Validation
        if not repos or not username:
            st.error("Please fill in all required fields (Repositories and Username)")
        else:
            # Show progress
            progress_container = st.empty()
            start_time = time.time()

            with progress_container.container():
                st.info(f"🔄 Fetching PRs from {len(repos)} repositor{'y' if len(repos) == 1 else 'ies'}...")
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Fetch PRs using cached function with manual progress updates
                repos_tuple = tuple(repos)
                all_prs = []

                for idx, repo in enumerate(repos):
                    status_text.text(f"Fetching from {repo}...")
                    progress_bar.progress((idx + 1) / len(repos))

                # Use the cached function
                all_prs = fetch_prs_cached(
                    repos_tuple,
                    username,
                    token if token else None,
                    include_stats,
                    fetch_authored=True,
                    fetch_reviewed=True
                )

                elapsed_time = time.time() - start_time
                status_text.text(f"✅ Completed in {elapsed_time:.1f} seconds")
                time.sleep(0.5)  # Brief pause to show completion

            progress_container.empty()

            if not all_prs:
                st.warning("No pull requests found")
            else:
                # Apply date filter if needed
                if start_date or end_date:
                    start_dt = parse_date_filter(start_date) if start_date else None
                    end_dt = parse_date_filter(end_date) if end_date else None
                    all_prs = filter_prs_by_date(all_prs, start_dt, end_dt)

                    if not all_prs:
                        st.warning("No pull requests found matching the date filter")
                        st.stop()

                # Store in session state for persistent access
                st.session_state.pr_data = all_prs
                st.session_state.fetch_params = {
                    'repos': repos,
                    'username': username,
                    'output_format': output_format,
                    'include_stats': include_stats
                }

    # Display results from session state (persists across reruns)
    if st.session_state.pr_data is not None:
        all_prs = st.session_state.pr_data
        fetch_params = st.session_state.fetch_params

        # Count by type
        authored_count = sum(1 for pr in all_prs if pr.get('pr_type') == 'Authored')
        reviewed_count = sum(1 for pr in all_prs if pr.get('pr_type') == 'Reviewed')

        # Display aggregate statistics
        st.success(f"✅ Found {len(all_prs)} pull request(s): {authored_count} authored, {reviewed_count} reviewed")

        if fetch_params.get('include_stats', False):
            st.subheader("📈 Aggregate Statistics")
            col1, col2, col3, col4 = st.columns(4)

            total_commits = sum(pr.get('commits', 0) for pr in all_prs)
            total_additions = sum(pr.get('additions', 0) for pr in all_prs)
            total_deletions = sum(pr.get('deletions', 0) for pr in all_prs)
            total_changes = total_additions + total_deletions

            with col1:
                st.metric("Total PRs", len(all_prs))
            with col2:
                st.metric("Total Commits", f"{total_commits:,}")
            with col3:
                st.metric("Lines Added", f"{total_additions:,}")
            with col4:
                st.metric("Lines Deleted", f"{total_deletions:,}")

            st.markdown("---")

        # Display PR table
        st.subheader("Pull Requests")

        # Format data for display
        display_data = []
        for pr in all_prs:
            row = {
                "Type": pr.get('pr_type', 'Unknown'),
                "Repo": pr.get('repo', 'Unknown'),
                "PR": f"#{pr['number']}",
                "Title": pr['title'][:50] + "..." if len(pr['title']) > 50 else pr['title'],
                "Status": "MERGED" if pr['merged'] else pr['state'].upper(),
                "Date": pr['merged_at'] if pr['merged'] else pr['created_at']
            }

            if fetch_params.get('include_stats', False):
                row.update({
                    "Commits": pr.get('commits', 0),
                    "Lines Changed": f"+{pr.get('additions', 0)} -{pr.get('deletions', 0)}"
                })

            display_data.append(row)

        st.dataframe(display_data, use_container_width=True, hide_index=True)

        # Export button (now outside fetch scope, uses session state)
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            output_format = fetch_params.get('output_format', 'HTML')
            if st.button(f"📥 Export to {output_format}", use_container_width=True, type="primary"):
                with st.spinner(f"Generating {output_format}..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format.lower()}") as tmp:
                        repos = fetch_params['repos']
                        username = fetch_params['username']
                        repo_names = ", ".join(repos) if len(repos) <= 3 else f"{len(repos)} repositories"

                        # Get customization settings from session state
                        custom_settings = st.session_state.get('customization', {})

                        if output_format == "HTML":
                            export_to_html(all_prs, tmp.name, repo_names, username, custom_settings)
                            mime_type = "text/html"
                        else:
                            export_to_pdf(all_prs, tmp.name, repo_names, username, custom_settings)
                            mime_type = "application/pdf"

                        # Read file for download
                        with open(tmp.name, 'rb') as f:
                            file_data = f.read()

                        # Cleanup
                        os.unlink(tmp.name)

                    st.success(f"{output_format} generated successfully!")

                    # Download button
                    filename = f"github_prs_{username}.{output_format.lower()}"
                    st.download_button(
                        label=f"💾 Download {output_format}",
                        data=file_data,
                        file_name=filename,
                        mime=mime_type,
                        use_container_width=True
                    )

with tab2:
    st.subheader("Customization Options")
    st.markdown("Customize the appearance and content of your exported reports")

    st.markdown("### Report Content")

    show_description = st.checkbox("Show PR descriptions", value=True)
    show_repo_name = st.checkbox("Show repository name", value=True)
    max_description_length = st.slider("Max description length (characters)", 100, 1000, 500, 50)

    st.markdown("### Sorting & Filtering")

    sort_by = st.selectbox(
        "Sort PRs by",
        ["Date (newest first)", "Date (oldest first)", "PR Number", "Status"],
        index=0
    )

    filter_status = st.multiselect(
        "Include only these statuses",
        ["MERGED", "OPEN", "CLOSED"],
        default=["MERGED", "OPEN", "CLOSED"]
    )

    st.markdown("### Appearance (HTML only)")

    col1, col2 = st.columns(2)
    with col1:
        primary_color = st.color_picker("Primary color", "#228b22")
        bg_color = st.color_picker("Background color", "#f5f5f5")
    with col2:
        text_color = st.color_picker("Text color", "#333333")
        font_family = st.selectbox(
            "Font family",
            ["Arial, sans-serif", "Georgia, serif", "Courier New, monospace", "Verdana, sans-serif"]
        )

    custom_title = st.text_input("Custom report title (leave empty for default)", "")

    st.markdown("---")
    st.info("💡 These settings will be applied when you export from the 'Fetch PRs' tab")

    # Store settings in session state
    if 'customization' not in st.session_state:
        st.session_state.customization = {}

    st.session_state.customization = {
        'show_description': show_description,
        'show_repo_name': show_repo_name,
        'max_description_length': max_description_length,
        'sort_by': sort_by,
        'filter_status': filter_status,
        'primary_color': primary_color,
        'bg_color': bg_color,
        'text_color': text_color,
        'font_family': font_family,
        'custom_title': custom_title
    }

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p>Need a GitHub token? <a href='https://github.com/settings/tokens' target='_blank'>Generate one here</a></p>
    <p>Made with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
