# youtyers backend

yt-dlp powered download backend. It speaks the cobalt API shape, so the youtyers
web UI can use it as its "Cobalt API URL".

## Deploy on SnapDeploy (recommended)

1. snapdeploy.dev pe account banao (no credit card).
2. **New Container → Deploy from GitHub** → repo `sanjeettiwari1299-eng/youtyers`,
   branch `arena/04dd398d-youtyers`, Dockerfile path `Dockerfile`.
3. Environment variables (optional but recommended):
   - `API_KEY` = koi random string. Ise set karoge to UI ke Settings mein bhi same key daalni hogi.
   - `PUBLIC_URL` = container ka URL, jaise `https://youtyers.containers.snapdeploy.app` (optional, auto detect hota hai).
4. Deploy karo. Port `9000` (SnapDeploy `PORT` inject karta hai, server use kar leta hai).
5. Browser mein `https://<your-container-url>/` kholo. Cobalt-style JSON aana chahiye.
6. Pages wali UI ke **Settings → Cobalt API URL** mein `https://<your-container-url>/` daalo,
   aur agar `API_KEY` set kiya hai to **API key** field mein wahi key.

Free tier notes: container kuch der idle rehne par sleep ho jata hai, pehli request pe ~60 sec
lag sakte hain. Ek download ka file server pe 15 minute tak rehta hai (tunnel ke liye).

## Run with Docker locally

```bash
docker compose up -d --build
```

Optional `.env` next to `docker-compose.yml`:

```env
PORT=9000          # host port
API_KEY=change-me  # if set, every request needs this key
```

`restart: unless-stopped` is set, so the container comes back after reboot / sleep-wake.
Docker itself must start on boot (Docker Desktop: "Start Docker Desktop when you sign in").

## API

Cobalt-style (used by the UI):

```bash
curl -X POST https://<host>/ \
  -H "Authorization: Api-Key change-me" -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","downloadMode":"auto","videoQuality":"1080"}'
# -> {"status":"tunnel","url":"https://<host>/tunnel?id=...","filename":"..."}
curl -L "https://<host>/tunnel?id=..." -o video.mp4
```

- `downloadMode`: `auto` (video, default), `audio` (mp3), `mute` (treated as video).
- `videoQuality`: `max` (default, capped at 1080p to keep free tiers working), `720`, `480`, etc.

Simple direct download:

```bash
curl -L -H "X-API-Key: change-me" "https://<host>/download?url=VIDEO_URL&type=audio" -o audio.mp3
```

Other: `GET /` (instance info), `GET /health`.
Errors are JSON: `{"status":"error","error":{"code":"..."}}` with `400`, `401`, `404`, `502`.

## YouTube not downloading

YouTube often blocks server IPs. Try in order:

1. Rebuild to get the newest yt-dlp: `docker compose build --no-cache && docker compose up -d`
   (on SnapDeploy: redeploy the container).
2. Cookies from a logged-in browser: export `youtube.com` cookies in Netscape format
   (extension "Get cookies.txt LOCALLY"), save as `cookies.txt`, and set
   `COOKIE_FILE=/cookies.txt`. For local Docker, uncomment the `volumes` lines in `docker-compose.yml`.
   On SnapDeploy the file has to be in the image, so this is not easy there. Use a secondary account.

Other sites (Instagram, X, TikTok, etc.) usually work without cookies.

## Updating

yt-dlp changes often. Rebuild / redeploy regularly.

## Running without Docker

```bash
pip install -U yt-dlp
# ffmpeg must be installed (merge + mp3)
PORT=9000 python server.py
```
