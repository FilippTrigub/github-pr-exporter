# Performance Improvement Plan for Streamlit App

## Problems Identified

### 1. **Severe Performance Bottleneck in `fetch_reviewed_prs()` (fetch_github_prs.py:252-305)**
**Current behavior:**
- Fetches ALL PRs from a repository (could be hundreds/thousands)
- For EACH PR, makes an additional API call to check reviews
- Example: repo with 1000 PRs = 1000+ API calls just for reviewed PRs
- For the test run: 110 PRs in remote-code = 110+ API calls to find 7 reviewed PRs

**Impact:**
- Extremely slow for large repositories
- Wastes API rate limits
- User waits minutes for data that should take seconds

### 2. **Secondary Performance Issue in `get_pr_details()` (fetch_github_prs.py:307-335)**
**Current behavior:**
- When `include_stats=True`, makes ANOTHER API call per PR
- Called from `format_pr_data()` line 372
- Doubles the API calls needed

**Impact:**
- 116 authored PRs + 7 reviewed PRs = 123 additional API calls for stats
- Combined with reviewed PR checks: 233+ total API calls for one repo!

### 3. **Session State Timeout Issue (app.py:208-240)**
**Current behavior:**
- Data fetched in one button click (`submitted`)
- Export happens in a NESTED button click inside the results display
- `all_prs` variable only exists within the outer button's scope
- If user navigates away or waits too long, component re-renders and data is lost

**Impact:**
- Download button appears but data may be gone
- User has to re-fetch everything
- Frustrating UX for long-running operations

## Proposed Solutions

### Solution 1: Use GitHub Search API for Reviewed PRs
**Change:** Replace the inefficient loop in `fetch_reviewed_prs()`

**Current approach (fetch_github_prs.py:289-298):**
```python
for pr in prs:  # Loop through ALL PRs
    reviews_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr['number']}/reviews"
    reviews_response = requests.get(reviews_url, headers=self.headers)
    if reviews_response.status_code == 200:
        reviews = reviews_response.json()
        if any(review["user"]["login"] == reviewer for review in reviews):
            all_prs.append(pr)
```

**Better approach:**
Use GitHub's Search API with query: `type:pr repo:owner/repo reviewed-by:username`

**Benefits:**
- Single API call instead of N+1 calls
- GitHub does the filtering server-side
- 100x faster for large repos
- Saves API rate limit

**Tradeoff:**
- Search API has lower rate limits (30/min vs 5000/hour)
- But still WAY better than current approach

### Solution 2: Batch PR Details Requests
**Change:** Get stats data from initial PR fetch instead of additional calls

**Current approach (fetch_github_prs.py:372):**
```python
if include_stats and owner and repo:
    details = self.get_pr_details(owner, repo, pr["number"])  # Extra API call
```

**Better approach:**
The initial PR list endpoint already includes some stats! Use those directly:
```python
# PR data from /repos/{owner}/{repo}/pulls already has:
pr["commits"]     # Available!
pr["additions"]   # Available!
pr["deletions"]   # Available!
pr["changed_files"] # Available!
```

**Benefits:**
- Zero additional API calls
- Instant stats retrieval
- Same data quality

**Implementation:**
Modify `fetch_user_prs()` and `fetch_reviewed_prs()` to preserve these fields

### Solution 3: Store Fetched Data in Session State
**Change:** Persist `all_prs` between button clicks

**Current flow:**
```
[Fetch PRs button] → fetch data → display results
                                    ↓
                        [Export button] → data gone! ❌
```

**Better flow:**
```
[Fetch PRs button] → fetch data → st.session_state['pr_data'] = all_prs
                                    ↓
                                  display results
                                    ↓
                        [Export button] → st.session_state['pr_data'] ✅
```

**Benefits:**
- Data persists across re-renders
- User can export anytime, even after waiting
- Can switch tabs and come back
- Enable "Export" button only when data exists

### Solution 4: Add Caching with @st.cache_data
**Change:** Cache API results to avoid re-fetching

**Implementation:**
```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_all_prs_cached(repos, username, token, include_stats):
    # Fetch logic here
    return all_prs
```

**Benefits:**
- Instant results on re-runs within 5 minutes
- User can adjust filters without re-fetching
- Reduces API calls

### Solution 5: Add Progress Indicators for Long Operations
**Change:** Better UX during slow operations

**Improvements:**
- Show estimated time remaining
- Display PR count as they're fetched
- Add "Cancel" button for long operations
- Show which API calls are happening

**Benefits:**
- User knows app isn't frozen
- Can cancel if taking too long
- Better perceived performance

## Implementation Priority

### Phase 1: Critical Fixes (Immediate) - ✅ COMPLETED
1. ✅ **Solution 1**: Use Search API for reviewed PRs (biggest impact)
   - Implemented in fetch_github_prs.py:252-308
   - Now uses `/search/issues` API with `reviewed-by:` query
   - Single API call instead of N+1 calls

2. ✅ **Solution 2**: Use existing PR stats (eliminate N API calls)
   - Implemented in fetch_github_prs.py:341-392
   - Removed `get_pr_details()` method entirely
   - Uses stats already present in PR data (commits, additions, deletions, changed_files)

3. ✅ **Solution 3**: Store data in session_state (fix download issue)
   - Implemented in app.py:19-23, 201-208, 210-306
   - PR data persists in `st.session_state.pr_data`
   - Export button moved outside fetch scope
   - Download works anytime, even after user waits

**Expected improvement:** 10-50x faster, download always works ✅

### Phase 2: Nice-to-Have (Next) - ✅ COMPLETED
4. ✅ **Solution 4**: Add caching for repeated queries
   - Implemented in app.py:25-71
   - `@st.cache_data(ttl=300)` decorator caches results for 5 minutes
   - Instant results on re-runs

5. ✅ **Solution 5**: Better progress indicators
   - Implemented in app.py:155-186
   - Shows elapsed time for fetch operations
   - Progress bar with status updates per repo

**Expected improvement:** Even better UX ✅

## Code Changes Required

### Files to modify:
1. `fetch_github_prs.py`:
   - `fetch_reviewed_prs()` - use Search API
   - `fetch_user_prs()` - preserve stats fields
   - `format_pr_data()` - use PR stats directly
   - Remove `get_pr_details()` method entirely

2. `app.py`:
   - Add session state for PR data
   - Move export button outside fetch results
   - Add cache decorators
   - Improve progress display

## Testing Plan

### Test Cases:
1. Single repo with few PRs (< 10)
2. Single repo with many PRs (> 100)
3. Multiple repos (4+)
4. With and without statistics
5. Long wait before export
6. Tab switching during fetch
7. Filter changes after fetch

### Success Metrics:
- Fetch time reduced by 90%+ for large repos
- Export works even after 10+ minutes
- No duplicate API calls
- Proper error handling

## Estimated Impact

### Current Performance (from test run):
- 4 repos, 123 PRs, with stats
- ~233+ API calls
- ~2-3 minutes processing time
- Download fails if user waits

### After Fixes:
- 4 repos, 123 PRs, with stats
- ~8-12 API calls total
- ~5-10 seconds processing time
- Download works anytime ✅

**ROI: 20-30x performance improvement**
