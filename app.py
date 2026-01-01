#!/usr/bin/env python3
"""
Streamlit app for GitHub PR Exporter
"""

import streamlit as st
from datetime import datetime, timedelta
import tempfile
import os
from fetch_github_prs import GitHubPRFetcher, export_to_html, export_to_pdf, filter_prs_by_date, parse_date_filter

st.set_page_config(
    page_title="GitHub PR Exporter",
    page_icon="📊",
    layout="centered"
)

st.title("📊 GitHub PR Exporter")
st.markdown("Export your GitHub pull requests to HTML or PDF")

# Input fields
with st.form("pr_export_form"):
    st.subheader("Repository Details")

    col1, col2 = st.columns(2)
    with col1:
        owner = st.text_input("Repository Owner *", placeholder="e.g., facebook")
        author = st.text_input("PR Author *", placeholder="e.g., yourusername")

    with col2:
        repo = st.text_input("Repository Name *", placeholder="e.g., react")
        token = st.text_input("GitHub Token (optional)", type="password",
                              help="Required for private repos. Increases rate limit from 60 to 5000 requests/hour")

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

    st.subheader("Output Format")
    output_format = st.radio("Export as:", ["HTML", "PDF"], horizontal=True)

    submitted = st.form_submit_button("Export PRs", type="primary", use_container_width=True)

if submitted:
    # Validation
    if not owner or not repo or not author:
        st.error("Please fill in all required fields (Owner, Repo, Author)")
    else:
        with st.spinner("Fetching pull requests..."):
            try:
                # Fetch PRs
                fetcher = GitHubPRFetcher(token if token else None)
                prs = fetcher.fetch_user_prs(owner, repo, author)

                if not prs:
                    st.warning(f"No pull requests found for {author} in {owner}/{repo}")
                else:
                    formatted_prs = fetcher.format_pr_data(prs)

                    # Apply date filter if needed
                    if start_date or end_date:
                        start_dt = parse_date_filter(start_date) if start_date else None
                        end_dt = parse_date_filter(end_date) if end_date else None
                        formatted_prs = filter_prs_by_date(formatted_prs, start_dt, end_dt)

                        if not formatted_prs:
                            st.warning("No pull requests found matching the date filter")
                            st.stop()

                    st.success(f"Found {len(formatted_prs)} pull request(s)")

                    # Generate export
                    with st.spinner(f"Generating {output_format}..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format.lower()}") as tmp:
                            if output_format == "HTML":
                                export_to_html(formatted_prs, tmp.name, f"{owner}/{repo}", author)
                                mime_type = "text/html"
                            else:
                                export_to_pdf(formatted_prs, tmp.name, f"{owner}/{repo}", author)
                                mime_type = "application/pdf"

                            # Read file for download
                            with open(tmp.name, 'rb') as f:
                                file_data = f.read()

                            # Cleanup
                            os.unlink(tmp.name)

                    st.success(f"{output_format} generated successfully!")

                    # Download button
                    filename = f"github_prs_{owner}_{repo}_{author}.{output_format.lower()}"
                    st.download_button(
                        label=f"📥 Download {output_format}",
                        data=file_data,
                        file_name=filename,
                        mime=mime_type,
                        use_container_width=True
                    )

            except Exception as e:
                st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    <p>Need a GitHub token? <a href='https://github.com/settings/tokens' target='_blank'>Generate one here</a></p>
    <p>Made with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
