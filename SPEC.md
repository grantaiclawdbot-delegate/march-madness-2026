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

- **Repository:** Hosted under the `grantaiclawdbot-delegate` GitHub account
- **URL:** Served via GitHub Pages (e.g., `https://grantaiclawdbot-delegate.github.io/march-madness-2026/`)

### Grid Configuration Storage

The grid config (axis numbers + participant names) is stored in a **static JSON file** (`data/grid-config.json`) committed to the repository. This ensures:

- The same grid data is available on all devices (phone, PC, any browser)
- No backend or database required
- The grid is set up once at the start of the tournament and rarely changes

The admin edits the grid using the Tab 1 UI locally, then exports/commits the config to the repo. All other users see the same read-only grid.

### Tournament Results Data Strategy

Results are fetched using a **two-tier approach**:

1. **Primary: Live API calls from the browser.** On page load, the webpage fetches scores directly from `https://ncaa-api.henrygd.me` (the free NCAA JSON API). This provides real-time data with no server infrastructure needed. The browser calls the scoreboard endpoint for each tournament date and assembles the results client-side.

2. **Fallback: Static JSON file.** If the live API is unavailable (CORS blocked, API down, rate limited), the page falls back to `data/tournament-results.json` — a pre-fetched snapshot of results committed to the repo. This file can be updated manually or via GitHub Actions.

If CORS proves to be a persistent issue, a **GitHub Actions cron job** can be set up to auto-fetch results every 15–30 minutes on game days and commit the updated JSON.

## Web Tool

### Tab 1: Grid Setup

A 10×10 grid displaying the pool configuration:

1. **Edit axis numbers** — Set the randomly drawn number (0–9) for each position on both the X-axis (higher seed) and Y-axis (lower seed). These are editable and saveable.
2. **Enter participant names** — Click any square in the grid to enter/edit the name of the person who purchased that square.
3. **Persist data** — Grid configuration is saved to localStorage for local editing sessions. Once finalized, the grid is exported to `data/grid-config.json` and committed to the repo for cross-device access.

### Tab 2: Results Tracker

Displays live-updated game results and maps each completed game to a winning square/participant:

1. **Fetch scores** — On page load, attempt to fetch live scores from the NCAA API. Fall back to the static JSON if the API is unreachable.
2. **Determine winning square** — For each completed game (Round 1 onwards), compare seeds to identify the worse/better-ranked team, then take the last digit of each score to produce the Y/X coordinate.
3. **Show winners** — Display which participant owns the winning square for each game, along with the payout amount for that round.

### Tab 3: Leaderboard

A running tally of each participant's total winnings:

1. **Aggregate by person** — Sum up all payouts won by each participant across all completed games.
2. **Update after each game** — As new results come in, the leaderboard reflects current totals.
3. **Show breakdown** — Each person's total winnings, number of wins, and per-game detail.

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
- `startTime` — tip-off time (ET)
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
