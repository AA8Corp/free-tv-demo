#!/usr/bin/env python3
"""
AA8 Today Games, auto-detect
For the instructor only. No typing needed in class.

What it does:
- Fetches today's games from the ESPN public scoreboard API.
  No API key needed. Source is site.api.espn.com, the same
  data ESPN shows on its own scoreboard pages.
- Leagues checked: NFL, NBA, WNBA, NCAA Football,
  NCAA Basketball, MLB, NHL.
- Writes today-games.csv in the same format as
  events-schedule.csv, so the instructor dashboard runner
  can use it directly, with no typing.
- Writes today-games.json with full details.
- Writes today-games.html with clickable game cards.
  Click a game to copy the check command, or to expand
  its legal broadcaster and kickoff time. No typing in class.

What it does NOT do:
- It does not search for pirate streams itself.
  That is the job of pirate-stream-search.py.
- It does not play video, and it does not link to a stream.
  It links only to the legal source, for example nfl.com
  or espn.com, and to the ESPN scoreboard page for the game.

Use:
    python3 today-games.py
    python3 today-games.py --date 2026-10-25
    python3 today-games.py --date 2026-10-25 --output today-games.csv

Then run the dashboard on today's games, no typing:
    python3 instructor-dashboard-runner.py --events today-games.csv --mock --force

Or run the search monitor on one game, by clicking the
command in today-games.html and pasting it in the terminal.
"""

import argparse
import csv
import html
import json
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

LEAGUES = [
    ("NFL", "football/nfl", "https://www.nfl.com/"),
    ("NBA", "basketball/nba", "https://www.nba.com/"),
    ("WNBA", "basketball/wnba", "https://www.wnba.com/"),
    ("NCAA Football", "football/college-football", "https://www.espn.com/college-football/"),
    ("NCAA Basketball", "basketball/mens-college-basketball", "https://www.espn.com/mens-college-basketball/"),
    ("MLB", "baseball/mlb", "https://www.mlb.com/"),
    ("NHL", "hockey/nhl", "https://www.nhl.com/"),
]

BROADCAST_MAP = {
    "NFL Net": "NFL Network",
    "NFL Network": "NFL Network",
    "CBS": "CBS",
    "FOX": "Fox",
    "NBC": "NBC",
    "ESPN": "ESPN",
    "ABC": "ABC",
    "Amazon": "Amazon Prime Video",
    "Prime Video": "Amazon Prime Video",
    "TNT": "TNT",
    "TBS": "TBS",
    "NBA TV": "NBA TV",
}


def fetch_league(sport_path, date_str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard?dates={date_str}"
    req = urllib.request.Request(url, headers={"User-Agent": "AA8-Today-Games/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    return data.get("events", [])


def broadcast_name(event):
    try:
        broadcasts = event["competitions"][0].get("broadcasts", [])
        if broadcasts:
            names = broadcasts[0].get("names", [])
            if names:
                return BROADCAST_MAP.get(names[0], names[0])
    except Exception:
        pass
    return ""


def esc(text):
    return html.escape(str(text or ""))


def main():
    parser = argparse.ArgumentParser(description="AA8 today games auto-detect.")
    parser.add_argument("--date", default="", help="Date YYYY-MM-DD, default today in ET")
    parser.add_argument("--output", default="today-games.csv", help="CSV output, events format")
    parser.add_argument("--json-output", default="today-games.json", help="JSON output")
    parser.add_argument("--html-output", default="today-games.html", help="HTML output with clickable cards")
    args = parser.parse_args()

    if args.date:
        date_str = args.date.replace("-", "")
        date_label = args.date
    else:
        now = datetime.now(ET)
        date_str = now.strftime("%Y%m%d")
        date_label = now.strftime("%Y-%m-%d")

    games = []
    for league_name, sport_path, legal_url in LEAGUES:
        try:
            events = fetch_league(sport_path, date_str)
        except Exception as e:
            print(f"{league_name}: fetch failed: {e}")
            continue
        print(f"{league_name}: {len(events)} games")
        for event in events:
            name = event.get("name", "")
            # ESPN name is "Team A at Team B", keep it as the event name.
            # For the search monitor, "Team A vs Team B" also works.
            iso = event.get("date", "")
            try:
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                kickoff_et = dt.astimezone(ET).strftime("%H:%M")
            except Exception:
                kickoff_et = ""
            bc = broadcast_name(event)
            games.append({
                "league": league_name,
                "event": name,
                "date": date_label,
                "kickoff_et": kickoff_et,
                "legal_broadcaster": bc or "Check league schedule",
                "legal_source_url": legal_url,
                "notes": f"Auto-detected from ESPN scoreboard for {date_label}. Broadcast listed as {bc or 'not listed'} on ESPN.",
            })

    games.sort(key=lambda g: (g["kickoff_et"], g["league"], g["event"]))

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["league", "event", "date", "kickoff_et", "legal_broadcaster", "legal_source_url", "notes"])
        writer.writeheader()
        for g in games:
            writer.writerow(g)

    with open(args.json_output, "w", encoding="utf-8") as f:
        json.dump({"date": date_label, "count": len(games), "games": games}, f, indent=2)

    cards = ""
    for g in games:
        cmd = f'python3 pirate-stream-search.py --event "{g["event"]}" --date {g["date"]} --league {g["league"]} --mock'
        cards += f"""
        <div class="card">
          <h3>{esc(g['league'])}: {esc(g['event'])}</h3>
          <p><strong>Kickoff:</strong> {esc(g['date'])} {esc(g['kickoff_et'])} ET &nbsp;|&nbsp;
          <strong>Legal:</strong> {esc(g['legal_broadcaster'])}</p>
          <p><a href="{esc(g['legal_source_url'])}">{esc(g['legal_source_url'])}</a></p>
          <button onclick="copyCommand(this)" data-cmd="{esc(cmd)}">Copy check command</button>
          <button onclick="this.parentElement.querySelector('details').open = !this.parentElement.querySelector('details').open">Show details</button>
          <details><summary>Details, no typing needed</summary>
          <p>Command to run in the terminal:<br><code>{esc(cmd)}</code></p>
          <p>{esc(g['notes'])}</p>
          </details>
          <p class="copied" style="display:none;">Copied. Paste it in the terminal to check this game.</p>
        </div>
        """

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AA8 Today Games, {esc(date_label)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.5; }}
.card {{ border: 1px solid #999; padding: 1rem; margin-bottom: 1rem; }}
button {{ padding: 0.4rem 0.8rem; margin-right: 0.5rem; }}
code {{ background: #eee; padding: 0.2rem; }}
</style>
</head>
<body>
<h1>Today Games, {esc(date_label)}</h1>
<p>{len(games)} games found on the ESPN scoreboard. Click a game to copy its check command. No typing needed in class.</p>
<p>To check all of today's games at once, run:<br><code>python3 instructor-dashboard-runner.py --events today-games.csv --mock --force</code></p>
<script>
function copyCommand(btn) {{
  var cmd = btn.getAttribute("data-cmd");
  if (navigator.clipboard) {{
    navigator.clipboard.writeText(cmd).then(function() {{
      var note = btn.parentElement.querySelector(".copied");
      if (note) note.style.display = "block";
    }});
  }} else {{
    prompt("Copy this command:", cmd);
  }}
}}
</script>
{cards if cards else "<p>No games found for this date in the leagues checked.</p>"}
</body>
</html>
"""
    with open(args.html_output, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"\nFound {len(games)} games for {date_label}.")
    print(f"Wrote {args.output}, {args.json_output}, {args.html_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
