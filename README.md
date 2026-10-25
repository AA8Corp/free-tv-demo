# AA8 Free TV Demo, phone-first, GitHub Pages

Live: https://aa8corp.github.io/free-tv-demo/

## What this is

A phone-first instructor demo for the AA8 anti-piracy lecture.
No typing in class. Tap a game, tap a channel category, tap Full screen,
cast to a monitor.

## What is on the page

- Games: today's games, auto-detected from the ESPN public scoreboard.
  Pre-run data for Monday Oct 26, 2026 is embedded: 15 games,
  NFL 1, NBA 9, WNBA 1, MLB 1, NHL 3.
  A Refresh button fetches live from ESPN in the phone browser, no server,
  no API key. ESPN allows that, Access-Control-Allow-Origin is *.
- Channels: 61 channels, tap a category chip to filter, no typing.
- Findings: pre-run mock findings for Oct 26, domain only in the student
  view, full finding in the teacher view, suspicious domains as plain text,
  never as links. No pirate video, no play button for a suspected page.
- Lab Player: plays legal and owned streams only, Mux test stream by default,
  allowlist enforced in JavaScript.

## How to run it from your phone tomorrow, Oct 26

1. Open the live URL above on your phone.
2. Full screen: tap Full screen at the top. On iPhone Safari, full screen
   for a web page is not available, so tap Share, Add to Home Screen,
   open it from the home screen, and rotate to landscape.
3. Cast: iPhone, Control Center, Screen Mirroring, pick the Apple TV or
   AirPlay monitor. Android, Quick Settings, Cast, pick the Chromecast or TV.
   Or use a USB-C to HDMI adapter.
4. In class: tap Games, tap a game card to expand it, tap Present mode
   for huge text on the monitor.
5. Refresh games: tap Refresh today's games from ESPN.

## How the data is refreshed

GitHub Action: .github/workflows/refresh-free-tv-demo.yml
Runs daily at 12:00 ET, and on demand from the GitHub mobile app:
Actions, Refresh Free TV Demo, Run workflow.
It runs today-games.py and the dashboard runner in mock mode only,
rebuilds this page, and commits the fresh data back to main.
Pages rebuilds in about 1-2 minutes.

Live search (Bing/Google) is not run in the Action, because it needs API keys.
For a live search, run pirate-stream-search.py on a lab PC.

## Files

- index.html: the demo page, self-contained, Oct 26 data embedded.
- data/today-games.json: today's games, from today-games.py.
- data/dashboard.json: mock findings for those games.
- data/channels.json: 61 channels with legal service.
- data/student-summary.csv: student view, domain only.

Source scripts live in free-tv-streaming-experiment/ in this repo:
today-games.py, instructor-dashboard-runner.py, pirate-stream-search.py,
build-github-demo.py, channels.csv.
