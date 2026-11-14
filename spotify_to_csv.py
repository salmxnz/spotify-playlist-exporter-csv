#!/usr/bin/env python3
"""Export a Spotify playlist to CSV (stdlib only).

Setup (one time):
  1. Create a free app at https://developer.spotify.com/dashboard
  2. Add this Redirect URI to the app: http://127.0.0.1:8888/callback
  3. Put SPOTIFY_CLIENT_ID=... in .env next to this script (no secret needed: PKCE login)

Usage:
  python3 spotify_to_csv.py "https://open.spotify.com/playlist/<id>" [-o out.csv]

A browser opens once for you to log in. The token is kept in memory only.
"""
import argparse, base64, csv, hashlib, http.server, json, os, re, secrets
import sys, threading, urllib.parse, urllib.request, webbrowser

REDIRECT = "http://127.0.0.1:8888/callback"
API = "https://api.spotify.com/v1"


def login(client_id):
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT,
        "code_challenge_method": "S256", "code_challenge": challenge, "state": state,
        "scope": "playlist-read-private playlist-read-collaborative"})
    box = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            box["code"], box["state"] = q.get("code", [None])[0], q.get("state", [None])[0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b"Done. You can close this tab.")
        def log_message(self, *a): pass

    srv = http.server.HTTPServer(("127.0.0.1", 8888), H)
    t = threading.Thread(target=srv.handle_request); t.start()
    print("Opening browser to log in to Spotify...")
    webbrowser.open(url); t.join(300); srv.server_close()
    if box.get("state") != state or not box.get("code"):
        sys.exit("Login failed or timed out.")
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": box["code"], "redirect_uri": REDIRECT,
        "client_id": client_id, "code_verifier": verifier}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://accounts.spotify.com/api/token", body)) as r:
        return json.load(r)["access_token"]


def get(token, url):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def q(s):
    return urllib.parse.quote_plus(s)


def load_env():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        for line in open(path):
            k, _, v = line.strip().partition("=")
            if k and not k.startswith("#"):
                os.environ.setdefault(k, v)


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("link"); ap.add_argument("-o", "--out", default="playlist.csv")
    a = ap.parse_args()
    m = re.search(r"playlist[/:]([A-Za-z0-9]+)", a.link)
    if not m: sys.exit("That doesn't look like a Spotify playlist link.")
    cid = os.environ.get("SPOTIFY_CLIENT_ID") or sys.exit("Set SPOTIFY_CLIENT_ID first.")
    token = login(cid)
    pid = m.group(1)
    name = get(token, f"{API}/playlists/{pid}?fields=name")["name"]
    url, rows = f"{API}/playlists/{pid}/items?limit=100", []
    while url:
        page = get(token, url)
        for it in page["items"]:
            t = it.get("item") or it.get("track")
            if not t or not t.get("id"): continue  # local files / removed
            artists = ", ".join(x["name"] for x in t["artists"])
            term = q(f"{artists} {t['name']}")
            rows.append({
                "artist": artists, "title": t["name"], "album": t["album"]["name"],
                "duration_s": round(t["duration_ms"] / 1000),
                "isrc": (t.get("external_ids") or {}).get("isrc", ""),
                "spotify_url": t["external_urls"]["spotify"],
                "beatport": f"https://www.beatport.com/search?q={term}",
                "traxsource": f"https://www.traxsource.com/search?term={term}",
                "bandcamp": f"https://bandcamp.com/search?q={term}",
                "owned": ""})
        url = page.get("next")
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"'{name}': wrote {len(rows)} tracks to {a.out}")


if __name__ == "__main__":
    main()
