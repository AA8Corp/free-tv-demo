# Phone + Cast Runbook, AA8 Free TV Demo
## Lecture: Monday Oct 26, 2026

Demo page (once the repo is live):
https://aa8corp.github.io/free-tv-demo/

Local copy, if GitHub is not live yet:
~/workspace/free-tv-demo-repo/index.html
Open it in a phone browser via a local file share, or serve it:
python3 -m http.server 8902, then open http://<computer-ip>:8902/

## Before class, 10 minutes

1. Charge the phone. Bring a charger and a USB-C to HDMI adapter as backup.
2. Connect the phone and the monitor to the same Wi-Fi, if casting wirelessly.
   If the venue Wi-Fi is weak, use the HDMI adapter instead, it does not need Wi-Fi for the screen, but the live ESPN refresh does.
3. Open the demo page on the phone. Check that the 15 games for Oct 26 load.
   Headline game: NFL, Dallas Cowboys at Philadelphia Eagles, 8:15 PM ET, ESPN.
   Other games that day: NBA 9, WNBA 1, MLB 1, NHL 3.
4. Tap Refresh today's games from ESPN. If it loads, the live badge shows.
   If it fails, the pre-run Oct 26 games stay on screen, keep going.
5. Tap a game card to expand it. Check the legal broadcaster and the findings counts.
6. Tap Present mode once, check the huge text fits the monitor, tap Exit.

## Cast to the monitor

iPhone:
- Control Center, Screen Mirroring, pick the Apple TV or AirPlay monitor.
- If no AirPlay monitor, use a USB-C to HDMI adapter, plug it in, pick the HDMI input on the monitor.
- Full screen: Safari does not do full screen for a web page. Tap Share, Add to Home Screen, open the demo from the home screen, rotate to landscape.

Android:
- Quick Settings, Cast or Screen Cast, pick the Chromecast or TV.
- Or use a USB-C to HDMI adapter.
- Full screen: tap Full screen at the top of the page.

## During the lecture, no typing

- Games tab: tap a game card to expand it. Tap Copy check command to copy it, paste it in a terminal later if you want to show the command.
- Present mode: tap Present this game on a card, the monitor shows huge team names, kickoff, and legal broadcaster. Tap Exit present mode to go back.
- Channels tab: tap a category chip, Broadcast, Kids, Sports, Entertainment, News, Lifestyle, Movies, Premium. 61 channels total. No typing needed.
- Findings tab: tap a game to expand its findings. Student view shows domain only. Suspicious domains are plain text, never links. No pirate video, no play button for a suspected page.
- Lab Player tab: tap Load Mux test stream, then play. It plays legal test content only. Findings are never wired to the player.

## If something goes wrong

- Page will not load: check Wi-Fi, reload, or open the local copy from the laptop and cast the laptop screen instead.
- Live ESPN refresh fails: keep using the pre-run Oct 26 games, they are embedded in the page.
- Cast drops: plug in the HDMI adapter, pick the HDMI input, reload the page.
- Full screen will not work on iPhone Safari: use Add to Home Screen, or Present mode, which hides the tabs and fills the screen.
- A student asks for a pirate link: do not share it. Show the legal source on the game card, and the findings table, and the takedown template in the lecture kit.

## After class

- GitHub Action Refresh Free TV Demo runs daily at 12:00 ET, and on demand from the GitHub mobile app, Actions, Refresh Free TV Demo, Run workflow. It rebuilds the page with the next day's games in mock mode.
- Live search (Bing/Google) needs API keys and is not run in the Action. Run pirate-stream-search.py on a lab PC for a live search.
