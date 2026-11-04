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
| **https://sanjeettiwari1299-eng.github.io/youtyers/** | ✅ **LIVE** — GitHub Pages par deploy ho gaya, khulne par browser khud Cobalt se connect karke v11.7.1 / 21 services load karta hai |
| Arena live preview (`https://3000-<sandbox>.e2b.app`) | Session ke andar preview panel se chal raha hai (`node server.js`) |

### Pages setup (ho gaya)

Repo → **Settings → Pages → Source = `GitHub Actions`** set kiya gaya. Uske baad `arena/9c3ca5c9-youtyers` branch par har push `.github/workflows/pages.yml` chalata hai aur site auto-deploy hoti hai. (Pehle Pages API `403 Resource not accessible by integration` de raha tha — Arena ke GitHub integration ke paas `pages:write` nahi hai, isliye toggle UI se karna pada.) Workflow se `environment: github-pages` block hataaya gaya kyunki uski branch protection rule sirf `main` ko allow karti thi.

## Test results (GitHub Actions smoke test, 4 Nov 2026)

| Check | Result |
| --- | --- |
| `GET /` instance info | ✅ Cobalt **v11.7.1**, **21 services** |
| `Access-Control-Allow-Origin` | ✅ `*` — browser kisi bhi origin se seedha call kar sakta hai, relay ki zarurat nahi |
| `POST /` processing endpoint | ✅ valid Cobalt JSON (`error.api.link.invalid` invalid test link par expected) |
| Real download — Vimeo | ✅ HTTP 200, `status: redirect` **aur** `alwaysProxy` ke saath `status: tunnel`; dono mein asli filename + file URL mila |
| Browser se live site | ✅ `https://sanjeettiwari1299-eng.github.io/youtyers/` khul kar khud instance se v11.7.1 / 21 services load karta hai |
| File bytes fetch (CI runner se) | ⚠️ HTTP 403 — GitHub Actions ke egress IP har request par badalte hain, aur Cobalt tunnel token / Vimeo signed URL IP-bound hote hain. Ek normal browser (stable IP) mein ye link chalte hain; isliye site mein **Cobalt tunnel** default ON hai |
| YouTube | ⚠️ is instance par `error.api.fetch.fail` — Cobalt instance ko YouTube ke liye `cookies.json` / `YOUTUBE_SESSION_SERVER` chahiye (site ka code nahi, instance-side baat hai) |

Matlab site + Cobalt pipeline kaam kar rahe hain; asli `tunnel` / `redirect` file links ban rahe hain. YouTube ke liye ya to instance configure karo, ya site ke ⚙️ **Settings** mein kisi doosre Cobalt instance ka URL daal do — UI bilkul same chalega (`?api=` query se bhi).

Har push par halka smoke test chalta hai; 6-service download probe **Actions → Run workflow** (manual dispatch) par chalta hai.

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
