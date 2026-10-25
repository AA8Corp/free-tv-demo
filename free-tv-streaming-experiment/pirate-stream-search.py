#!/usr/bin/env python3
"""
AA8 Pirate Stream Search Monitor, defensive version
For cybersecurity and networking classes only.

Yes, you can recreate the discovery part of a site like
StreamEast, for defense. You cannot recreate the viewing part.

How the pirate aggregator worked, in plain words:
- It did not host video itself.
- It scanned the web for live feeds that had been illegally
  re-transmitted from official signals.
- It organized them by league, team, and kickoff time.
- It ranked them so a viewer could pick a game in two clicks.

How this monitor works, same discovery, opposite purpose:
- It builds search queries from an event name.
- It asks a search provider for pages that match that event.
- It filters out known legal broadcasters and league sites.
- It runs the detector on each candidate, headers and page
  text only, never video.
- It writes a teacher report with full evidence, and a
  student summary with domain only, no clickable watch list.
- It drafts one alert per HIGH finding, for the teacher to
  review and send to the rights holder.

What it does NOT do:
- It does not download video segments.
- It does not play a stream.
- It does not extract a playable .m3u8 link for viewing.
- It does not bypass DRM, login, geo block, or any protection.
- It does not publish a list of working pirate streams.
- It does not file a DMCA notice. Only a rights holder or
  authorized agent can do that.

Search providers, in order:
1. Bing Web Search API, if BING_API_KEY is set.
2. Google Custom Search API, if GOOGLE_API_KEY and GOOGLE_CX are set.
3. DuckDuckGo HTML, teaching fallback only. This is fragile
   and rate limited. Use an official API for real monitoring.
4. --mock, classroom test with no live search.
5. --seed-file, audit a teacher supplied CSV, same as the detector.

Use:
    # Classroom test, no live search, no pirate URLs:
    python3 pirate-stream-search.py --event "Saints vs Steelers" \
        --date "2026-10-25" --mock --output search-report.json

    # Channel mode, one channel:
    python3 pirate-stream-search.py --mode channel --channel "AMC" \
        --mock --output channel-report.json

    # Channel mode, all channels in channels.csv:
    python3 pirate-stream-search.py --mode channel \
        --channels-file channels.csv --mock --output channel-report.json

    # Audit a teacher list:
    python3 pirate-stream-search.py --event "Saints vs Steelers" \
        --date "2026-10-25" --seed-file lab-urls.csv --output search-report.json

    # Live search, teacher only, official API preferred:
    python3 pirate-stream-search.py --event "Saints vs Steelers" \
        --date "2026-10-25" --output search-report.json

Environment:
    BING_API_KEY, GOOGLE_API_KEY, GOOGLE_CX
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

VERSION = "2.1.0"

LEGAL_DOMAINS = {
    "nfl.com", "nflnetwork.com", "cbssports.com", "paramountplus.com",
    "fox.com", "foxsports.com", "nbc.com", "peacocktv.com",
    "espn.com", "abc.com", "amazon.com", "primevideo.com",
    "nba.com", "mlb.com", "nhl.com", "youtube.com", "youtu.be",
    "tubitv.com", "pluto.tv", "therokuchannel.roku.com",
    "freevee.com", "plex.tv",
    "amc.com", "amcplus.com", "bet.com", "max.com", "hbo.com",
    "cartoonnetwork.com", "adultswim.com", "disneyplus.com",
    "nickelodeon.com", "nick.com", "comedycentral.com",
    "fxnetworks.com", "tnt.com", "tbs.com", "cnn.com",
    "foodnetwork.com", "hgtv.com", "mtv.com", "vh1.com",
    "discoveryplus.com", "hulu.com", "cbs.com", "abc.com",
    "nbc.com", "fox.com", "cwtv.com", "pbs.org",
    "hallmarkplus.com", "tennischannel.com", "foxnews.com",
}

# Channel mode: channel name to legal service and legal domains.
# A page that claims to show a channel live, but is not on one
# of these domains, is a signal, not proof on its own.
CHANNEL_LEGAL = {
    "AMC": {"service": "AMC+", "domains": ["amc.com", "amcplus.com"], "url": "https://www.amcplus.com/"},
    "BET": {"service": "BET+ / Paramount+", "domains": ["bet.com", "paramountplus.com"], "url": "https://www.bet.com/"},
    "HBO": {"service": "Max", "domains": ["max.com", "hbo.com"], "url": "https://www.max.com/"},
    "Cartoon Network": {"service": "Max", "domains": ["cartoonnetwork.com", "adultswim.com", "max.com"], "url": "https://www.max.com/"},
    "Disney Channel": {"service": "Disney+", "domains": ["disneyplus.com"], "url": "https://www.disneyplus.com/"},
    "Nickelodeon": {"service": "Paramount+", "domains": ["nickelodeon.com", "nick.com", "paramountplus.com"], "url": "https://www.paramountplus.com/"},
    "Comedy Central": {"service": "Paramount+", "domains": ["comedycentral.com", "paramountplus.com"], "url": "https://www.paramountplus.com/"},
    "FX": {"service": "Hulu", "domains": ["fxnetworks.com", "hulu.com"], "url": "https://www.hulu.com/"},
    "TNT": {"service": "Max", "domains": ["tnt.com", "max.com"], "url": "https://www.max.com/"},
    "TBS": {"service": "Max", "domains": ["tbs.com", "max.com"], "url": "https://www.max.com/"},
    "ESPN": {"service": "ESPN app", "domains": ["espn.com"], "url": "https://www.espn.com/"},
    "CNN": {"service": "Max", "domains": ["cnn.com", "max.com"], "url": "https://www.max.com/"},
    "Food Network": {"service": "Max / Discovery+", "domains": ["foodnetwork.com", "max.com", "discoveryplus.com"], "url": "https://www.max.com/"},
    "HGTV": {"service": "Max / Discovery+", "domains": ["hgtv.com", "max.com", "discoveryplus.com"], "url": "https://www.max.com/"},
    "MTV": {"service": "Paramount+", "domains": ["mtv.com", "paramountplus.com"], "url": "https://www.paramountplus.com/"},
    "VH1": {"service": "Paramount+", "domains": ["vh1.com", "paramountplus.com"], "url": "https://www.paramountplus.com/"},
    "ABC": {"service": "ABC / Hulu", "domains": ["abc.com", "hulu.com"], "url": "https://abc.com/"},
    "CBS": {"service": "CBS / Paramount+", "domains": ["cbs.com", "paramountplus.com"], "url": "https://www.paramountplus.com/"},
    "NBC": {"service": "NBC / Peacock", "domains": ["nbc.com", "peacocktv.com"], "url": "https://www.peacocktv.com/"},
    "Fox": {"service": "Fox / Fox One", "domains": ["fox.com"], "url": "https://www.fox.com/"},
    "ESPN2": {"service": "ESPN app", "domains": ["espn.com"], "url": "https://www.espn.com/"},
    "FS1": {"service": "Fox One", "domains": ["fox.com"], "url": "https://www.fox.com/"},
    "NFL Network": {"service": "NFL+", "domains": ["nfl.com", "nflnetwork.com"], "url": "https://www.nfl.com/"},
    "NBA TV": {"service": "NBA League Pass", "domains": ["nba.com"], "url": "https://www.nba.com/"},
    "USA Network": {"service": "Peacock", "domains": ["peacocktv.com"], "url": "https://www.peacocktv.com/"},
    "Bravo": {"service": "Peacock", "domains": ["peacocktv.com"], "url": "https://www.peacocktv.com/"},
}

SUSPICIOUS_KEYWORDS = [
    "watch free", "free live stream", "live stream free",
    "no sign up", "no subscription", "100% free",
    "hd stream", "watch online free",
]

HLS_PATTERN = re.compile(r"\.m3u8", re.IGNORECASE)
DASH_PATTERN = re.compile(r"\.mpd", re.IGNORECASE)
PLAYER_PATTERN = re.compile(
    r"(video-js|jwplayer|hls\.js|dash\.js|<video[^>]*>)",
    re.IGNORECASE,
)
IFRAME_PATTERN = re.compile(r"<iframe[^>]+src=", re.IGNORECASE)
LINK_PATTERN = re.compile(
    r'result__a[^>]+href="([^"]+)"', re.IGNORECASE
)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def domain_of(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return ""


def is_legal_domain(domain):
    for legal in LEGAL_DOMAINS:
        if domain == legal or domain.endswith("." + legal):
            return True
    return False


def build_queries(event, league=""):
    base = event.strip()
    queries = [
        f"{base} live stream free",
        f"{base} watch online free",
        f"{base} live stream",
    ]
    if league:
        queries.append(f"{league} {base} live stream free")
    return queries


def build_channel_queries(channel):
    name = channel.strip()
    return [
        f"{name} live stream free",
        f"{name} watch online free",
        f"{name} live TV free",
        f"watch {name} live free",
    ]


def load_channels(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            channel = (row.get("channel") or "").strip()
            if not channel:
                continue
            rows.append({
                "channel": channel,
                "owner": (row.get("owner") or "").strip(),
                "legal_service": (row.get("legal_service") or "").strip(),
                "legal_url": (row.get("legal_url") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
            })
    return rows


def search_bing(query, count=10):
    key = os.environ.get("BING_API_KEY", "")
    if not key:
        return []
    url = (
        "https://api.bing.microsoft.com/v7.0/search?"
        + urllib.parse.urlencode({"q": query, "count": count})
    )
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": key})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
    results = []
    for item in data.get("webPages", {}).get("value", []):
        results.append({
            "url": item.get("url", ""),
            "title": item.get("name", ""),
            "snippet": item.get("snippet", ""),
            "provider": "bing",
        })
    return results


def search_google(query, count=10):
    key = os.environ.get("GOOGLE_API_KEY", "")
    cx = os.environ.get("GOOGLE_CX", "")
    if not key or not cx:
        return []
    url = (
        "https://www.googleapis.com/customsearch/v1?"
        + urllib.parse.urlencode({"key": key, "cx": cx, "q": query, "num": count})
    )
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    results = []
    for item in data.get("items", []):
        results.append({
            "url": item.get("link", ""),
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "provider": "google",
        })
    return results


def search_duckduckgo(query, count=10):
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        text = resp.read(200000).decode("utf-8", errors="ignore")
    results = []
    for match in LINK_PATTERN.finditer(text):
        link = urllib.parse.unquote(match.group(1))
        if link.startswith("http"):
            results.append({
                "url": link,
                "title": "",
                "snippet": "",
                "provider": "duckduckgo-html",
            })
        if len(results) >= count:
            break
    return results


def mock_results(event):
    # Classroom test only. No live URLs, no pirate domains.
    return [
        {"url": "https://www.nfl.com/", "title": "NFL official site", "snippet": "", "provider": "mock"},
        {"url": "https://example.com/", "title": "Example test page", "snippet": "", "provider": "mock"},
    ]


def mock_channel_results(channel):
    # Classroom test only. Legal URL for the channel, plus a placeholder.
    info = CHANNEL_LEGAL.get(channel, {})
    legal_url = info.get("url", "https://example.com/")
    return [
        {"url": legal_url, "title": f"{channel} official site", "snippet": "", "provider": "mock"},
        {"url": "https://example.com/", "title": "Example test page", "snippet": "", "provider": "mock"},
    ]


def search_all_queries(queries):
    seen = set()
    candidates = []
    for query in queries:
        results = []
        try:
            results = search_bing(query)
        except Exception as e:
            print(f"  Bing search failed, trying next provider: {e}")
        if not results:
            try:
                results = search_google(query)
            except Exception as e:
                print(f"  Google search failed, trying next provider: {e}")
        if not results:
            try:
                results = search_duckduckgo(query)
                time.sleep(2)
            except Exception as e:
                print(f"  DuckDuckGo search failed: {e}")
        for item in results:
            url = item.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            item["query"] = query
            candidates.append(item)
        if len(candidates) >= 20:
            break
    return candidates


def search_all(event, league, use_live=True):
    queries = build_queries(event, league)
    seen = set()
    candidates = []
    for query in queries:
        if not use_live:
            continue
        results = []
        # Try official APIs first, then the teaching fallback.
        try:
            results = search_bing(query)
        except Exception as e:
            print(f"  Bing search failed, trying next provider: {e}")
        if not results:
            try:
                results = search_google(query)
            except Exception as e:
                print(f"  Google search failed, trying next provider: {e}")
        if not results:
            try:
                results = search_duckduckgo(query)
                time.sleep(2)
            except Exception as e:
                print(f"  DuckDuckGo search failed: {e}")
        for item in results:
            url = item.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            item["query"] = query
            candidates.append(item)
        if len(candidates) >= 20:
            break
    return candidates


def fetch_page(url, timeout=10, max_bytes=200000):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AA8-Search-Monitor/2.0 (classroom audit, metadata only)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        headers = dict(resp.headers)
        content_type = headers.get("Content-Type", "")
        raw = resp.read(max_bytes)
    text = raw.decode("utf-8", errors="ignore")
    return status, headers, content_type, text


def score_page(url, event, status, content_type, text):
    domain = domain_of(url)
    indicators = []
    score = 0
    if domain and not is_legal_domain(domain):
        indicators.append("domain is not a known legal broadcaster or league site")
        score += 2
    else:
        indicators.append("domain matches a known legal broadcaster or league site")
        score -= 2
    if event and event.lower() in text.lower():
        indicators.append("event name appears in page text")
        score += 2
    if HLS_PATTERN.search(text):
        indicators.append("page references an .m3u8 HLS playlist")
        score += 2
    if DASH_PATTERN.search(text):
        indicators.append("page references a .mpd DASH manifest")
        score += 1
    if PLAYER_PATTERN.search(text):
        indicators.append("page contains an embedded video player")
        score += 1
    if IFRAME_PATTERN.search(text):
        indicators.append("page contains an iframe embed")
        score += 1
    lowered = text.lower()
    for phrase in SUSPICIOUS_KEYWORDS:
        if phrase in lowered:
            indicators.append(f"page uses phrase: '{phrase}'")
            score += 1
            break
    if "all rights reserved" not in lowered and "licensed" not in lowered:
        indicators.append("no clear license or rights statement found in page text")
        score += 1
    if url.lower().endswith(".m3u8") or url.lower().endswith(".mpd"):
        indicators.append("URL points directly to a manifest file, not a web page")
        score += 3
    if status != 200:
        indicators.append(f"HTTP status is {status}, not 200")
        score += 1
    if score >= 6:
        verdict = "HIGH - review as suspected unauthorized stream"
    elif score >= 3:
        verdict = "MEDIUM - needs teacher review"
    else:
        verdict = "LOW - no strong indicators in this check"
    return {
        "url": url,
        "domain": domain,
        "http_status": status,
        "content_type": content_type,
        "score": score,
        "verdict": verdict,
        "indicators": indicators,
        "page_text_hash": sha256_text(text[:5000]),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def load_seed(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            if url:
                rows.append({"url": url, "title": "", "snippet": "", "provider": "seed-file", "query": "seed-file"})
    return rows


def write_alert(finding, event, event_date, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    safe_domain = re.sub(r"[^A-Za-z0-9_.-]", "_", finding["domain"] or "unknown")
    path = os.path.join(out_dir, f"alert-{safe_domain}.md")
    content = f"""# Student Alert Draft, Teacher Review Required
