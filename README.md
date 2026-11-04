# youtyers

Simple self-hosted downloader API powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).
(Replaces the old cobalt setup.)

## Run

```bash
docker compose up -d --build
```

Optional `.env` next to `docker-compose.yml`:

```env
PORT=9000          # host port
API_KEY=change-me  # if set, every request needs this key
```

## Use

```bash
# video (mp4)
curl -L -H "X-API-Key: change-me" \
  "http://localhost:9000/download?url=https://www.youtube.com/watch?v=VIDEO_ID" -o video.mp4

# audio (mp3)
curl -L -H "X-API-Key: change-me" \
  "http://localhost:9000/download?url=https://www.youtube.com/watch?v=VIDEO_ID&type=audio" -o audio.mp3
```

- `type` is `video` (default) or `audio`.
- Key can also be passed as `&key=...` in the URL.
- Health check: `GET /health`.
- Errors come back as JSON (`400` bad input, `401` wrong key, `502` download failed).

Note: the server is synchronous. A long video takes time before the response starts.

## Keep it running after sleep / reboot

`restart: unless-stopped` is set in `docker-compose.yml`, so the container comes back
automatically. Also make sure Docker starts on boot / login:

- **Docker Desktop (Windows/macOS):** Settings → General → enable "Start Docker Desktop when you sign in".
- **Linux:** `sudo systemctl enable docker`

Check status: `docker compose ps` (should show `Up`). If it shows `Exited`, check
`docker compose logs -f downloader`.

## Updating

YouTube changes often, so update yt-dlp regularly:

```bash
docker compose build --no-cache && docker compose up -d
```

If YouTube downloads start failing (`Sign in to confirm you're not a bot`, `403`, etc.),
rebuild as above first. That fixes most cases.

## YouTube cookies (if YouTube blocks the server)

1. Log into YouTube in a browser, export `youtube.com` cookies in Netscape format
   (extension: "Get cookies.txt LOCALLY").
2. Save as `cookies.txt` next to `docker-compose.yml`. **Do not commit it** (it is in `.gitignore`).
3. In `docker-compose.yml`, set `COOKIE_FILE: /cookies.txt` and uncomment the `volumes` lines.
4. `docker compose up -d`.

Use a secondary account. Cookies can get the account flagged.

## Running without Docker

```bash
pip install -U yt-dlp
# plus ffmpeg installed on the system (needed for merge and mp3)
python server.py   # listens on 0.0.0.0:9000
```
