# csv_spotify_export
Export a Spotify playlist to CSV (artist, title, album, duration, ISRC, Spotify link, Beatport/Traxsource/Bandcamp search links, empty `owned` column).

1. Client ID lives in `.env` (`SPOTIFY_CLIENT_ID=...`). Redirect URI in the Spotify app must be `http://127.0.0.1:8888/callback`.
2. `python3 spotify_to_csv.py "<playlist link>" -o house.csv`
