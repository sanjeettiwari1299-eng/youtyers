# Youtyers — apna Cobalt video downloader

Ye repo do cheezein rakhta hai:

| File | Kaam |
|------|------|
| `Dockerfile` | Aapka **Cobalt API server** (`ghcr.io/imputnet/cobalt:latest`) — yahi asli download engine hai |
| `index.html` + `server.js` + `api/cobalt.js` | Us engine ke upar **aapki apni website** (UI + optional relay) |
| `.github/workflows/pages.yml` | GitHub Pages deploy + Cobalt API smoke test |

Default Cobalt instance: `https://youtyers-528be.containers.snapdeploy.app/`

## URLs

| URL | Status |
| --- | --- |
| Arena live preview (`https://3000-<sandbox>.e2b.app`) | Abhi chal raha hai (`node server.js`) |
| `https://sanjeettiwari1299-eng.github.io/youtyers/` | Pages enable hone ke baad workflow khud deploy karega |

### GitHub Pages enable karna (ek baar, 10 second)

Is repo par Pages API `403 Resource not accessible by integration` deta hai (Arena ke GitHub integration ke paas `pages:write` permission nahi hai — na sandbox token ke paas, na Actions `GITHUB_TOKEN` ke paas). Isliye ye toggle **repo owner ko UI se karna padega**:

1. Repo → **Settings** → **Pages**
2. **Build and deployment → Source** = `GitHub Actions`
3. **Actions** tab → workflow `Deploy Youtyers to GitHub Pages` → **Run workflow** (ya koi bhi naya push)

Uske baad har push par site auto-deploy hogi. Workflow mein Pages already-enabled check hai, to enable karte hi deploy chal jayega.

> Agar deploy step permission error de: **Settings → Actions → General → Workflow permissions → "Read and write permissions"** ON kar do.

## Test results (GitHub Actions smoke test, 4 Nov 2026)

| Check | Result |
| --- | --- |
| `GET /` instance info | ✅ Cobalt **v11.7.1**, **21 services** |
| `Access-Control-Allow-Origin` | ✅ `*` — browser kisi bhi origin se seedha call kar sakta hai, relay ki zarurat nahi |
| `POST /` processing endpoint | ✅ HTTP 400 with valid Cobalt JSON `{"status":"error","code":"error.api.link.invalid"}` (invalid test link ke liye expected response) — endpoint zinda aur sahi format de raha hai |

Matlab download pipeline reachable hai; bas sahi video link daalne par `tunnel` / `redirect` / `picker` response aayega aur file download ho jayegi.

## Local chalana

```bash
node server.js          # http://localhost:3000
PORT=8080 node server.js
```

Koi npm install nahi — Node 18+ ka built-in `fetch` aur `http`.

## Kaise kaam karta hai

1. Browser `POST <COBALT_API>/` karta hai `Accept: application/json` + `Content-Type: application/json` ke saath.
2. Cobalt `tunnel` / `redirect` (file URL + filename), `picker` (multiple media), `local-processing` ya `error` return karta hai.
3. UI download button dikhata hai. Agar CORS / network direct call block kare, to same-origin `/api/cobalt?api=…` relay use hota hai (Vercel par `api/cobalt.js`, local par `server.js`).

## Instance / relay badalna

- Site ke ⚙️ **Settings** mein API URL, optional API key (`Api-Key …` / `Bearer …`) aur optional Relay URL — browser `localStorage` mein save hota hai.
- Query params: `?api=https%3A%2F%2Fmy-cobalt.example%2F` aur `?relay=https%3A%2F%2Fhost%2Fapi%2Fcobalt%3Fapi%3D`
- Deploy time env var: `COBALT_API_URL`
- `window.COBALT_API_URL` / `window.COBALT_RELAY` se bhi override kar sakte ho.

**Note:** public `api.cobalt.tools` par bot protection (Turnstile) hai, isliye apna hi instance use karna sabse reliable hai. Docker image yahin repo ke `Dockerfile` mein hai; container deploy karte waqt `API_URL` env var apne public URL par set karna zaroori hai (Cobalt tunnels usi URL par bante hain).

## Features

- Video (auto) / Audio-only (MP3 etc.) / Mute mode
- Quality 240p → 4K, codec (H264/VP9/AV1), container, bitrate, filename style, subtitles
- `picker` posts (Instagram carousel, TikTok photo) ke liye har item ka alag download + background audio
- Multi-media, always-proxy, better-audio, metadata toggles
- Instance health check + supported services list, recent links, Hindi-friendly error messages
- Download, force-save with progress, copy link, open in new tab

## Deploy (Vercel — optional)

Files: `index.html`, `vercel.json`, `package.json`, `api/cobalt.js`. Koi build step nahi — `index.html` static serve hota hai aur `api/cobalt.js` Node function banta hai.

## Disclaimer

Sirf wahi content download karo jiska aapko legal adhikar hai aur jo service ke terms ke andar ho.
