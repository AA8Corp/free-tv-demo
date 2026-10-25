#!/usr/bin/env python3
"""Build the phone-first GitHub Pages demo for the free TV experiment.

Reads today-games-2026-10-26.json, dashboard (answer key) json,
and channels.json, and writes a single self-contained index.html
with the Oct 26 data embedded, plus live ESPN fetch at runtime.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Two layouts: Website_Portfolio staging uses assets/free-tv-demo/,
# the standalone free-tv-demo repo uses the repo root itself.
if (ROOT / "assets" / "free-tv-demo").exists():
    BASE = ROOT / "assets" / "free-tv-demo"
else:
    BASE = ROOT
EXP = Path(__file__).resolve().parent

games = json.loads((BASE / "data" / "today-games.json").read_text())
dashboard = json.loads((BASE / "data" / "dashboard.json").read_text())
channels = json.loads((BASE / "data" / "channels.json").read_text())

# Findings lookup by event name, from the mock dashboard run for Oct 26.
findings = {}
for item in dashboard.get("events", []):
    ev = item["event"]
    findings[ev["event"]] = {
        "league": ev["league"],
        "date": ev["date"],
        "kickoff_et": ev["kickoff_et"],
        "legal_broadcaster": ev["legal_broadcaster"],
        "legal_source_url": ev["legal_source_url"],
        "findings": item.get("findings", []),
        "alert_count": item.get("alert_count", 0),
    }

embedded = {
    "date": games["date"],
    "count": games["count"],
    "games": games["games"],
    "findings": findings,
    "channels": channels["channels"],
}

html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#111111">
<title>AA8 Free TV Demo, Oct 26</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: #111; color: #fff; font-size: 18px; line-height: 1.45; }
header { position: sticky; top: 0; background: #111; padding: 12px 16px; border-bottom: 1px solid #333; z-index: 10; }
h1 { font-size: 22px; margin: 0 0 4px 0; }
.sub { color: #bbb; font-size: 15px; }
button { font-size: 18px; min-height: 56px; padding: 12px 18px; border-radius: 12px; border: none; background: #1e88e5; color: #fff; margin: 4px 4px 4px 0; cursor: pointer; }
button.ghost { background: #333; }
button.big { width: 100%; font-size: 20px; }
button.active { background: #43a047; }
.tabs { display: flex; gap: 8px; padding: 12px 16px 0 16px; flex-wrap: wrap; }
.tabs button { flex: 1; min-width: 100px; background: #222; }
.tabs button.active { background: #1e88e5; }
main { padding: 16px; max-width: 900px; margin: 0 auto; }
.card { background: #1c1c1c; border: 1px solid #333; border-radius: 16px; padding: 16px; margin-bottom: 16px; }
.card h2 { margin: 0 0 8px 0; font-size: 22px; }
.badge { display: inline-block; background: #333; border-radius: 999px; padding: 4px 12px; font-size: 15px; margin: 2px 4px 2px 0; }
.badge.live { background: #2e7d32; }
.badge.mock { background: #6a1b9a; }
a { color: #90caf9; }
code { background: #000; padding: 4px 8px; border-radius: 6px; font-size: 15px; word-break: break-all; }
details summary { cursor: pointer; font-size: 20px; padding: 8px 0; }
table { width: 100%; border-collapse: collapse; font-size: 15px; }
td, th { border-bottom: 1px solid #333; padding: 8px 4px; text-align: left; vertical-align: top; }
.chip { background: #222; border: 1px solid #444; color: #fff; }
input[type="search"] { width: 100%; font-size: 18px; padding: 14px; border-radius: 12px; border: 1px solid #444; background: #222; color: #fff; margin: 8px 0; }
video { width: 100%; border-radius: 12px; background: #000; }
#present { display: none; position: fixed; inset: 0; background: #000; color: #fff; z-index: 50; padding: 32px 24px; text-align: center; }
#present h2 { font-size: 42px; line-height: 1.2; }
#present p { font-size: 26px; }
.hidden { display: none !important; }
.note { color: #bbb; font-size: 15px; }
</style>
</head>
<body>
<header>
  <h1>AA8 Free TV Demo</h1>
  <div class="sub">Anti-piracy detection, instructor demo. Monday Oct 26, 2026. No typing in class, tap a game.</div>
  <div>
    <button id="fsBtn" onclick="toggleFullscreen()">Full screen</button>
    <button class="ghost" onclick="togglePresent()">Present mode</button>
  </div>
</header>

<div class="tabs">
  <button class="active" onclick="showTab('games', this)">Games</button>
  <button onclick="showTab('channels', this)">Channels</button>
  <button onclick="showTab('findings', this)">Findings</button>
  <button onclick="showTab('player', this)">Lab Player</button>
  <button onclick="showTab('cast', this)">Cast</button>
</div>

<main>
<section id="tab-games">
  <p><span class="badge live" id="liveBadge">Pre-run data: Oct 26, 2026</span> <span class="badge mock">Mock findings, classroom test</span></p>
  <p id="gamesCount"></p>
  <p><button class="big" onclick="refreshLive()">Refresh today's games from ESPN</button></p>
  <div id="gamesList"></div>
  <p class="note">Games come from the ESPN public scoreboard, no API key. Tap a game to expand it. The check command is copied when you tap Copy command. Findings are pre-run in mock mode, so the class sees the same result every time.</p>
</section>

<section id="tab-channels" class="hidden">
  <p>61 channels. Tap a category, no typing needed.</p>
  <div id="catChips"></div>
  <input type="search" id="chanSearch" placeholder="Search channels, optional" oninput="renderChannels()">
  <div id="channelsList"></div>
</section>

<section id="tab-findings" class="hidden">
  <p>Student view shows domain only. Teacher view below shows the full finding, with suspicious domains as plain text, never as links. No pirate video, no play button for a suspected page.</p>
  <div id="findingsList"></div>
</section>

<section id="tab-player" class="hidden">
  <div class="card">
    <h2>Lab Player</h2>
    <p>Plays legal and owned streams only. Default is the Mux legal test stream. Findings are never wired to this player.</p>
    <video id="labPlayer" controls playsinline></video>
    <p id="playerStatus">Status: ready.</p>
    <p><input id="hlsUrl" type="url" placeholder="Paste an .m3u8 URL you own, or a legal test stream" style="width:100%;font-size:16px;padding:12px;border-radius:10px;border:1px solid #444;background:#222;color:#fff;"></p>
    <button onclick="loadLabStream()">Load allowed stream</button>
    <button class="ghost" onclick="loadTestStream()">Load Mux test stream</button>
    <button class="ghost" onclick="stopLabStream()">Stop</button>
    <p class="note">Allowlist: localhost, lab private IPs, test-streams.mux.dev, devstreaming-cdn.apple.com, and known legal broadcaster domains. Any other domain is blocked.</p>
  </div>
</section>

<section id="tab-cast" class="hidden">
  <div class="card">
    <h2>Run this from your phone, cast to a monitor</h2>
    <ol>
      <li><strong>Open this page on your phone.</strong> It is live at aa8corp.github.io/free-tv-demo/</li>
      <li><strong>Full screen:</strong> tap Full screen at the top. On iPhone, Safari does not do full screen for a web page, so instead tap Share, then Add to Home Screen, open it from the home screen, and rotate to landscape. On Android Chrome, tap Full screen and it fills the monitor.</li>
      <li><strong>Cast, iPhone:</strong> Control Center, Screen Mirroring, pick the Apple TV or AirPlay monitor. Or use a USB-C to HDMI adapter.</li>
      <li><strong>Cast, Android:</strong> Quick Settings, Cast or Screen Cast, pick the Chromecast or TV. Or use a USB-C to HDMI adapter.</li>
      <li><strong>In class:</strong> tap Games, tap a game card to expand it, tap Present mode for huge text on the monitor. Tap a channel category chip to filter channels, no typing.</li>
      <li><strong>Refresh games:</strong> tap Refresh today's games from ESPN. That fetches live from ESPN in the phone browser, no server, no API key. If the venue Wi-Fi blocks it, the pre-run Oct 26 games stay on screen.</li>
    </ol>
    <p class="note">If the monitor shows the browser address bar, rotate the phone to landscape and scroll down once, or use Present mode, which hides the tabs.</p>
  </div>
</section>
</main>

<div id="present">
  <h2 id="presentTitle">Pick a game first</h2>
  <p id="presentBody">Tap a game card, then Present mode.</p>
  <p><button onclick="togglePresent()">Exit present mode</button></p>
</div>

<script src="https://cdn.jsdelivr.net/npm/hls.js@1.5.13/dist/hls.min.js"></script>
<script>
const EMBEDDED = __EMBEDDED_JSON__;
let games = EMBEDDED.games.slice();
let findings = EMBEDDED.findings;
let channels = EMBEDDED.channels.slice();
let pickedGame = null;

function esc(s){ return String(s==null?"":s).replace(/[&<>"']/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
function showTab(id, btn){
  ["games","channels","findings","player","cast"].forEach(function(t){
    document.getElementById("tab-"+t).classList.toggle("hidden", t!==id);
  });
  document.querySelectorAll(".tabs button").forEach(function(b){ b.classList.remove("active"); });
  if(btn) btn.classList.add("active");
  window.scrollTo(0,0);
}
function toggleFullscreen(){
  if(document.fullscreenElement){ document.exitFullscreen(); return; }
  var el = document.documentElement;
  if(el.requestFullscreen){ el.requestFullscreen(); }
  else { alert("Full screen is not available in this browser. On iPhone, use Add to Home Screen, then open it from the home screen and rotate to landscape."); }
}
function togglePresent(){
  var p = document.getElementById("present");
  if(p.style.display==="block"){ p.style.display="none"; return; }
  if(pickedGame){
    document.getElementById("presentTitle").textContent = pickedGame.league + ": " + pickedGame.event;
    document.getElementById("presentBody").textContent = pickedGame.date + " " + pickedGame.kickoff_et + " ET. Legal: " + pickedGame.legal_broadcaster + ".";
  }
  p.style.display="block";
  if(document.documentElement.requestFullscreen){ document.documentElement.requestFullscreen().catch(function(){}); }
}
function copyCommand(cmd, btn){
  if(navigator.clipboard){ navigator.clipboard.writeText(cmd).then(function(){ if(btn) btn.textContent="Copied"; }); }
  else { prompt("Copy this command:", cmd); }
}
function renderGames(){
  document.getElementById("gamesCount").textContent = games.length + " games for " + EMBEDDED.date + ".";
  var out = "";
  games.forEach(function(g){
    var f = findings[g.event] || {findings:[], alert_count:0};
    var high = 0, med = 0, low = 0;
    f.findings.forEach(function(x){ if(x.score>=6) high++; else if(x.score>=3) med++; else low++; });
    var cmd = 'python3 pirate-stream-search.py --event "' + g.event + '" --date ' + g.date + ' --league ' + g.league + ' --mock';
    out += '<div class="card"><details><summary><strong>' + esc(g.league) + ': ' + esc(g.event) + '</strong><br>' +
      esc(g.date) + ' ' + esc(g.kickoff_et) + ' ET &nbsp;|&nbsp; Legal: ' + esc(g.legal_broadcaster) + '</summary>' +
      '<p>Legal source: <a href="' + esc(g.legal_source_url) + '">' + esc(g.legal_source_url) + '</a></p>' +
      '<p>Findings: ' + high + ' HIGH, ' + med + ' MEDIUM, ' + low + ' LOW. Draft alerts: ' + (f.alert_count||0) + '</p>' +
      '<p><button onclick="copyCommand(' + JSON.stringify(cmd).replace(/"/g, "&quot;") + ', this)">Copy check command</button> ' +
      '<button class="ghost" onclick="pickGame(' + JSON.stringify(g.event).replace(/"/g, "&quot;") + ')">Present this game</button></p>' +
      '<p><code>' + esc(cmd) + '</code></p>' +
      '</details></div>';
  });
  document.getElementById("gamesList").innerHTML = out || "<p>No games found.</p>";
}
function pickGame(eventName){
  var g = games.find(function(x){ return x.event===eventName; });
  if(!g) return;
  pickedGame = g;
  document.getElementById("presentTitle").textContent = g.league + ": " + g.event;
  document.getElementById("presentBody").textContent = g.date + " " + g.kickoff_et + " ET. Legal: " + g.legal_broadcaster + ".";
  togglePresent();
}
function renderChannels(){
  var cats = ["All"].concat(Array.from(new Set(channels.map(function(c){ return c.category; }))));
  var chips = document.getElementById("catChips");
  if(!chips.dataset.built){
    chips.innerHTML = cats.map(function(c){ return '<button class="chip" onclick="filterCat(\'' + c + '\', this)">'+esc(c)+'</button>'; }).join("");
    chips.dataset.built = "1";
    chips.dataset.cat = "All";
  }
  var cat = chips.dataset.cat || "All";
  var q = (document.getElementById("chanSearch").value || "").toLowerCase();
  var list = channels.filter(function(c){ return (cat==="All" || c.category===cat) && (!q || c.channel.toLowerCase().indexOf(q)>=0 || c.legal_service.toLowerCase().indexOf(q)>=0); });
  document.getElementById("channelsList").innerHTML = list.map(function(c){
    return '<div class="card"><h2>'+esc(c.channel)+'</h2><p><span class="badge">'+esc(c.category)+'</span> <span class="badge">'+esc(c.owner)+'</span></p><p>Legal: '+esc(c.legal_service)+'<br><a href="'+esc(c.legal_url)+'">'+esc(c.legal_url)+'</a></p><p class="note">'+esc(c.notes)+'</p></div>';
  }).join("") || "<p>No channels match.</p>";
}
function filterCat(cat, btn){
  document.getElementById("catChips").dataset.cat = cat;
  document.querySelectorAll("#catChips .chip").forEach(function(b){ b.classList.remove("active"); });
  if(btn) btn.classList.add("active");
  renderChannels();
}
function renderFindings(){
  var out = "";
  Object.keys(findings).forEach(function(name){
    var f = findings[name];
    var rows = f.findings.map(function(x){
      return "<tr><td>"+esc(x.domain)+"</td><td>"+esc(x.score)+"</td><td>"+esc(x.verdict)+"</td><td>"+esc((x.indicators||[]).join("; "))+"</td></tr>";
    }).join("");
    out += '<div class="card"><details><summary><strong>'+esc(f.league)+': '+esc(name)+'</strong></summary>' +
      '<p>Kickoff '+esc(f.date)+' '+esc(f.kickoff_et)+' ET. Legal: '+esc(f.legal_broadcaster)+'</p>' +
      '<table><tr><th>Domain</th><th>Score</th><th>Verdict</th><th>Indicators</th></tr>'+rows+'</table></details></div>';
  });
  document.getElementById("findingsList").innerHTML = out;
}
async function refreshLive(){
  var badge = document.getElementById("liveBadge");
  badge.textContent = "Fetching live from ESPN...";
  try {
    var now = new Date();
    var parts = new Intl.DateTimeFormat("en-US", {timeZone:"America/New_York", year:"numeric", month:"2-digit", day:"2-digit"}).formatToParts(now);
    var y = parts.find(function(p){return p.type==="year";}).value;
    var m = parts.find(function(p){return p.type==="month";}).value;
    var d = parts.find(function(p){return p.type==="day";}).value;
    var dateStr = y+m+d;
    var leagues = [["NFL","football/nfl"],["NBA","basketball/nba"],["WNBA","basketball/wnba"],["NCAA Football","football/college-football"],["NCAA Basketball","basketball/mens-college-basketball"],["MLB","baseball/mlb"],["NHL","hockey/nhl"]];
    var all = [];
    for(var i=0;i<leagues.length;i++){
      var res = await fetch("https://site.api.espn.com/apis/site/v2/sports/"+leagues[i][1]+"/scoreboard?dates="+dateStr);
      var data = await res.json();
      (data.events||[]).forEach(function(e){
        var dt = new Date(e.date);
        var kick = new Intl.DateTimeFormat("en-US", {timeZone:"America/New_York", hour:"2-digit", minute:"2-digit", hour12:false}).format(dt);
        var bc = "";
        try { bc = e.competitions[0].broadcasts[0].names[0] || ""; } catch(err) {}
        all.push({league: leagues[i][0], event: e.name, date: y+"-"+m+"-"+d, kickoff_et: kick, legal_broadcaster: bc||"Check league schedule", legal_source_url: "https://www.espn.com/", notes:"Live from ESPN scoreboard."});
      });
    }
    if(all.length){
      all.sort(function(a,b){ return (a.kickoff_et||"").localeCompare(b.kickoff_et||""); });
      games = all;
      renderGames();
      badge.textContent = "Live from ESPN: " + all.length + " games today";
      badge.classList.add("live");
    } else {
      badge.textContent = "ESPN returned no games today, showing pre-run Oct 26 games";
    }
  } catch(err) {
    badge.textContent = "Live fetch failed, showing pre-run Oct 26 games";
  }
}
var hls = null;
function setStatus(t){ document.getElementById("playerStatus").textContent = "Status: " + t; }
function loadLabStream(){
  var url = document.getElementById("hlsUrl").value.trim();
  if(!url){ setStatus("Paste an .m3u8 URL you own, or load the Mux test stream."); return; }
  var allowed = ["localhost","127.0.0.1","test-streams.mux.dev","devstreaming-cdn.apple.com"];
  var host = "";
  try { host = new URL(url).hostname; } catch(e) { setStatus("That URL did not parse."); return; }
  var ok = allowed.some(function(d){ return host===d || host.endsWith("."+d); }) || host.startsWith("192.168.") || host.startsWith("10.") || host.indexOf("nfl.com")>=0 || host.indexOf("espn.com")>=0 || host.indexOf("nba.com")>=0;
  if(!ok){ setStatus("Blocked: that domain is not on the allowlist."); return; }
  var video = document.getElementById("labPlayer");
  if(hls){ hls.destroy(); hls = null; }
  if(window.Hls && Hls.isSupported()){ hls = new Hls(); hls.loadSource(url); hls.attachMedia(video); hls.on(Hls.Events.MANIFEST_PARSED, function(){ setStatus("Playing allowed stream: "+url); video.play(); }); hls.on(Hls.Events.ERROR, function(e,d){ setStatus("Player error: "+d.type+" "+d.details); }); }
  else if(video.canPlayType("application/vnd.apple.mpegurl")){ video.src = url; video.addEventListener("loadedmetadata", function(){ setStatus("Playing allowed stream: "+url); video.play(); }); }
  else { setStatus("This browser cannot play HLS."); }
}
function loadTestStream(){ document.getElementById("hlsUrl").value = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"; loadLabStream(); }
function stopLabStream(){ var video = document.getElementById("labPlayer"); if(hls){ hls.destroy(); hls = null; } video.pause(); video.removeAttribute("src"); video.load(); setStatus("Stopped."); }
renderGames();
renderChannels();
renderFindings();
</script>
</body>
</html>
"""

html = html.replace("__EMBEDDED_JSON__", json.dumps(embedded))
out = BASE / "index.html"
out.write_text(html, encoding="utf-8")
print(f"Wrote {out}, {len(html)} bytes, {len(games['games'])} games, {len(channels['channels'])} channels")
