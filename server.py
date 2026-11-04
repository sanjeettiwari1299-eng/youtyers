"""youtyers backend: yt-dlp powered, speaks the cobalt API shape.

So the existing youtyers web UI (cobalt-style client) can use it as its
"Cobalt API URL".

Endpoints
  GET  /                 instance info (cobalt-style JSON)
  GET  /health           {"status": "ok"}
  POST /                 cobalt-style request -> {"status":"tunnel","url":...}
  GET  /tunnel?id=...    streams the file prepared by POST /
  GET  /download?url=&type=video|audio   simple direct download (curl friendly)

Env vars
  PORT         listen port (default 9000; SnapDeploy injects this)
  API_KEY      if set, requests need "Authorization: Api-Key <key>",
               "X-API-Key: <key>" or "?key=<key>"
  COOKIE_FILE  optional Netscape cookies.txt path (helps with YouTube)
  PUBLIC_URL   optional public base URL, e.g. https://x.containers.snapdeploy.app
               (otherwise derived from the request Host / X-Forwarded-* headers)
  MAX_CONCURRENT  parallel downloads (default 2; free tiers have little RAM)
"""

import json
import os
import secrets
import shutil
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

import yt_dlp

PORT = int(os.environ.get("PORT", "9000"))
API_KEY = os.environ.get("API_KEY", "")
COOKIE_FILE = os.environ.get("COOKIE_FILE", "")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", "2"))
TUNNEL_TTL = 15 * 60  # seconds a prepared file stays downloadable

COBALT_VERSION = "11.7.1"  # version string the UI expects to see
SERVICES = [
    "bilibili", "bluesky", "dailymotion", "facebook", "instagram", "loom",
    "ok", "pinterest", "newgrounds", "reddit", "rutube", "snapchat",
    "soundcloud", "streamable", "tiktok", "tumblr", "twitch clips",
    "twitter", "vimeo", "vk", "youtube",
]

_slots = threading.BoundedSemaphore(MAX_CONCURRENT)
_tunnels = {}  # id -> {"path", "name", "dir", "created"}
_tunnels_lock = threading.Lock()


# ---------- downloading ----------

def _height_cap(quality: str) -> int:
    q = (quality or "").strip().lower()
    if q in ("", "max", "auto"):
        return 1080  # keep memory/disk sane on small hosts
    try:
        return max(144, min(2160, int(q)))
    except ValueError:
        return 1080


