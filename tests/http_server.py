"""Serveur HTTP local pour tester le téléchargement : ETag, Last-Modified, 304, pannes."""

import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeServer:
    def __init__(self):
        self.files: dict[str, bytes] = {}
        self.requests: list[tuple[str, dict]] = []  # (chemin, en-têtes conditionnels reçus)
        self.etags = True  # False : le serveur ne fournit aucun validateur
        self.status: int | None = None  # force un code d'erreur (ex. 503)
        self.truncate = False  # annonce plus d'octets qu'il n'en envoie
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                conditional = {
                    k: v for k, v in self.headers.items() if k in ("If-None-Match", "If-Modified-Since")
                }
                outer.requests.append((self.path, conditional))
                if outer.status:
                    self.send_response(outer.status)
                    self.end_headers()
                    return
                body = outer.files.get(self.path.split("?")[0])
                if body is None:
                    self.send_response(404)
                    self.end_headers()
                    return
                etag = f'"{hashlib.md5(body).hexdigest()}"'
                if outer.etags and self.headers.get("If-None-Match") == etag:
                    self.send_response(304)
                    self.end_headers()
                    return
                self.send_response(200)
                if outer.etags:
                    self.send_header("ETag", etag)
                    self.send_header("Last-Modified", "Mon, 04 May 2026 10:08:20 GMT")
                self.send_header("Content-Length", str(len(body) + (10 if outer.truncate else 0)))
                self.end_headers()
                self.wfile.write(body)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base_url = f"http://127.0.0.1:{self._httpd.server_port}"
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def url(self, path: str) -> str:
        return self.base_url + path

    def count(self, path: str) -> int:
        return sum(1 for p, _ in self.requests if p.split("?")[0] == path)

    def close(self):
        self._httpd.shutdown()
        self._httpd.server_close()
