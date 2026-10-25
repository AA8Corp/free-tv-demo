#!/usr/bin/env python3
"""
AA8 Instructor Dashboard Runner
For the teacher only. Not for students to watch streams.

What it is:
An answer key and monitoring dashboard for the anti-piracy lecture.

It runs 10 minutes before kickoff, for every league in
events-schedule.csv: NFL, NBA, WNBA, NCAA Football, NCAA Basketball.
For each game starting soon, it runs the search monitor,
scores candidate pages, and builds an instructor dashboard.

What the instructor can view:
- The event, league, kickoff time, and legal broadcaster.
- How many HIGH and MEDIUM findings the monitor found.
- The domain, score, verdict, and indicators for each finding.
- The draft alert for each HIGH finding, for teacher review.
- The legal source link, so the class can compare legal vs suspicious.
- The Lab Player at the top of the dashboard. It plays only
  legal and owned streams: the Mux test stream by default,
  the Apple test stream, or the teacher's own OBS HLS stream
  from the lab network. It has play, pause, volume, and a
  status line that shows the manifest URL, the level, and
  any load error. It does not auto-load any finding.

What the instructor cannot view here, on purpose:
- No embedded pirate stream, no play button for a suspected page.
- No clickable link to a suspected pirate page.
- Suspicious domains are shown as plain text, not as links.
- No video download, no playback of unauthorized content,
  no DRM bypass.

The player uses an allowlist in JavaScript. It will only load
an .m3u8 URL if the domain is localhost, a lab private IP,
test-streams.mux.dev, devstreaming-cdn.apple.com, or a known
legal broadcaster domain. Any other domain is blocked with a
message, and the player does not load it. Findings are never
wired to the player, the teacher must paste a URL they own
or a legal test stream.

Why: viewing the pirate video is not needed to verify it.
Title match, live window, manifest reference, and domain
pattern are enough evidence for a report, and clicking play
exposes the teacher to malware, popups, and tracking.
The dashboard is the answer key, the report is the evidence,
and the player is for teaching HLS with legal content.

How it runs, 10 minutes before kickoff:
- The runner checks events-schedule.csv every run.
- An event is due if now is between kickoff minus 15 minutes
  and kickoff plus 30 minutes. That gives a 10 minute
  pre-kickoff check, with a little slack for a late start.
- Run it from cron every 5 minutes on the lab PC, or run it
  by hand before class.
- Example cron, lab PC, America/New_York, every 5 minutes:
    */5 * * * * cd /home/teacher/free-tv-streaming-experiment && /usr/bin/python3 instructor-dashboard-runner.py --mock >> dashboard.log 2>&1
  Remove --mock for live search, and set BING_API_KEY or
  GOOGLE_API_KEY and GOOGLE_CX for an official search API.
  See pirate-stream-search.py for the provider order.

Modes:
    --mock        Classroom test, no live search.
    --force       Run all events in the file, even if not due yet.
                  Use this for a demo, or to build a sample dashboard.
    --seed-file   Audit a teacher CSV list instead of live search.

Use:
    python3 instructor-dashboard-runner.py --mock --force
    python3 instructor-dashboard-runner.py --force --seed-file lab-urls.csv

Outputs, in the same folder:
    instructor-dashboard.html   Teacher dashboard, open in a browser.
    instructor-answer-key.json  Full data, teacher only.
    instructor-student-summary.csv  Domain only, for students.
    alerts/  Draft alerts, one per HIGH finding, teacher review only.
"""

# =============================================================================
# IMPORTS AND GLOBAL CONSTANTS
# =============================================================================
import argparse
import csv
import html
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

VERSION = "1.1.0"
ET = ZoneInfo("America/New_York")

# Legal broadcaster lists used for reference in the dashboard
LEAGUE_LEGAL = {
    "NFL": ["NFL Network", "CBS", "Fox", "NBC", "ESPN", "ABC", "Amazon Prime Video"],
    "NBA": ["ESPN", "ABC", "TNT", "NBA TV", "NBA League Pass"],
    "WNBA": ["ESPN", "ABC", "CBS Sports Network", "NBA TV", "Ion"],
    "NCAA Football": ["ESPN", "ABC", "Fox", "CBS", "NBC", "SEC Network", "Big Ten Network"],
    "NCAA Basketball": ["ESPN", "ABC", "CBS", "Fox", "TNT", "Big Ten Network"],
}


