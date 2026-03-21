# March Madness 2026 Bracket — Project Spec

## Overview

We are building a webpage tool for tracking results of a March Madness basketball pool. The tool will pull live tournament scores and determine which pool participants are winning based on their purchased grid squares.

## How the Pool Works

### The Grid

The pool is based on a **10×10 grid** (100 squares total). Participants purchase one or more squares in the grid. Each square has a coordinate expressed as **Y/X**.

### Axes

- **Y-axis (rows 0–9):** Represents the **lower-ranked team** (worse seed) in each game. A higher seed number = worse rank (e.g., seed 12 is lower-ranked than seed 2).
- **X-axis (columns 0–9):** Represents the **higher-ranked team** (better seed) in each game. A lower seed number = better rank (e.g., seed 5 is higher-ranked than seed 7).

### Number Assignment

The numbers 0–9 on each axis are **randomly drawn** after participants have already selected their squares. This means no one knows which numbers their squares will correspond to until the draw happens.

### Determining Winners

Every game from **Round 1 onwards** (excluding First Four) produces exactly **1 winner** on the grid. The winning square is determined by:

1. **Identify seeds:** Compare the two teams' seeds. The higher seed number = worse-ranked team. The lower seed number = better-ranked team.
2. **Take the last digit of each team's final score:**
   - Last digit of the **worse seed's** score → **Y-axis**
   - Last digit of the **better seed's** score → **X-axis**
3. The square at coordinate **Y/X** is the winner for that game.

**Example:** `(12) High Point 83, (5) Wisconsin 82`
- Worse seed: High Point (12) — score 83 → last digit **3** → Y-axis
- Better seed: Wisconsin (5) — score 82 → last digit **2** → X-axis
- Winning square: **3/2**

### Payouts

Each game awards a fixed dollar amount based on the round:

| Round | Name | Games | Payout per Game | Round Total |
|---|---|---|---|---|
| 1 | Round of 64 | 32 | $50 | $1,600 |
| 2 | Round of 32 | 16 | $100 | $1,600 |
| 3 | Sweet 16 | 8 | $200 | $1,600 |
| 4 | Elite Eight | 4 | $400 | $1,600 |
| 5 | Final Four | 2 | $800 | $1,600 |
| 6 | Championship | 1 | $2,000 | $2,000 |
| | | **63 games** | | **$10,000** |

- **Cost per square:** $100
- **Total squares:** 100
- **Total prize pool:** $10,000

## Hosting & Deployment

The tool is hosted on **GitHub Pages** for free, accessible from any device (desktop, phone, tablet) via a browser.

- **Repository:** `grantaiclawdbot-delegate/march-madness-2026` (public)
- **URL:** `https://grantaiclawdbot-delegate.github.io/march-madness-2026/`
- **Local use:** Also works opened directly as a `file://` in a browser (no server needed)

### Grid Configuration Storage

The grid config (axis numbers + participant names) is stored in **three tiers** with cascading priority:

1. **localStorage** — Used for local editing sessions (highest priority)
2. **`data/grid-config.json`** — Committed to the repo; shared source of truth across devices (loaded when localStorage is empty, requires HTTP serving)
3. **Embedded `DEFAULT_GRID` in HTML** — Hardcoded JS object inside `index.html`; works on `file://` protocol when `fetch()` is blocked (lowest priority fallback)

The admin edits the grid using the Tab 1 UI, then uses **Export JSON** to download the config. That file replaces `data/grid-config.json` in the repo. The embedded `DEFAULT_GRID` in the HTML should also be updated to match.

### Tournament Results Data Strategy

Results are fetched using a **three-tier approach**:

1. **Primary: Live API calls from the browser.** On page load, the webpage fetches scores directly from `https://ncaa-api.henrygd.me` for each tournament date (up to today, in parallel). This provides real-time data with no server infrastructure.

2. **Fallback: `data/tournament-results.json`** — A pre-fetched snapshot committed to the repo. Loaded if the live API is unreachable (requires HTTP serving). The URL includes a cache-busting `?t=<timestamp>` parameter so browsers always fetch the latest version after a push — bypassing both browser cache and CDN edge cache.

3. **Embedded `FALLBACK_RESULTS` in HTML** — Hardcoded JS object inside `index.html`; works on `file://` protocol when `fetch()` is blocked.

The **source badge** distinguishes all three tiers: "LIVE from NCAA API", "Static fallback data" (JSON file loaded from GitHub Pages), or "Embedded snapshot (offline)" (embedded FALLBACK_RESULTS used).

