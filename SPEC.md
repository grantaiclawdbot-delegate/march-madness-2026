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

2. **Fallback: `data/tournament-results.json`** — A pre-fetched snapshot committed to the repo. Loaded if the live API is unreachable (requires HTTP serving).

3. **Embedded `FALLBACK_RESULTS` in HTML** — Hardcoded JS object inside `index.html`; works on `file://` protocol. Must be manually updated with new results.

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
6. **Live/pre indicators** — In-progress games show "LIVE"; upcoming games show time (CT) and network.
7. **Source badge** — Shows whether data is "LIVE from NCAA API", "Static fallback", or embedded.
8. **Collapsible round sections** — Each round section (Round of 64, Round of 32, etc.) is independently collapsible. Default state on first visit is collapsed. A right-pointing chevron (▶) in the section header rotates 90° when expanded. Tap/click the header to toggle. Expanded/collapsed state for each round is persisted in `localStorage` under key `mm_results_sections` (object keyed by round number: `{ "1": true, "2": false, ... }` where `true` = expanded). State is restored on every page load and after every `renderResults()` call.

### Tab 3: Leaderboard

A running tally of each participant's total winnings:

1. **Aggregate by person** — Sums all payouts won by each participant across all completed games.
2. **Sorted by total** — Ranked from highest to lowest earnings.
3. **Win count** — Shows number of games won alongside dollar total.

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
- Grid cells reduced from 80px to 56px wide on mobile, with a "← Scroll →" hint
- `overflow-x: auto` scroll wrappers on all results tables
- Reduced table cell padding and font sizes on mobile
- Reduced tab content padding (12px vs 24px) on mobile
- Leaderboard uses full width on mobile
- All changes are gated behind a `@media (max-width: 600px)` query

### Version B — Grid Setup table (Tab 1) mobile improvements

The Grid Setup table on the B version has additional mobile-specific enhancements:

- **Horizontal scrolling with sticky Y-axis column** — The table scrolls horizontally while the first column (Y-axis row labels) stays frozen/sticky so it remains visible while the user swipes right.
- **Scroll shadow hint** — A subtle right-edge gradient shadow overlays the table container to signal that the table is scrollable. The shadow fades out automatically when the user reaches the right end of the table (implemented via a scroll event listener that toggles a CSS class).
- **Reduced cell size** — Cell padding and font sizes are smaller on mobile to fit more content on screen.
- **Vertical axis label hidden** — The vertical "Worse Seed (Away)" label on the left side of the grid is hidden on mobile (`display: none`) to give the sticky first column enough room without overlap.

Both versions share identical data (same `DEFAULT_GRID`, `FALLBACK_RESULTS`, `ROUND_SCHEDULE`, and data fetching logic).

## Project Structure

```
March Madness Bracket/
├── index.html                      # Version B — mobile-optimized UI (blue title) — main URL
├── index-b.html                    # Version A — original UI (red title), desktop-first
├── SPEC.md                         # This file — full project specification
├── .gitignore                      # Excludes .claude/ directory
├── squares config.png              # Original pool grid image (source for names)
└── data/
    ├── grid-config.json            # Grid axis numbers + participant names (JSON)
    └── tournament-results.json     # Pre-fetched game results snapshot (JSON)
```

### Key Implementation Details

- **Header title color** — In both `index.html` and `index-b.html`, the "March Madness 2026" title is styled in **yellow** (`#FFD700`). The subtitle span ("— Squares Pool") uses the default text color in both.
- **Single HTML file** — No build tools, no frameworks, no dependencies. All CSS and JS are inline.
- **Embedded data** — `DEFAULT_GRID` and `FALLBACK_RESULTS` are hardcoded as JS objects in `index.html` so it works when opened via `file://` protocol (where `fetch()` is blocked).
- **localStorage key** — `mm2026_grid` stores local grid edits. Clear it to revert to the embedded default.
- **Tab persistence** — `mm_active_tab` stores the last active tab index (0 = Grid Setup, 1 = Results Tracker, 2 = Leaderboard). On page load, both `index.html` and `index-b.html` read this key and restore the previously viewed tab instead of defaulting to Grid Setup. The key is written every time the user switches tabs.
- **Results section states** — `mm_results_sections` stores an object of `{ roundNumber: boolean }` pairs where `true` = expanded. Written on every toggle. Read on every `renderResults()` call to restore state. Default (no key) = all collapsed.
- **Live API parsing** — The NCAA API response format is `{ games: [{ game: {...}, teams: [...] }] }`. The parser filters to tournament games only (both teams must have seeds) and normalizes into the internal format.
- **Round detection** — Games are assigned to rounds by matching their date against `ROUND_SCHEDULE` (a hardcoded date-to-round mapping in the JS).

## How to Recreate This Project

1. **Create a public GitHub repo** under any account.
2. **Copy `index.html`** — it's fully self-contained with embedded grid config and fallback results data.
3. **Copy `data/grid-config.json`** and **`data/tournament-results.json`** — these are fetched when served over HTTP (GitHub Pages) but not required since data is also embedded.
4. **Enable GitHub Pages** — Settings → Pages → Deploy from branch (main/master, root).
5. **Update grid names** — Edit via Tab 1 UI, click Export JSON, replace `data/grid-config.json`, and update the `DEFAULT_GRID` object in `index.html` to match.
6. **Update fallback results** — Fetch new data from `https://ncaa-api.henrygd.me/scoreboard/basketball-men/d1/YYYY/MM/DD`, update `data/tournament-results.json`, and update `FALLBACK_RESULTS` in `index.html`.
7. **Push to GitHub** — `git add -A && git commit -m "update" && git push`.

## GitHub Setup

- **Repo:** `grantaiclawdbot-delegate/march-madness-2026` (public)
- **Live URL:** `https://grantaiclawdbot-delegate.github.io/march-madness-2026/`
- **Pages source:** Deploy from `master` branch, root folder
- **Collaborator:** `puresoto` added as collaborator (git credentials on local machine authenticate as this user)
- **No `gh` CLI installed** — repo was created manually via GitHub web UI; pushes via `git push`

## Status (as of 2026-03-20)

- Grid fully populated with all 100 participant names from pool image
- Round of 64 Day 1 (Mar 19): 16 games complete, results showing with winning squares
- Round of 64 Day 2 (Mar 20): 16 games upcoming, showing times/networks
- Live NCAA API confirmed working when served over HTTP (GitHub Pages)
- Site accessible on desktop and iPhone via GitHub Pages URL
- Embedded fallback data covers through Mar 20 pre-game state
