#!/usr/bin/env python3
"""
AA8 Pirate Stream Detector, defensive version
For cybersecurity and networking classes only.

What it does:
- Takes a teacher supplied list of URLs to audit, in a CSV file.
- Fetches only HTTP headers and the first part of the HTML page.
- Looks for detection indicators, not for video to watch.
- Scores each URL and writes a JSON report and a CSV report.
- Can generate a draft alert report from a finding.

What it does NOT do:
- It does not download video segments.
- It does not play a stream.
- It does not extract a playable .m3u8 link for viewing.
- It does not bypass DRM, login, geo block, or any protection.
- It does not search the web for pirate streams to watch.
- It does not file a DMCA notice. Only a rights holder or
  authorized agent can do that. Students send a tip or alert.

Use:
    python3 pirate-stream-detector.py --input lab-urls.csv \
        --event "Saints vs Steelers" --date "2026-10-25" \
        --output report.json

Input CSV format, with a header row:
    url,expected_source,notes
    https://example.com/legal-game-page,NFL Network,teacher test page
    https://example.com/class-test-stream,AA8 Lab,our own HLS test

The teacher controls the input list. Do not add live pirate
URLs to a student handout. Use the lab list in class.
"""

import argparse
import csv
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

VERSION = "1.0.0"

# Legal broadcasters and league sites for the sports in this class.
# If the page claims to show a live NFL or NBA game and the domain
# is not in this list, that is a signal, not proof on its own.
LEGAL_DOMAINS = {
    "nfl.com", "nflnetwork.com", "cbssports.com", "paramountplus.com",
    "fox.com", "foxsports.com", "nbc.com", "peacocktv.com",
    "espn.com", "abc.com", "amazon.com", "primevideo.com",
    "nba.com", "mlb.com", "nhl.com", "youtube.com", "youtu.be",
    "tubitv.com", "pluto.tv", "therokuchannel.roku.com",
    "freevee.com", "plex.tv",
}

# Words that often appear on aggregator pages. One match alone
# means very little. Several together raise the score.
SUSPICIOUS_KEYWORDS = [
    "watch free", "free live stream", "live stream free",
    "no sign up", "no subscription", "100% free",
    "hd stream", "watch online free",
]

# Indicators in page text or headers.
HLS_PATTERN = re.compile(r"\.m3u8", re.IGNORECASE)
DASH_PATTERN = re.compile(r"\.mpd", re.IGNORECASE)
PLAYER_PATTERN = re.compile(
    r"(video-js|jwplayer|hls\.js|dash\.js|<video[^>]*>)",
    re.IGNORECASE,
)
IFRAME_PATTERN = re.compile(r"<iframe[^>]+src=", re.IGNORECASE)


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


def fetch_page(url, timeout=10, max_bytes=200000):
    """
    Fetch headers and a limited amount of HTML only.
    We never request .ts, .m4s, or other video segments.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AA8-Detector/1.0 (classroom audit, metadata only)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        headers = dict(resp.headers)
        content_type = headers.get("Content-Type", "")
        raw = resp.read(max_bytes)
    text = raw.decode("utf-8", errors="ignore")
    return status, headers, content_type, text


def score_page(url, event, status, headers, content_type, text):
    domain = domain_of(url)
    indicators = []
    score = 0

    # 1. Domain is not a known legal broadcaster.
    if domain and not is_legal_domain(domain):
        indicators.append("domain is not a known legal broadcaster or league site")
        score += 2
    else:
        indicators.append("domain matches a known legal broadcaster or league site")
        score -= 2

    # 2. Event name appears in the page.
    if event and event.lower() in text.lower():
        indicators.append("event name appears in page text")
        score += 2

    # 3. HLS or DASH manifest reference in page text.
    if HLS_PATTERN.search(text):
        indicators.append("page references an .m3u8 HLS playlist")
        score += 2
    if DASH_PATTERN.search(text):
        indicators.append("page references a .mpd DASH manifest")
        score += 1

    # 4. Embedded player or iframe.
    if PLAYER_PATTERN.search(text):
        indicators.append("page contains an embedded video player")
        score += 1
    if IFRAME_PATTERN.search(text):
        indicators.append("page contains an iframe embed")
        score += 1

    # 5. Suspicious marketing language.
    lowered = text.lower()
    for phrase in SUSPICIOUS_KEYWORDS:
        if phrase in lowered:
            indicators.append(f"page uses phrase: '{phrase}'")
            score += 1
            break

    # 6. No license or rights statement found.
    if "all rights reserved" not in lowered and "licensed" not in lowered:
        indicators.append("no clear license or rights statement found in page text")
        score += 1

    # 7. Content type is HTML, as expected for a schedule page.
    # A direct .m3u8 URL is not a normal web page, flag it for review.
    if url.lower().endswith(".m3u8") or url.lower().endswith(".mpd"):
        indicators.append("URL points directly to a manifest file, not a web page")
        score += 3

    if status != 200:
        indicators.append(f"HTTP status is {status}, not 200")
        score += 1

    # Verdict bands. These are classroom bands, not legal findings.
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


def load_input(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            rows.append({
                "url": url,
                "expected_source": (row.get("expected_source") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
            })
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="AA8 defensive pirate stream detector, metadata only."
    )
    parser.add_argument("--input", required=True, help="CSV file with urls to audit")
    parser.add_argument("--event", default="", help="Event name, e.g. Saints vs Steelers")
    parser.add_argument("--date", default="", help="Event date, e.g. 2026-10-25")
    parser.add_argument("--output", default="detector-report.json",
                        help="JSON report output file")
    parser.add_argument("--csv-output", default="detector-report.csv",
                        help="CSV report output file")
    args = parser.parse_args()

    rows = load_input(args.input)
    if not rows:
        print("No URLs found in input file.", file=sys.stderr)
        return 1

    findings = []
    for row in rows:
        url = row["url"]
        print(f"Checking: {url}")
        try:
            status, headers, content_type, text = fetch_page(url)
            finding = score_page(url, args.event, status, headers, content_type, text)
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
        finding["expected_source"] = row["expected_source"]
        finding["notes"] = row["notes"]
        findings.append(finding)
        print(f"  {finding['verdict']} (score {finding['score']})")

    report = {
        "tool": "AA8 Pirate Stream Detector",
        "version": VERSION,
        "event": args.event,
        "event_date": args.date,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Defensive classroom audit only. Scores are indicators, "
            "not a legal finding of infringement. Only a rights holder "
            "or authorized agent can file a DMCA notice."
        ),
        "findings": findings,
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    with open(args.csv_output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "url", "domain", "expected_source", "http_status",
            "score", "verdict", "indicators",
        ])
        writer.writeheader()
        for item in findings:
            writer.writerow({
                "url": item["url"],
                "domain": item["domain"],
                "expected_source": item.get("expected_source", ""),
                "http_status": item["http_status"],
                "score": item["score"],
                "verdict": item["verdict"],
                "indicators": "; ".join(item["indicators"]),
            })

    print(f"\nWrote {args.output} and {args.csv_output}")
    print("Reminder: send findings as a tip or alert to the rights holder.")
    print("Do not file a DMCA notice unless you are the owner or authorized agent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
