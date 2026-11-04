"""Tiny download API backed by yt-dlp (replaces cobalt).

Endpoints:
  GET /health
  GET /download?url=<video url>&type=video|audio
      -> returns the downloaded file as an attachment.

Env vars:
  PORT         listen port (default 9000)
  API_KEY      if set, requests must send header "X-API-Key: <key>" or ?key=<key>
  COOKIE_FILE  optional path to a Netscape-format cookies.txt (helps with YouTube)
"""

import os
import shutil
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import yt_dlp

PORT = int(os.environ.get("PORT", "9000"))
API_KEY = os.environ.get("API_KEY", "")
COOKIE_FILE = os.environ.get("COOKIE_FILE", "")


def build_opts(kind: str, outdir: str) -> dict:
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
        opts["format"] = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
        opts["merge_output_format"] = "mp4"
    if COOKIE_FILE and os.path.isfile(COOKIE_FILE):
        opts["cookiefile"] = COOKIE_FILE
    return opts


def download(url: str, kind: str):
    """Download into a temp dir. Returns (path, filename, tmpdir)."""
    tmpdir = tempfile.mkdtemp(prefix="yt-")
    try:
        with yt_dlp.YoutubeDL(build_opts(kind, tmpdir)) as ydl:
            ydl.extract_info(url, download=True)
        files = [f for f in os.listdir(tmpdir) if not f.endswith((".part", ".ytdl"))]
        if not files:
            raise RuntimeError("no file produced")
        name = max(files, key=lambda f: os.path.getsize(os.path.join(tmpdir, f)))
        return os.path.join(tmpdir, name), name, tmpdir
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise


class Handler(BaseHTTPRequestHandler):
    server_version = "youtyers/1.0"

    def _send_json(self, code: int, obj: dict):
        import json

        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self, qs: dict) -> bool:
        if not API_KEY:
            return True
        key = self.headers.get("X-API-Key") or (qs.get("key") or [""])[0]
        return key == API_KEY

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path == "/health":
            return self._send_json(200, {"status": "ok"})

        if parsed.path != "/download":
            return self._send_json(404, {"error": "not found"})

        if not self._authorized(qs):
            return self._send_json(401, {"error": "unauthorized"})

        url = (qs.get("url") or [""])[0].strip()
        kind = (qs.get("type") or ["video"])[0].strip().lower()
        if urlparse(url).scheme not in ("http", "https"):
            return self._send_json(400, {"error": "url must be http(s)"})
        if kind not in ("video", "audio"):
            return self._send_json(400, {"error": "type must be video or audio"})

        try:
            path, name, tmpdir = download(url, kind)
        except Exception as e:  # yt-dlp raises DownloadError and friends
            return self._send_json(502, {"error": "download failed", "detail": str(e)[:500]})

        try:
            from urllib.parse import quote

            size = os.path.getsize(path)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header(
                "Content-Disposition", f"attachment; filename*=UTF-8''{quote(name)}"
            )
            self.end_headers()
            with open(path, "rb") as fh:
                shutil.copyfileobj(fh, self.wfile)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    print(f"listening on 0.0.0.0:{PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
