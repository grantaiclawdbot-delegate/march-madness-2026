#!/usr/bin/env python3
"""
update_matchups.py — Fetches NCAA tournament matchup data for upcoming games and updates:
  - data/tournament-results.json
  - FALLBACK_RESULTS in index.html and index-b.html

Unlike update_scores.py (which only fetches dates up to today), this script checks
ALL tournament dates (March 21–April 7 2026) to discover new matchups once prior
rounds conclude.

For each game on the API it will:
  - ADD the game to the appropriate round if not already present in the JSON
  - UPDATE team names, seeds, startTime, network, and gameState for any game that
    has missing/TBD team info, a TBA start time, or an empty network

Scores and game state on already-complete games are never overwritten; use
update_scores.py for live score updates.

Usage: python update_matchups.py
No arguments needed. Uses only Python standard library.
"""

import json
import re
import os
import subprocess
import sys
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ============================================================
# CONFIGURATION
# ============================================================

NCAA_API = "https://ncaa-api.henrygd.me"
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(REPO_ROOT, "data", "tournament-results.json")
HTML_FILES = [
    os.path.join(REPO_ROOT, "index.html"),
    os.path.join(REPO_ROOT, "index-b.html"),
]
LOG_PATH = os.path.join(REPO_ROOT, "update_matchups.log")

# Full path to git — required when run headless from Task Scheduler
GIT_EXE = r"C:\Program Files\Git\bin\git.exe"
if not os.path.isfile(GIT_EXE):
    GIT_EXE = "git"

# All possible tournament dates to check (March 21 – April 7 2026)
# Round 1 (Mar 19–20) is already complete; matchups only change from Round 2 onward.
TOURNAMENT_DATES = [
    "2026-03-21", "2026-03-22",  # Round of 32
    "2026-03-27", "2026-03-28",  # Sweet 16
    "2026-03-29", "2026-03-30",  # Elite Eight
    "2026-04-04",                # Final Four
    "2026-04-06",                # Championship
]

# Tournament round schedule — mirrors ROUND_SCHEDULE in index.html
ROUND_SCHEDULE = [
    {"round": 1, "name": "Round of 64",  "payout": 50,   "dates": ["2026-03-19", "2026-03-20"]},
    {"round": 2, "name": "Round of 32",  "payout": 100,  "dates": ["2026-03-21", "2026-03-22"]},
    {"round": 3, "name": "Sweet 16",     "payout": 200,  "dates": ["2026-03-27", "2026-03-28"]},
    {"round": 4, "name": "Elite Eight",  "payout": 400,  "dates": ["2026-03-29", "2026-03-30"]},
    {"round": 5, "name": "Final Four",   "payout": 800,  "dates": ["2026-04-04"]},
    {"round": 6, "name": "Championship", "payout": 2000, "dates": ["2026-04-06"]},
]

# Build a date → round mapping for quick lookup
DATE_TO_ROUND = {}
for rs in ROUND_SCHEDULE:
    for d in rs["dates"]:
        DATE_TO_ROUND[d] = rs["round"]

# ============================================================
# LOGGING
# ============================================================

_log_file = None

def _open_log():
    global _log_file
    _log_file = open(LOG_PATH, "a", encoding="utf-8", buffering=1)

def log(msg=""):
    """Print to stdout and append to log file with flush."""
    print(msg, flush=True)
    if _log_file:
        _log_file.write(msg + "\n")
        _log_file.flush()

# ============================================================
# HELPERS
# ============================================================

def et_to_ct(time_str):
    """Convert ET time string to CT (1 hour behind). Mirrors JS etToCt()."""
    if not time_str or not isinstance(time_str, str):
        return time_str
    if re.search(r"CT$", time_str, re.IGNORECASE):
        return time_str  # Already converted
    m = re.match(r"^(\d+):(\d+)\s*(AM|PM)(?:\s*E[SD]?T)?$", time_str, re.IGNORECASE)
    if not m:
        return time_str
    hours = int(m.group(1))
    minutes = m.group(2)
    period = m.group(3).upper()
    # Convert to 24-hour
    if period == "PM" and hours != 12:
        hours += 12
    if period == "AM" and hours == 12:
        hours = 0
    # Subtract 1 hour (ET → CT)
    hours -= 1
    # Back to 12-hour
    new_period = "PM" if hours >= 12 else "AM"
    if hours > 12:
        hours -= 12
    if hours == 0:
        hours = 12
    return f"{hours}:{minutes} {new_period} CT"