def build_opts(kind: str, outdir: str, height: int) -> dict:
    opts = {
        "outtmpl": os.path.join(outdir, "%(title).150B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": False,
    }
    if kind == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        opts["format"] = (
            f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
            f"bv*[height<={height}]+ba/b[height<={height}]/b"
        )
        opts["merge_output_format"] = "mp4"
    if COOKIE_FILE and os.path.isfile(COOKIE_FILE):
        opts["cookiefile"] = COOKIE_FILE
    return opts


def download(url: str, kind: str, height: int):
    """Download into a fresh temp dir. Returns (path, filename, tmpdir)."""
    tmpdir = tempfile.mkdtemp(prefix="yt-")
    try:
        with _slots:
            with yt_dlp.YoutubeDL(build_opts(kind, tmpdir, height)) as ydl:
                ydl.extract_info(url, download=True)
        files = [f for f in os.listdir(tmpdir) if not f.endswith((".part", ".ytdl"))]
        if not files:
            raise RuntimeError("no file produced")
        name = max(files, key=lambda f: os.path.getsize(os.path.join(tmpdir, f)))
        return os.path.join(tmpdir, name), name, tmpdir
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


# ---------- tunnel store ----------

def _sweep():
    now = time.time()
    with _tunnels_lock:
        for tid in [t for t, v in _tunnels.items() if now - v["created"] > TUNNEL_TTL]:
            shutil.rmtree(_tunnels[tid]["dir"], ignore_errors=True)
            del _tunnels[tid]


def _add_tunnel(path: str, name: str, tmpdir: str) -> str:
    _sweep()
    tid = secrets.token_urlsafe(18)
    with _tunnels_lock:
        _tunnels[tid] = {"path": path, "name": name, "dir": tmpdir, "created": time.time()}
    return tid


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    server_version = "youtyers/1.0"

    # -- helpers --

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Accept, Authorization, X-API-Key",
        )
        self.send_header("Access-Control-Expose-Headers", "Content-Disposition, Content-Length")

    def _json(self, code: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code: int, err_code: str):
        self._json(code, {"status": "error", "error": {"code": err_code}})

    def _base_url(self) -> str:
        if PUBLIC_URL:
            return PUBLIC_URL
        proto = self.headers.get("X-Forwarded-Proto", "http").split(",")[0].strip()
        host = self.headers.get("X-Forwarded-Host") or self.headers.get("Host", f"localhost:{PORT}")
        return f"{proto}://{host.split(',')[0].strip()}"

    def _authorized(self, qs: dict) -> bool:
        if not API_KEY:
            return True
        auth = self.headers.get("Authorization", "")
        supplied = ""
        if auth.lower().startswith("api-key "):
            supplied = auth[8:].strip()
        supplied = supplied or self.headers.get("X-API-Key", "") or (qs.get("key") or [""])[0]
        return secrets.compare_digest(supplied, API_KEY)

    def _send_file(self, path: str, name: str):
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(name)}")
        self._cors()
        self.end_headers()
        with open(path, "rb") as fh:
            shutil.copyfileobj(fh, self.wfile)

    # -- verbs --

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path == "/health":
            return self._json(200, {"status": "ok"})

        if parsed.path == "/":
            return self._json(200, {
                "cobalt": {
                    "version": COBALT_VERSION,
                    "url": self._base_url(),
                    "services": SERVICES,
                    "backend": "yt-dlp",
                },
                "git": {"branch": "main", "commit": "unknown", "remote": "youtyers"},
            })

        if parsed.path == "/tunnel":
            tid = (qs.get("id") or [""])[0]
            with _tunnels_lock:
                item = _tunnels.get(tid)
            if not item or time.time() - item["created"] > TUNNEL_TTL or not os.path.exists(item["path"]):
                return self._error(404, "error.api.tunnel.expired")
            return self._send_file(item["path"], item["name"])

        if parsed.path == "/download":
            if not self._authorized(qs):
                return self._error(401, "error.api.auth.key.invalid")
            url = (qs.get("url") or [""])[0].strip()
            kind = (qs.get("type") or ["video"])[0].strip().lower()
            if urlparse(url).scheme not in ("http", "https"):
                return self._error(400, "error.api.link.invalid")
            if kind not in ("video", "audio"):
                return self._error(400, "error.api.invalid_body")
            try:
                path, name, tmpdir = download(url, kind, _height_cap("max"))
            except Exception as e:
                return self._json(502, {"status": "error", "error": {"code": "error.api.fetch.fail"},
                                        "detail": str(e)[:300]})
            try:
                self._send_file(path, name)
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
            return

        return self._error(404, "error.api.not_found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/api/json"):
            return self._error(404, "error.api.not_found")
        if not self._authorized({}):
            return self._error(401, "error.api.auth.key.invalid")

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            return self._error(400, "error.api.invalid_body")

        url = str(body.get("url", "")).strip()
        if urlparse(url).scheme not in ("http", "https"):
            return self._error(400, "error.api.link.invalid")

        mode = str(body.get("downloadMode", "auto")).lower()
        kind = "audio" if mode == "audio" else "video"  # "mute" returns video here
        height = _height_cap(str(body.get("videoQuality", "max")))

        try:
            path, name, tmpdir = download(url, kind, height)
        except Exception as e:
            print(f"download failed for {url}: {e}", flush=True)
            return self._error(502, "error.api.fetch.fail")

        tid = _add_tunnel(path, name, tmpdir)
        return self._json(200, {
            "status": "tunnel",
            "url": f"{self._base_url()}/tunnel?id={tid}",
            "filename": name,
        })

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    print(f"listening on 0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
