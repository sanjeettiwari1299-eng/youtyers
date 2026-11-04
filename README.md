# youtyers

Self-hosted [cobalt](https://github.com/imputnet/cobalt) downloader API.

## Run

```bash
docker compose up -d
```

API: `http://localhost:9000/`

Optional `.env` (same folder as `docker-compose.yml`):

```env
API_URL=http://localhost:9000/   # URL your frontend uses to reach the API
COBALT_PORT=9000                 # host port
```

### Keep it running after sleep / reboot

`restart: unless-stopped` is set in `docker-compose.yml`, so the container comes back
automatically. Also make sure Docker itself starts on boot / login:

- **Docker Desktop (Windows/macOS):** Settings → General → enable "Start Docker Desktop when you sign in".
- **Linux:** `sudo systemctl enable docker`

Check status: `docker compose ps` — it should show `Up`. If it shows `Exited`, run
`docker compose up -d` and then `docker compose logs -f cobalt`.

### Updating (YouTube breaks often, so update regularly)

```bash
docker compose pull && docker compose up -d
```

## YouTube not downloading

YouTube blocks many self-hosted instances, so downloads often fail with
`file tunnel empty`, `0B file`, `youtube asked the instance to log in`, or
`Failed to extract signature decipher algorithm`. This is a known upstream issue, not
something this repo can fully fix. Things to try, in order:

1. **Update the image** (see above). Most YouTube fixes come as image updates.
2. **Use cookies from a logged-in browser session:**
   - Export `youtube.com` cookies in Netscape format with a browser extension
     (for example "Get cookies.txt LOCALLY") while logged in.
   - Save them as `cookies.json` next to `docker-compose.yml`. **Do not commit this file.**
   - In `docker-compose.yml`, uncomment `COOKIE_PATH` and the `volumes` line.
   - Run `docker compose up -d`.
   - Use a secondary account. Cookies can get the account flagged.
3. **Fallback without cobalt:** use `yt-dlp` directly for YouTube (`pip install -U yt-dlp`).
   Its update cadence is usually faster than cobalt's.

Other sites (Instagram, X, TikTok, etc.) generally work without cookies.