def fetch_scoreboard(date_str):
    """Fetch scoreboard JSON from NCAA API for date string YYYY-MM-DD.
    Returns parsed JSON dict or None on error."""
    y, m, d = date_str.split("-")
    url = f"{NCAA_API}/scoreboard/basketball-men/d1/{y}/{m}/{d}"
    log(f"  Fetching {url} ...")
    req = Request(url, headers={"User-Agent": "update_matchups.py/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            log(f"    -> OK")
            return data
    except HTTPError as e:
        log(f"    -> HTTP {e.code}")
        return None
    except URLError as e:
        log(f"    -> Error: {e.reason}")
        return None
    except Exception as e:
        log(f"    -> Error: {e}")
        return None


def parse_api_games(api_data, date_str):
    """Parse NCAA API response into our internal game format.
    Actual API format: { games: [{ game: { away: {...}, home: {...}, ... } }] }
    Returns list of game dicts."""
    if not api_data:
        return []
    raw = api_data.get("games", [])
    games = []
    for entry in raw:
        try:
            game_obj = entry.get("game")
            if not game_obj:
                continue

            away = game_obj.get("away")
            home = game_obj.get("home")
            if not away or not home:
                continue

            # Only include tournament games — both teams must have seeds
            away_seed = away.get("seed")
            home_seed = home.get("seed")
            if not away_seed and not home_seed:
                continue

            def get_name(t):
                names = t.get("names") or {}
                return (names.get("short")
                        or names.get("char6")
                        or t.get("teamName")
                        or t.get("name")
                        or "??")

            def get_score(t):
                s = t.get("score")
                if s is None or s == "":
                    return None
                try:
                    return int(s)
                except (ValueError, TypeError):
                    return None

            state = (game_obj.get("gameState") or "pre").lower().strip()
            game_state = "final" if "final" in state else state

            games.append({
                "gameID": str(game_obj.get("gameID", "")),
                "date": date_str,
                "startTime": et_to_ct(game_obj.get("startTime") or ""),
                "network": game_obj.get("network") or "",
                "gameState": game_state,
                "away": {
                    "team": get_name(away),
                    "seed": int(away_seed or 0),
                    "score": get_score(away),
                },
                "home": {
                    "team": get_name(home),
                    "seed": int(home_seed or 0),
                    "score": get_score(home),
                },
            })
        except Exception as e:
            log(f"    Warning: skipping entry due to error: {e}")
            continue
    return games


def is_tbd_team(team_name):
    """Return True if a team name looks like a TBD placeholder."""
    if not team_name:
        return True
    return team_name.strip().upper() in ("TBD", "??", "", "TBA")


def game_needs_matchup(game):
    """Return True if this game is missing team/time/network data that the API might supply."""
    away = game.get("away", {})
    home = game.get("home", {})
    if is_tbd_team(away.get("team", "")) or is_tbd_team(home.get("team", "")):
        return True
    if not away.get("seed") or not home.get("seed"):
        return True
    if not game.get("startTime") or game.get("startTime", "").upper() in ("TBA", "TBD", ""):
        return True
    if not game.get("network"):
        return True
    return False


def apply_matchup(existing_game, api_game):
    """
    Update an existing game entry with matchup data from the API.
    Only fills in missing/TBD fields; never overwrites existing score data.
    Returns (updated_game, changed: bool).
    """
    updated = dict(existing_game)
    changed = False

    away = dict(existing_game.get("away", {}))
    home = dict(existing_game.get("home", {}))

    # Update team/seed only if TBD
    if is_tbd_team(away.get("team", "")) or not away.get("seed"):
        new_away_team = api_game["away"]["team"]
        new_away_seed = api_game["away"]["seed"]
        if away.get("team") != new_away_team or away.get("seed") != new_away_seed:
            away["team"] = new_away_team
            away["seed"] = new_away_seed
            changed = True

    if is_tbd_team(home.get("team", "")) or not home.get("seed"):
        new_home_team = api_game["home"]["team"]
        new_home_seed = api_game["home"]["seed"]
        if home.get("team") != new_home_team or home.get("seed") != new_home_seed:
            home["team"] = new_home_team
            home["seed"] = new_home_seed
            changed = True

    # Update startTime if missing or TBA
    existing_time = (existing_game.get("startTime") or "").upper()
    if not existing_time or existing_time in ("TBA", "TBD"):
        new_time = api_game.get("startTime", "")
        if new_time and new_time.upper() not in ("TBA", "TBD"):
            updated["startTime"] = new_time
            changed = True

    # Update network if missing
    if not existing_game.get("network"):
        new_network = api_game.get("network", "")
        if new_network:
            updated["network"] = new_network
            changed = True

    # Update gameState if existing is "pre" and API has something different
    if existing_game.get("gameState") == "pre":
        new_state = api_game.get("gameState", "pre")
        if new_state != "pre":
            updated["gameState"] = new_state
            changed = True

    updated["away"] = away
    updated["home"] = home
    return updated, changed


def canonical(obj):
    """Return a canonical JSON string for comparison (sorted keys, no spaces)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def run_git(args):
    """Run a git command in REPO_ROOT. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        [GIT_EXE] + args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ============================================================
# MAIN
# ============================================================

def main():
    _open_log()
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log(f"\n{'='*60}")
    log(f"=== update_matchups.py  started {run_ts} ===")
    log(f"{'='*60}")
    log(f"REPO_ROOT : {REPO_ROOT}")
    log(f"GIT_EXE   : {GIT_EXE}  (exists={os.path.isfile(GIT_EXE) if GIT_EXE != 'git' else 'N/A-using-PATH'})")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log(f"Today (UTC): {today}")
    log()

    # Remove stale HEAD.lock if present
    lock_path = os.path.join(REPO_ROOT, ".git", "HEAD.lock")
    if os.path.exists(lock_path):
        log(f"WARNING: stale HEAD.lock found — removing {lock_path}")
        try:
            os.remove(lock_path)
            log("  HEAD.lock removed OK")
        except Exception as e:
            log(f"  Could not remove HEAD.lock: {e}")

    # ── Step 1: Load existing data ──────────────────────────
    log(f"Reading {JSON_PATH} ...")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        existing = json.load(f)

    # ── Step 2: Fetch API data for all tournament dates ─────
    # Fetch all dates regardless of whether they're in the past or future
    log(f"Fetching API data for tournament dates: {TOURNAMENT_DATES}\n")

    api_by_date = {}     # date  → [game, ...]
    api_by_game_id = {}  # gameID → game

    for date_str in TOURNAMENT_DATES:
        raw = fetch_scoreboard(date_str)
        games = parse_api_games(raw, date_str)
        log(f"  -> {len(games)} tournament game(s) for {date_str}")
        api_by_date[date_str] = games
        for g in games:
            if g["gameID"]:
                api_by_game_id[g["gameID"]] = g

    log()

    # ── Step 3: Merge matchup data into existing structure ───
    existing_rounds = {r["round"]: r for r in existing["rounds"]}
    changes = 0
    new_rounds = []

    for rs in ROUND_SCHEDULE:
        rnum = rs["round"]
        ex_round = existing_rounds.get(rnum, {
            "round": rnum, "name": rs["name"], "payout": rs["payout"], "games": []
        })

        games = list(ex_round.get("games", []))
        game_id_set = {g["gameID"] for g in games if g.get("gameID")}

        # 3a. Update existing games that need matchup data
        for i, game in enumerate(games):
            gid = game.get("gameID", "")
            if not gid or gid not in api_by_game_id:
                continue
            api_game = api_by_game_id[gid]
            if game_needs_matchup(game):
                updated, changed = apply_matchup(game, api_game)
                if changed:
                    a_old = game.get("away", {}).get("team", "?")
                    h_old = game.get("home", {}).get("team", "?")
                    a_new = updated.get("away", {}).get("team", "?")
                    h_new = updated.get("home", {}).get("team", "?")
                    t_new = updated.get("startTime", "")
                    n_new = updated.get("network", "")
                    log(f"  [R{rnum}] Updated game {gid}: {a_old}/{h_old} -> {a_new} vs {h_new}  {t_new}  {n_new}")
                    games[i] = updated
                    changes += 1

        # 3b. Add new games from API that don't exist in this round yet
        for date_str in rs["dates"]:
            for api_game in api_by_date.get(date_str, []):
                gid = api_game["gameID"]
                if not gid or gid in game_id_set:
                    continue
                # Only add if the game has valid team data
                a = api_game["away"]["team"]
                h = api_game["home"]["team"]
                a_seed = api_game["away"]["seed"]
                h_seed = api_game["home"]["seed"]
                if is_tbd_team(a) or is_tbd_team(h) or not a_seed or not h_seed:
                    log(f"  [R{rnum}] Skipping game {gid} on {date_str} — teams not yet determined")
                    continue
                log(f"  [R{rnum}] NEW game {gid}: {a} (#{a_seed}) vs {h} (#{h_seed}) on {date_str}")
                games.append(api_game)
                game_id_set.add(gid)
                changes += 1

        new_rounds.append({
            "round": ex_round["round"],
            "name":  ex_round["name"],
            "payout": ex_round["payout"],
            "games": games,
        })

    if changes == 0:
        log("No matchup changes detected from API.")
    else:
        log(f"\n{changes} change(s) detected.")

    # ── Step 4: Check whether data actually changed ──────────
    existing_rounds_data = existing.get("rounds", [])
    if canonical(existing_rounds_data) == canonical(new_rounds):
        log("\nData unchanged -- nothing to commit.")
        log(f"=== Finished {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} ===")
        return

    # ── Step 5: Write data/tournament-results.json ───────────
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    updated = {"lastUpdated": now_utc, "rounds": new_rounds}

    log(f"\nWriting {JSON_PATH} ...")
    with open(JSON_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(updated, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # ── Step 6: Update FALLBACK_RESULTS in both HTML files ───
    compact_json = json.dumps(updated, separators=(",", ":"), ensure_ascii=False)
    new_line = f"const FALLBACK_RESULTS = {compact_json};"

    for html_path in HTML_FILES:
        name = os.path.basename(html_path)
        log(f"Updating {name} ...")
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        new_content, n = re.subn(
            r"^const FALLBACK_RESULTS = .*?;$",
            new_line,
            content,
            flags=re.MULTILINE,
        )
        if n == 0:
            log(f"  WARNING: FALLBACK_RESULTS line not found in {name}")
        else:
            log(f"  -> Replaced ({n} occurrence(s))")
        with open(html_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)

    # ── Step 7: Git add / commit / push ─────────────────────
    log("\nRunning git operations ...")

    rc, status_out, status_err = run_git(["status", "--porcelain"])
    log(f"git status rc={rc}")
    if status_err:
        log(f"  stderr: {status_err}")
    if not status_out:
        log("Git: nothing to commit (files may not have changed on disk).")
        log(f"=== Finished {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} ===")
        return

    log(f"Changed files:\n{status_out}")

    rel_json = os.path.relpath(JSON_PATH, REPO_ROOT).replace("\\", "/")
    for path in [rel_json] + [os.path.relpath(p, REPO_ROOT).replace("\\", "/") for p in HTML_FILES]:
        rc_add, out_add, err_add = run_git(["add", path])
        if rc_add != 0:
            log(f"  git add {path} failed (rc={rc_add}): {err_add}")

    commit_msg = f"Update tournament matchups — {now_utc[:16].replace('T', ' ')} UTC"
    rc, out, err = run_git(["commit", "-m", commit_msg])
    log(f"git commit rc={rc}")
    if out:
        log(f"  stdout: {out}")
    if err:
        log(f"  stderr: {err}")
    if rc != 0:
        log(f"ERROR: Git commit failed")
        sys.exit(1)
    log(f"Committed: {commit_msg}")

    rc, out, err = run_git(["push", "origin", "master"])
    log(f"git push rc={rc}")
    if out:
        log(f"  stdout: {out}")
    if err:
        log(f"  stderr: {err}")
    if rc != 0:
        log(f"ERROR: Git push failed — see stderr above")
        sys.exit(1)
    log("Pushed to origin/master.")
    log(f"\nDone! {changes} matchup update(s) committed and pushed.")
    log(f"=== Finished {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} ===")


if __name__ == "__main__":
    main()