`update_scores.py` keeps **all three data locations in sync** on every run: it updates `data/tournament-results.json`, then uses regex to replace the `FALLBACK_RESULTS` constant in both `index.html` and `index-b.html`, then commits and pushes all three files together. This means the embedded snapshot is always as current as the JSON file.

If CORS proves to be a persistent issue, a **GitHub Actions cron job** can be set up to auto-fetch results every 15–30 minutes on game days and commit the updated JSON.

### Data Normalization

All data — regardless of source (live API, static JSON, or embedded fallback) — passes through `normalizeResults()` before rendering. This function:

1. **Strips invalid rounds** — Removes any round not in `ROUND_SCHEDULE` (e.g. First Four with round 0). This is critical because external data sources may include rounds we don't want to display.
2. **Ensures all 6 rounds exist** — Adds missing rounds with empty game arrays.
3. **Pads TBD games** — If a round has fewer games than `expectedGames`, fills the remainder with TBD placeholders.

This was added because the three data tiers (live API, static JSON, embedded JS) can get out of sync. Rather than relying on each source being perfectly formatted, the normalizer is the single point of enforcement. **Any changes to which rounds are displayed or how games are structured should be made in `normalizeResults()` and `ROUND_SCHEDULE`.**

### Caching & Deployment Notes

GitHub Pages uses CDN caching that can persist after a new deploy, even with a green checkmark in Actions. Key lessons:

- **Always keep all data files (`data/*.json`) and embedded JS constants in sync** when making structural changes (e.g. removing a round). If the static JSON still has old data, GitHub Pages will serve it via `fetch()` even though the embedded fallback is correct.
- **Defensive normalization** (`normalizeResults()`) is the safety net — it makes rendering correct regardless of stale cached data.
- **Testing:** After pushing, use `?v=N` query string or incognito to bypass browser cache. For CDN cache, an empty commit can force a redeploy, but edge caching may still delay propagation.

## Web Tool

### Tab 1: Grid Setup

A 10×10 grid displaying the pool configuration:

1. **Locked by default** — Grid is read-only on load. Axis inputs are disabled, cells are not clickable, and action buttons are visually greyed out (opacity + no hover highlight). This makes it clear they are disabled, not just non-functional.
2. **Enable editing via console** — Run `enableGridEditing()` in the browser DevTools console to unlock the grid, axis inputs, and action buttons. Buttons restore their full color and hover effects when enabled. No UI toggle is exposed to prevent accidental edits.
3. **Edit axis numbers** — Set the randomly drawn number (0–9) for each position on both the X-axis (higher seed) and Y-axis (lower seed).
4. **Enter participant names** — Click any square to enter/edit the name.
5. **Save** — Writes current state to localStorage.
6. **Export JSON** — Downloads the grid as `grid-config.json` for committing to the repo.
7. **Clear All** — Removes localStorage; on next reload, falls back to embedded default or JSON file.

Axis labels: "Better Seed (Home)" centered below the grid, "Worse Seed (Away)" running vertically along the left side of the grid.