# =============================================================================
# MODULE LOADER
# =============================================================================
def load_search_module():
    """Dynamically load the pirate-stream-search.py helper module."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "pirate-stream-search.py")
    spec = importlib.util.spec_from_file_location("pirate_stream_search", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# =============================================================================
# EVENT LOADING AND TIME LOGIC
# =============================================================================
def load_events(path):
    """Load events from the CSV schedule file."""
    events = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append({
                "league": (row.get("league") or "").strip(),
                "event": (row.get("event") or "").strip(),
                "date": (row.get("date") or "").strip(),
                "kickoff_et": (row.get("kickoff_et") or "").strip(),
                "legal_broadcaster": (row.get("legal_broadcaster") or "").strip(),
                "legal_source_url": (row.get("legal_source_url") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
            })
    return events


def kickoff_datetime(event):
    """Convert event date + kickoff_et into a timezone-aware datetime."""
    date_str = event["date"]
    time_str = event["kickoff_et"]
    naive = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=ET)


def is_due(event, now_et, force=False):
    """
    Return True if the event should be checked now.
    Window: kickoff - 15 minutes through kickoff + 30 minutes.
    """
    if force:
        return True
    try:
        kickoff = kickoff_datetime(event)
    except Exception:
        return False
    return (kickoff - timedelta(minutes=15)) <= now_et <= (kickoff + timedelta(minutes=30))


# =============================================================================
# HTML HELPERS
# =============================================================================
def esc(text):
    """HTML-escape a string for safe insertion into the dashboard."""
    return html.escape(str(text or ""))


# =============================================================================
# DASHBOARD HTML GENERATOR
# (Contains the Lab Player with the JavaScript allow-list)
# =============================================================================
def build_dashboard(answer_key, output_path):
    """
    Build the full instructor-dashboard.html file.
    Includes:
      - Event sections with findings (domains as plain text only)
      - Lab Player that is restricted to legal / lab streams only
    """
    now_str = datetime.now(ET).strftime("%Y-%m-%d %I:%M %p ET")
    rows_html = ""
    for item in answer_key["events"]:
        event = item["event"]
        findings = item["findings"]
        high = sum(1 for f in findings if f["score"] >= 6)
        medium = sum(1 for f in findings if 3 <= f["score"] < 6)
        low = sum(1 for f in findings if f["score"] < 3)
        status = item["status"]
        legal_list = ", ".join(LEAGUE_LEGAL.get(event["league"], [event["legal_broadcaster"]]))
        findings_html = ""
        if not findings:
            findings_html = "<p>No candidates checked in this run.</p>"
        else:
            findings_html = "<table><tr><th>Domain</th><th>Score</th><th>Verdict</th><th>Indicators</th></tr>"
            for f in findings:
                # Domain as plain text, never as a link. No video, no play button.
                findings_html += (
                    f"<tr><td>{esc(f['domain'])}</td>"
                    f"<td>{f['score']}</td>"
                    f"<td>{esc(f['verdict'])}</td>"
                    f"<td>{esc('; '.join(f['indicators']))}</td></tr>"
                )
            findings_html += "</table>"
        rows_html += f"""
        <details open>
          <summary><strong>{esc(event['league'])}: {esc(event['event'])}</strong> &nbsp; {esc(event['date'])} {esc(event['kickoff_et'])} ET &nbsp; Click to expand or collapse</summary>
          <p><strong>Kickoff:</strong> {esc(event['date'])} {esc(event['kickoff_et'])} ET &nbsp;|&nbsp;
          <strong>Legal broadcaster:</strong> {esc(event['legal_broadcaster'])} &nbsp;|&nbsp;
          <strong>Status:</strong> {esc(status)}</p>
          <p><strong>Legal options for this league:</strong> {esc(legal_list)}</p>
          <p><strong>Legal source:</strong> <a href="{esc(event['legal_source_url'])}">{esc(event['legal_source_url'])}</a></p>
          <p><strong>Findings:</strong> {high} HIGH, {medium} MEDIUM, {low} LOW. Draft alerts: {item['alert_count']}</p>
          {findings_html}
          <p><em>Notes:</em> {esc(event['notes'])}</p>
        </details>
        <hr>
        """

    # Build picker buttons in plain Python, to avoid nested quote issues in the f-string below.
    picker_parts = []
    for item in answer_key["events"]:
        ev = item["event"]
        label = esc(ev["league"]) + ": " + esc(ev["event"])
        name = esc(ev["event"]).replace("'", "")
        league = esc(ev["league"]).replace("'", "")
        date = esc(ev["date"]).replace("'", "")
        picker_parts.append('<button onclick="pickGame(\'' + name + '\', \'' + league + '\', \'' + date + '\')">' + label + '</button> ')
    picker_buttons = "".join(picker_parts)

    # -------------------------------------------------------------------------
    # Full HTML document (includes Lab Player + allow-list JavaScript)
    # -------------------------------------------------------------------------
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AA8 Instructor Dashboard, Anti-Piracy Answer Key</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js"></script>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.5; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #999; padding: 0.5rem; text-align: left; vertical-align: top; }}
th {{ background: #eee; }}
section {{ margin-bottom: 1rem; }}
.player-box {{ border: 2px solid #333; padding: 1rem; margin-bottom: 1rem; background: #f7f7f7; }}
.player-box input {{ width: 70%; padding: 0.4rem; }}
.player-box button {{ padding: 0.4rem 0.8rem; margin-left: 0.3rem; }}
#playerStatus {{ font-weight: bold; }}
</style>
</head>
<body>
<h1>AA8 Instructor Dashboard, Anti-Piracy Answer Key</h1>
<p>Generated: {esc(now_str)} &nbsp;|&nbsp; Tool version: {esc(answer_key['version'])}</p>
<p><strong>Teacher only.</strong> This dashboard shows detection results, plus a Lab Player for legal and owned streams only. Suspicious domains are plain text, never links. Full URLs are in the teacher JSON report only, for takedown evidence.</p>

<!-- =====================================================================
     LAB PLAYER SECTION
     Plays only legal / owned streams. Findings are never auto-loaded.
     ===================================================================== -->
<section class="player-box">
<h2>Lab Player, legal and owned streams only</h2>
<p>Use this to teach HLS in class. Default is the Mux legal test stream. Paste your own OBS HLS URL from the lab network to play your own stream. The player will block any other domain.</p>
<video id="labPlayer" controls width="100%" playsinline></video>
<p>
<label for="hlsUrl">HLS URL (.m3u8):</label><br>
<input id="hlsUrl" type="text" value="https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8">
<button onclick="loadLabStream()">Load stream</button>
<button onclick="loadTestStream()">Load Mux test stream</button>
<button onclick="stopLabStream()">Stop</button>
</p>
<p id="playerStatus">Status: ready. No stream loaded yet.</p>
<p><em>Allowlist:</em> localhost, 127.0.0.1, 192.168.*, 10.*, test-streams.mux.dev, devstreaming-cdn.apple.com, and known legal broadcaster domains. Findings are never wired to this player.</p>
</section>

<script>
/* =========================================================================
   LAB PLAYER ALLOW-LIST AND CONTROL FUNCTIONS
   Only domains in ALLOWED (plus private lab ranges) may be loaded.
   ========================================================================= */
var ALLOWED = ["localhost", "127.0.0.1", "test-streams.mux.dev", "devstreaming-cdn.apple.com", "nfl.com", "nflnetwork.com", "cbssports.com", "paramountplus.com", "fox.com", "foxsports.com", "nbc.com", "peacocktv.com", "espn.com", "abc.com", "amazon.com", "primevideo.com", "nba.com", "mlb.com", "nhl.com", "youtube.com", "youtu.be", "tubitv.com", "pluto.tv", "freevee.com", "plex.tv"];

function isAllowed(url) {{
  try {{
    var host = new URL(url).hostname.toLowerCase();
    if (host === "localhost" || host === "127.0.0.1") return true;
    if (host.startsWith("192.168.") || host.startsWith("10.")) return true;
    for (var i = 0; i < ALLOWED.length; i++) {{
      if (host === ALLOWED[i] || host.endsWith("." + ALLOWED[i])) return true;
    }}
    return false;
  }} catch (e) {{ return false; }}
}}

var hls = null;

function setStatus(msg) {{
  document.getElementById("playerStatus").textContent = "Status: " + msg;
}}

function loadLabStream() {{
  var url = document.getElementById("hlsUrl").value.trim();
  var video = document.getElementById("labPlayer");
  if (!url.endsWith(".m3u8")) {{
    setStatus("Blocked. URL must end in .m3u8.");
    return;
  }}
  if (!isAllowed(url)) {{
    setStatus("Blocked. That domain is not on the legal and lab allowlist. Use the detector report for evidence, do not play it here.");
    return;
  }}
  if (hls) {{
    hls.destroy();
    hls = null;
  }}
  if (window.Hls && Hls.isSupported()) {{
    hls = new Hls();
    hls.loadSource(url);
    hls.attachMedia(video);
    hls.on(Hls.Events.MANIFEST_PARSED, function() {{
      setStatus("Playing allowed stream: " + url);
      video.play();
    }});
    hls.on(Hls.Events.ERROR, function(event, data) {{
      setStatus("Player error: " + data.type + " " + data.details);
    }});
  }} else if (video.canPlayType("application/vnd.apple.mpegurl")) {{
    video.src = url;
    video.addEventListener("loadedmetadata", function() {{
      setStatus("Playing allowed stream: " + url);
      video.play();
    }});
  }} else {{
    setStatus("This browser cannot play HLS. Use Safari, or a browser with HLS.js support.");
  }}
}}

function loadTestStream() {{
  document.getElementById("hlsUrl").value = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8";
  loadLabStream();
}}

function stopLabStream() {{
  var video = document.getElementById("labPlayer");
  if (hls) {{
    hls.destroy();
    hls = null;
  }}
  video.pause();
  video.removeAttribute("src");
  video.load();
  setStatus("Stopped.");
}}
</script>

<p><strong>How to use it in class:</strong> open this file before kickoff, check the HIGH count for the game, compare the legal broadcaster to the findings, and review the draft alerts in the alerts folder. Students see the student summary CSV, domain only.</p>

<!-- =====================================================================
     CLICKABLE GAME PICKER
     No typing in class. Click a game, the command fills in below.
     ===================================================================== -->
<section class="player-box">
<h2>Pick a game, no typing needed</h2>
<p>Click a game below. The check command fills in automatically. Copy it and paste it in the terminal, or just click the game card below to expand its findings.</p>
<p>
<label for="pickedGame">Picked game:</label><br>
<input id="pickedGame" type="text" value="" placeholder="Click a game below" style="width:70%;">
</p>
<p id="pickedCommand">Command: click a game below.</p>
<p id="pickerButtons">
{picker_buttons}
</p>
</section>
<script>
function pickGame(name, league, date) {{
  document.getElementById("pickedGame").value = name;
  var cmd = 'python3 pirate-stream-search.py --event "' + name + '" --date ' + date + ' --league ' + league + ' --mock';
  document.getElementById("pickedCommand").textContent = "Command: " + cmd;
  if (navigator.clipboard) {{ navigator.clipboard.writeText(cmd); }}
}}
</script>
{rows_html}
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return output_path


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="AA8 instructor dashboard runner.")
    parser.add_argument("--events", default="events-schedule.csv", help="Events CSV file")
    parser.add_argument("--mock", action="store_true", help="Classroom test, no live search")
    parser.add_argument("--force", action="store_true", help="Run all events, even if not due")
    parser.add_argument("--seed-file", default="", help="CSV file with urls to audit, no live search")
    parser.add_argument("--output", default="instructor-dashboard.html", help="Dashboard HTML output")
    parser.add_argument("--answer-key", default="instructor-answer-key.json", help="Answer key JSON output")
    parser.add_argument("--student-output", default="instructor-student-summary.csv", help="Student CSV, domain only")
    parser.add_argument("--alert-dir", default="alerts", help="Folder for draft alerts")
    args = parser.parse_args()

    mod = load_search_module()
    events = load_events(args.events)
    now_et = datetime.now(ET)
    print(f"Now: {now_et.strftime('%Y-%m-%d %I:%M %p ET')}")
    print(f"Loaded {len(events)} events from {args.events}.")

    answer_events = []
    all_findings = []

    # -------------------------------------------------------------------------
    # Process each event
    # -------------------------------------------------------------------------
    for event in events:
        due = is_due(event, now_et, force=args.force)
        if not due:
            kickoff = kickoff_datetime(event)
            print(f"Skipping, not due yet: {event['league']} {event['event']} at {kickoff.strftime('%I:%M %p ET')}")
            answer_events.append({
                "event": event,
                "status": "not due yet, runs 10 minutes before kickoff",
                "findings": [],
                "alert_count": 0,
            })
            continue

        print(f"\nChecking: {event['league']} {event['event']} at {event['kickoff_et']} ET, legal: {event['legal_broadcaster']}")

        if args.mock:
            candidates = mod.mock_results(event["event"])
        elif args.seed_file:
            candidates = mod.load_seed(args.seed_file)
        else:
            candidates = mod.search_all(event["event"], event["league"], use_live=True)

        findings = []
        for item in candidates:
            url = item["url"]
            print(f"  Checking domain: {mod.domain_of(url)}")
            try:
                status, headers, content_type, text = mod.fetch_page(url)
                finding = mod.score_page(url, event["event"], status, content_type, text)
            except Exception as e:
                finding = {
                    "url": url,
                    "domain": mod.domain_of(url),
                    "http_status": None,
                    "content_type": "",
                    "score": 0,
                    "verdict": "ERROR - could not fetch page for review",
                    "indicators": [f"fetch error: {type(e).__name__}: {e}"],
                    "page_text_hash": "",
                    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            finding["league"] = event["league"]
            finding["event"] = event["event"]
            finding["search_query"] = item.get("query", "")
            finding["search_provider"] = item.get("provider", "")
            findings.append(finding)
            all_findings.append(finding)

        alert_count = 0
        for finding in findings:
            if finding["score"] >= 6:
                path = mod.write_alert(finding, event["event"], event["date"], args.alert_dir)
                alert_count += 1
                print(f"  Draft alert written: {path}")

        answer_events.append({
            "event": event,
            "status": "checked",
            "findings": findings,
            "alert_count": alert_count,
        })

    # -------------------------------------------------------------------------
    # Build answer-key JSON
    # -------------------------------------------------------------------------
    answer_key = {
        "tool": "AA8 Instructor Dashboard Runner",
        "version": VERSION,
        "generated_at_et": now_et.isoformat(),
        "leagues": ["NFL", "NBA", "WNBA", "NCAA Football", "NCAA Basketball"],
        "note": (
            "Teacher only answer key. Scores are indicators, not a legal "
            "finding of infringement. Lab Player in the dashboard plays "
            "legal and owned HLS streams only, with an allowlist. No links "
            "to suspected pirate pages in the dashboard. Full URLs are in "
            "this JSON only, for takedown evidence."
        ),
        "events": answer_events,
    }

    with open(args.answer_key, "w", encoding="utf-8") as f:
        json.dump(answer_key, f, indent=2)

    # -------------------------------------------------------------------------
    # Build student-facing CSV (domain only)
    # -------------------------------------------------------------------------
    with open(args.student_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["league", "event", "domain", "score", "verdict", "indicators"])
        writer.writeheader()
        for item in all_findings:
            writer.writerow({
                "league": item.get("league", ""),
                "event": item.get("event", ""),
                "domain": item["domain"],
                "score": item["score"],
                "verdict": item["verdict"],
                "indicators": "; ".join(item["indicators"]),
            })

    # -------------------------------------------------------------------------
    # Generate the HTML dashboard
    # -------------------------------------------------------------------------
    build_dashboard(answer_key, args.output)
    print(f"\nWrote {args.output}, {args.answer_key}, and {args.student_output}")
    print("Open the HTML file in a browser to view the instructor dashboard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
