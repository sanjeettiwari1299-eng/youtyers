# Youtyers — apna Cobalt video downloader

Ye repo do cheezein rakhta hai:

| File | Kaam |
|------|------|
| `Dockerfile` | Aapka **Cobalt API server** (`ghcr.io/imputnet/cobalt:latest`) — yahi asli download engine hai |
| `index.html` + `server.js` + `api/cobalt.js` | Us engine ke upar **aapki apni website** (UI + relay) |

Default Cobalt instance: `https://youtyers-528be.containers.snapdeploy.app/` (GET `/` par instance ka JSON milta hai, `cobalt.version 11.7.1`, 21 services).

## Site kaise chalao (local)

```bash
node server.js          # http://localhost:3000
PORT=8080 node server.js
```

Koi npm install nahi chahiye — Node 18+ ka built-in `fetch` aur `http` use hota hai.

## Kaise kaam karta hai

1. Browser `POST <COBALT_API>/` karta hai `Accept: application/json` + `Content-Type: application/json` ke saath.
2. Cobalt `tunnel` / `redirect` (file URL + filename), `picker` (multiple media), ya `error` return karta hai.
3. UI file ka download button dikhata hai. Agar CORS / network direct call block kare, to request apne hi origin ke `/api/cobalt?api=...` relay se jaati hai (Vercel par `api/cobalt.js`, local par `server.js`).

Relay isliye hai kyunki kuch Cobalt instances cross-origin calls block kar dete hain. Direct call pehle try hoti hai (fast, file instance se seedhe browser mein stream hoti hai).

## Cobalt instance badalna

- Site ke ⚙️ **Settings** mein API URL aur optional API key (`Api-Key …` / `Bearer …`) daalo — browser ke `localStorage` mein save hota hai.
- Ya URL ke saath query: `https://<aapka-url>/?api=https%3A%2F%2Fmy-cobalt.example%2F`
- Ya deploy time par env var: `COBALT_API_URL`

**Note:** public `api.cobalt.tools` par bot protection (Turnstile) hai, isliye apna hi instance use karna sabse reliable hai. Docker image yahin repo ke `Dockerfile` mein hai; container deploy karte waqt `API_URL` env var apne public URL par set karna zaroori hai (Cobalt tunnels usi URL par bante hain).

## Deploy (Vercel)

Repo root se ye files deploy karo: `index.html`, `vercel.json`, `package.json`, `api/cobalt.js`. Koi build step nahi — `index.html` static serve hota hai aur `api/cobalt.js` ek Node serverless function ban jata hai. Production URL `https://<project>.vercel.app` milta hai.

## Features

- Video (auto) / Audio-only (MP3 etc.) / Mute mode
- Quality 240p → 4K, codec (H264/VP9/AV1), container, bitrate, filename style, subtitles
- `picker` posts (Instagram carousel, TikTok photo) ke liye har item ka alag download
- Multi-media audio, always-proxy, better-audio, metadata toggles
- Instance health check + supported services list, recent links, Hindi-friendly error messages
- Download, force-save with progress, copy link, open in new tab

## Disclaimer

Sirf wahi content download karo jiska aapko legal adhikar hai aur jo service ke terms ke andar ho.