Grid was initially populated by reading `squares config.png` (the pool organizer's image of the physical grid).

### Tab 2: Results Tracker

Displays game results and maps each completed game to a winning square/participant:

1. **Fetch scores** — Attempts live NCAA API fetch for each tournament date. Falls back to static JSON, then to embedded data.
2. **All 6 rounds displayed** — Every round (Round of 64 through Championship) is always shown, even if matchups are not yet determined. First Four is excluded (no payout).
3. **Determine winning square** — For each completed game (Round 1 onwards), compares seeds and takes last digit of each score to produce Y/X coordinate.
4. **Show winners** — Displays participant name from the grid, along with payout amount.
5. **TBD placeholders** — Future rounds with unknown matchups show "X games — Matchups TBD". These are replaced automatically with real matchups when the API returns them.
6. **Game sort order within each round** — Within each round section, games are rendered in this priority order: (1) **Live/in-progress** games first (shown with current score and red "LIVE" label), (2) **Upcoming** (pre) games next (shown with scheduled time and network), (3) **TBD** games after that (matchup not yet determined), (4) **Completed** (final) games last (shown with final score, winning square, and payout). This ensures the most actionable information — live games — is always at the top.
7. **Live/pre indicators** — In-progress games show "LIVE"; upcoming games show time (CT) and network.
8. **Source badge** — Shows whether data is "LIVE from NCAA API", "Static fallback", or embedded.
9. **Last Updated timestamp** — Always displayed in Central Time (CT). Live data uses `toLocaleString('en-US', { timeZone: 'America/Chicago' }) + ' CT'`. Fallback/embedded ISO UTC timestamps are parsed and converted to CT at display time.
10. **Collapsible round sections** — Each round section (Round of 64, Round of 32, etc.) is independently collapsible. A **+** / **−** toggle icon (28×28px circle, white text on a translucent white background) sits on the **left** side of the section header: **+** when collapsed, **−** when expanded. Tap/click the header to toggle. Expanded/collapsed state for each round is persisted in `localStorage` under key `mm_results_sections` (object keyed by round number: `{ "1": true, "2": false, ... }` where `true` = expanded). State is restored on every page load and after every `renderResults()` call.
   - **Live auto-expand** — Any round containing at least one in-progress game (`gameState` is not `"final"`, `"pre"`, or `"tbd"`) is automatically expanded on first encounter. "First encounter" means the round has not previously been seen in a live state. A second `localStorage` key `mm_results_live_rounds` (object keyed by round number) tracks which rounds have been seen live. When a round first goes live, it is expanded regardless of any prior localStorage state, and both keys are updated. On subsequent visits, once a round is in `mm_results_live_rounds`, normal `mm_results_sections` state is used — meaning the user can manually collapse a live section and that choice is remembered.

### Tab 3: Leaderboard

A running tally of each participant's total winnings:

1. **Aggregate by person** — Sums all payouts won by each participant across all completed games.
2. **Sorted by total** — Ranked from highest to lowest earnings.
3. **Win count** — Shows number of games won alongside dollar total.

### Tab 4: My Numbers

A reference table showing each participant's grid squares expressed as number pairs:

1. **Reads grid data** — Iterates all 100 cells in `gridData` and extracts the Y-axis number (`gridData.yAxis[y]`) and X-axis number (`gridData.xAxis[x]`) for each occupied cell.
2. **Groups by name** — Collects all Y/X number pairs for each unique participant name. If axis numbers haven't been set yet, shows `?` in place of the digit.
3. **Sorted alphabetically** — Participants listed A–Z (case-insensitive).
4. **Table columns** — Name | Squares (Y/X as comma-separated pairs, e.g., `3/2, 0/7, 5/1`) | # (count of squares).
5. **Live updates** — Re-renders on Save, Clear All, and page load.

---

## Data Sources

### Primary: henrygd/ncaa-api — Free NCAA JSON API

- **Base URL:** `https://ncaa-api.henrygd.me`
- **GitHub:** https://github.com/henrygd/ncaa-api
- **Auth:** None required
- **Rate Limit:** 5 requests/second/IP
- **Format:** JSON
- **Self-host option:** `docker run --rm -p 3000:3000 henrygd/ncaa-api`

#### Endpoints

| Endpoint | Description | Example |
|---|---|---|
| `/scoreboard/basketball-men/d1/{YYYY}/{MM}/{DD}` | All games & scores for a date | `/scoreboard/basketball-men/d1/2026/03/19` |
| `/game/{gameID}` | Game details | `/game/6534597` |
| `/game/{gameID}/boxscore` | Box score | `/game/6534597/boxscore` |
| `/game/{gameID}/play-by-play` | Play-by-play | `/game/6534597/play-by-play` |
| `/game/{gameID}/scoring-summary` | Scoring summary | `/game/6534597/scoring-summary` |
| `/game/{gameID}/team-stats` | Team stats | `/game/6534597/team-stats` |
| `/standings/basketball-men/d1` | Standings | — |
| `/rankings/basketball-men/d1/{poll}` | Rankings | `/rankings/basketball-men/d1/associated-press` |
| `/schools-index` | All schools | — |

#### Scoreboard Response Shape

Each game object includes:

- `gameID` — unique identifier (use for `/game/{id}` detail calls)
- `away` / `home` — team short name, seed, score, winner flag, conference
- `startTime` — tip-off time (ET from API; converted to CT before storage/display)
- `network` — broadcast network (CBS, TBS, TNT, truTV)
- `gameState` — e.g. `final`, `live`, `pre`

#### Tournament Date Map (2026)

| Round | Dates |
|---|---|
| First Four | Mar 17–18 |
| First Round | Mar 19–20 |
| Second Round | Mar 21–22 |
| Sweet 16 | Mar 27–28 |
| Elite Eight | Mar 29–30 |
| Final Four | Apr 4 |
| Championship | Apr 6 |

### Backup Sources

#### 1. Kaggle — March Machine Learning Mania 2026

- **URL:** https://www.kaggle.com/competitions/march-machine-learning-mania-2026
- **Format:** CSV (downloadable datasets)
- **Auth:** Free Kaggle account
- **Coverage:** Historical data (2008–2025) plus 2026 tournament data
- **Best for:** Bulk historical analysis, seed/team stats
- **Limitation:** Not real-time; updated periodically

#### 2. Olympics.com — Full Schedule & Results

- **URL:** https://www.olympics.com/en/news/basketball-ncaa-march-madness-2026-full-schedule-results-scores-complete-list
- **Format:** HTML (would need scraping or WebFetch)
- **Auth:** None
- **Best for:** Human-readable complete game list with scores
- **Limitation:** Not structured data; requires parsing

#### 3. NCAA.com — Official Bracket

- **URL:** https://www.ncaa.com/news/basketball-men/mml-official-bracket/2026-03-19/2026-ncaa-tournament-bracket-schedule-scores-march-madness
- **Format:** HTML
- **Auth:** None
- **Best for:** Authoritative source of truth for bracket/seedings
- **Limitation:** Not structured data; the henrygd/ncaa-api already proxies this data as JSON

---

## A/B Testing

Two versions of the UI are deployed for A/B testing:

| Version | File | URL | Differences |
|---|---|---|---|
| B (mobile-optimized) | `index.html` | `https://grantaiclawdbot-delegate.github.io/march-madness-2026/` | Blue title (`#1976d2`), mobile-responsive layout — **main URL** |
| A (original) | `index-b.html` | `https://grantaiclawdbot-delegate.github.io/march-madness-2026/index-b.html` | Red title (`#ef5350`), desktop-first |

### Version B mobile changes

- Blue title color instead of red
- Tighter tab buttons that stretch to fill width on small screens
- Grid cells reduced from 80px to 72px wide on mobile (increased from 56px to reduce name text wrapping), with a "← Scroll →" hint
- `overflow-x: auto` scroll wrappers on all results tables
- Reduced table cell padding and font sizes on mobile
- Reduced tab content padding (12px vs 24px) on mobile
- Leaderboard uses full width on mobile
- All changes are gated behind a `@media (max-width: 600px)` query

### Version B — Grid Setup table (Tab 1) mobile improvements

The Grid Setup table on the B version has additional mobile-specific enhancements:

- **Horizontal scrolling with sticky Y-axis column** — The table scrolls horizontally while the first column (Y-axis row labels) stays frozen/sticky so it remains visible while the user swipes right.
- **Scroll shadow hint** — A subtle right-edge gradient shadow overlays the table container to signal that the table is scrollable. The shadow fades out automatically when the user reaches the right end of the table (implemented via a scroll event listener that toggles a CSS class).
- **Reduced cell size** — Cell padding and font sizes are smaller on mobile to fit more content on screen. Cell name font size is 0.58rem (reduced from 0.68rem to minimize text wrapping within the 72px-wide cells).
- **Vertical axis label visible on mobile** — The vertical "Worse Seed (Away)" label is shown on mobile at a reduced font size (0.65rem) and padding. It is visible at the initial (unscrolled) position and scrolls with the grid when the user swipes right. There is no overlap with the sticky first column: the label scrolls fully off-screen at precisely the same point the sticky column engages.

Both versions share identical data (same `DEFAULT_GRID`, `FALLBACK_RESULTS`, `ROUND_SCHEDULE`, and data fetching logic).

## Project Structure

```
March Madness Bracket/
├── index.html                      # Version B — mobile-optimized UI (blue title) — main URL
├── index-b.html                    # Version A — original UI (red title), desktop-first
├── update_scores.py                # Score update automation script (see below)
├── SPEC.md                         # This file — full project specification
├── .gitignore                      # Excludes .claude/ directory
├── squares config.png              # Original pool grid image (source for names)
└── data/
    ├── grid-config.json            # Grid axis numbers + participant names (JSON)
    └── tournament-results.json     # Pre-fetched game results snapshot (JSON)
```

## Score Update Script (`update_scores.py`)

`update_scores.py` automates the complete score update workflow in a single command.

### What it does

1. **Fetches scores** from `https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/{year}/{month}/{day}` for all tournament dates up to today (Mar 19–20 for Round 1, Mar 21–22 for Round 2, etc.)
2. **Updates `data/tournament-results.json`** — scores, game states (`pre`/`live`/`final`), and any new games that appear for later rounds
3. **Updates `FALLBACK_RESULTS`** in both `index.html` and `index-b.html` — replaces the embedded JS constant with the new data
4. **Commits and pushes** — runs `git add`, `git commit`, and `git push origin master` if anything changed. Skips if data is unchanged.

### Usage

```bash
python update_scores.py
```

No arguments needed. Run from the repo root. Uses only Python standard library (`json`, `re`, `os`, `subprocess`, `sys`, `datetime`, `urllib`).

### Key behaviors

- **Idempotent** — safe to run multiple times; only commits when data actually changed
- **API format** — actual NCAA API shape is `{ games: [{ game: { away: {...}, home: {...}, ... } }] }` (teams are inside `game`, not a separate `teams` array)
- **ET → CT conversion** — `startTime` from the API is Eastern Time; the script converts to Central (subtract 1 hour) before storing
- **Merge strategy** — updates existing games by `gameID` matching; adds new games; never removes games (in case API has intermittent issues)
- **No false commits** — compares rounds data (excluding `lastUpdated`) to decide whether to write files

### Key Implementation Details

- **Header title color** — In both `index.html` and `index-b.html`, the "March Madness 2026" title is styled in **yellow** (`#FFD700`). The subtitle span ("— Squares Pool") uses the default text color in both.
- **Single HTML file** — No build tools, no frameworks, no dependencies. All CSS and JS are inline.
- **Embedded data** — `DEFAULT_GRID` and `FALLBACK_RESULTS` are hardcoded as JS objects in `index.html` so it works when opened via `file://` protocol (where `fetch()` is blocked).
- **localStorage key** — `mm2026_grid` stores local grid edits. Clear it to revert to the embedded default.
- **Tab persistence** — `mm_active_tab` stores the last active tab name (`grid`, `results`, `leaderboard`, `mynumbers`). On page load, both `index.html` and `index-b.html` read this key and restore the previously viewed tab instead of defaulting to Grid Setup. The key is written every time the user switches tabs.
- **Results section states** — `mm_results_sections` stores an object of `{ roundNumber: boolean }` pairs where `true` = expanded. Written on every toggle and when a round is auto-expanded. Read on every `renderResults()` call to restore state. Default (no key) = all collapsed except live rounds.
- **Live round tracking** — `mm_results_live_rounds` stores `{ roundNumber: true }` for every round that has ever been seen in a live/in-progress state. Used to distinguish "newly live" rounds (auto-expand override) from rounds the user has already had a chance to interact with (respect `mm_results_sections`).
- **Live API parsing** — The NCAA API response format is `{ games: [{ game: { away: {...}, home: {...}, ... } }] }`. Teams are nested directly inside `game` as `away` and `home` objects. The parser filters to tournament games only (both teams must have seeds) and normalizes into the internal format.
- **Round detection** — Games are assigned to rounds by matching their date against `ROUND_SCHEDULE` (a hardcoded date-to-round mapping in the JS).

## How to Recreate This Project

1. **Create a public GitHub repo** under any account.
2. **Copy `index.html`** — it's fully self-contained with embedded grid config and fallback results data.
3. **Copy `data/grid-config.json`** and **`data/tournament-results.json`** — these are fetched when served over HTTP (GitHub Pages) but not required since data is also embedded.
4. **Enable GitHub Pages** — Settings → Pages → Deploy from branch (main/master, root).
5. **Update grid names** — Edit via Tab 1 UI, click Export JSON, replace `data/grid-config.json`, and update the `DEFAULT_GRID` object in `index.html` to match.
6. **Update fallback results** — Run `python update_scores.py` from the repo root. This fetches the latest scores, updates `data/tournament-results.json` and the `FALLBACK_RESULTS` constant in both HTML files, then commits and pushes everything together.
7. **Push to GitHub** — `git add -A && git commit -m "update" && git push`.

## GitHub Setup

- **Repo:** `grantaiclawdbot-delegate/march-madness-2026` (public)
- **Live URL:** `https://grantaiclawdbot-delegate.github.io/march-madness-2026/`
- **Pages source:** Deploy from `master` branch, root folder
- **Collaborator:** `puresoto` added as collaborator (git credentials on local machine authenticate as this user)
- **No `gh` CLI installed** — repo was created manually via GitHub web UI; pushes via `git push`

## Status (as of 2026-03-21)

- Grid fully populated with all 100 participant names from pool image
- Round of 64 (Mar 19–20): all 32 games complete, results showing with winning squares
- Round of 32 (Mar 21–22): 8 games in progress on Mar 21, 8 games scheduled for Mar 22
- Live NCAA API confirmed working when served over HTTP (GitHub Pages)
- Site accessible on desktop and iPhone via GitHub Pages URL
- `update_scores.py` operational — run `python update_scores.py` to sync scores and push
  - Updates all three data locations: `data/tournament-results.json`, `index.html` FALLBACK_RESULTS, `index-b.html` FALLBACK_RESULTS
  - Commits and pushes all three files together in a single commit