Do not send this as a formal DMCA notice. Only a rights holder or authorized agent can file a DMCA notice. This is a tip for review.

Event: {event}
Date: {event_date}
Legal broadcaster for this game: see lecture notes, check the league schedule page

Suspected page:
- URL, exact: {finding['url']}
- Domain: {finding['domain']}
- Date and time found: {finding['checked_at_utc']}
- HTTP status: {finding['http_status']}
- Detector score: {finding['score']}
- Detector verdict: {finding['verdict']}

Indicators:
{chr(10).join('- ' + i for i in finding['indicators'])}

Evidence:
- Page text hash: {finding['page_text_hash']}
- Detector report: see search-report.json

What I did not do: I did not watch the stream, download video, or enter personal information. I checked headers and page text only.
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def main():
    parser = argparse.ArgumentParser(description="AA8 defensive pirate stream search monitor.")
    parser.add_argument("--mode", choices=["event", "channel"], default="event",
                        help="Search for a sports event, or for a TV channel")
    parser.add_argument("--event", default="", help="Event name, e.g. Saints vs Steelers")
    parser.add_argument("--channel", default="", help="Channel name, e.g. AMC, BET, HBO, Cartoon Network")
    parser.add_argument("--channels-file", default="", help="CSV file with channels to check, see channels.csv")
    parser.add_argument("--date", default="", help="Event date, e.g. 2026-10-25")
    parser.add_argument("--league", default="", help="League, e.g. NFL")
    parser.add_argument("--output", default="search-report.json", help="Teacher JSON report")
    parser.add_argument("--student-output", default="search-report-student.csv", help="Student CSV, domain only")
    parser.add_argument("--alert-dir", default="alerts", help="Folder for draft alerts")
    parser.add_argument("--mock", action="store_true", help="Classroom test, no live search")
    parser.add_argument("--seed-file", default="", help="CSV file with urls to audit, no live search")
    args = parser.parse_args()

    # Build the list of targets to check.
    # Event mode: one event. Channel mode: one channel, or all channels in a file.
    targets = []
    if args.mode == "channel":
        if args.channels_file:
            for row in load_channels(args.channels_file):
                targets.append({"label": row["channel"], "legal": CHANNEL_LEGAL.get(row["channel"], {}), "row": row})
        elif args.channel:
            targets.append({"label": args.channel, "legal": CHANNEL_LEGAL.get(args.channel, {}), "row": {}})
        else:
            print("Channel mode needs --channel or --channels-file.", file=sys.stderr)
            return 1
    else:
        if not args.event:
            print("Event mode needs --event.", file=sys.stderr)
            return 1
        targets.append({"label": args.event, "legal": {}, "row": {}})

    findings = []
    for target in targets:
        label = target["label"]
        print(f"\nTarget: {label}")
        if target["legal"]:
            print(f"  Legal service: {target['legal'].get('service', '')} at {target['legal'].get('url', '')}")

        if args.mock:
            if args.mode == "channel":
                candidates = mock_channel_results(label)
            else:
                candidates = mock_results(label)
            print("Mock mode: no live search, classroom test only.")
        elif args.seed_file:
            candidates = load_seed(args.seed_file)
            print(f"Seed mode: auditing {len(candidates)} URLs from {args.seed_file}.")
        else:
            if args.mode == "channel":
                queries = build_channel_queries(label)
                print(f"Searching for: {label} live channel")
                print("This uses official search APIs first, DuckDuckGo HTML as a teaching fallback.")
                candidates = search_all_queries(queries)
            else:
                print(f"Searching for: {label}")
                print("This uses official search APIs first, DuckDuckGo HTML as a teaching fallback.")
                candidates = search_all(label, args.league, use_live=True)
            print(f"Found {len(candidates)} candidate pages.")

        for item in candidates:
            url = item["url"]
            print(f"Checking: {domain_of(url)}")
            try:
                status, headers, content_type, text = fetch_page(url)
                finding = score_page(url, label, status, content_type, text)
            except Exception as e:
                finding = {
                    "url": url,
                    "domain": domain_of(url),
                    "http_status": None,
                    "content_type": "",
                    "score": 0,
                    "verdict": "ERROR - could not fetch page for review",
                    "indicators": [f"fetch error: {type(e).__name__}: {e}"],
                    "page_text_hash": "",
                    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            finding["target"] = label
            finding["mode"] = args.mode
            finding["legal_service"] = target["legal"].get("service", "") if target["legal"] else ""
            finding["search_title"] = item.get("title", "")
            finding["search_query"] = item.get("query", "")
            finding["search_provider"] = item.get("provider", "")
            findings.append(finding)
            print(f"  {finding['verdict']} (score {finding['score']})")
            time.sleep(1)

    report = {
        "tool": "AA8 Pirate Stream Search Monitor",
        "version": VERSION,
        "mode": args.mode,
        "event": args.event,
        "channel": args.channel,
        "channels_file": args.channels_file,
        "event_date": args.date,
        "league": args.league,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Defensive classroom audit only. Scores are indicators, "
            "not a legal finding of infringement. Full URLs are in "
            "this teacher report only. Student summary shows domain only."
        ),
        "findings": findings,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with open(args.student_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["target", "domain", "score", "verdict", "indicators"])
        writer.writeheader()
        for item in findings:
            writer.writerow({
                "target": item.get("target", ""),
                "domain": item["domain"],
                "score": item["score"],
                "verdict": item["verdict"],
                "indicators": "; ".join(item["indicators"]),
            })

    alert_paths = []
    for item in findings:
        if item["score"] >= 6:
            alert_paths.append(write_alert(item, item.get("target", args.event), args.date, args.alert_dir))

    print(f"\nWrote {args.output} and {args.student_output}")
    if alert_paths:
        print(f"Wrote {len(alert_paths)} draft alert(s) to {args.alert_dir}/ for teacher review.")
    else:
        print("No HIGH findings, no draft alerts written.")
    print("Reminder: students send a tip or alert, not a DMCA notice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
