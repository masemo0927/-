#!/usr/bin/env python3
"""
법제처 API 로컬 프록시 서버
- Claude Code 환경에서 law.go.kr 접근이 차단될 때 사용
- 이 스크립트를 별도 터미널에서 실행: python law_proxy.py
- Claude Code는 localhost:8899를 통해 법제처 API에 접근
"""

import http.server
import urllib.request
import urllib.parse
import os
import sys

PROXY_PORT = 8899
LAW_API_BASE = "https://www.law.go.kr"


class LawProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[프록시] {self.address_string()} - {format % args}")

    def do_GET(self):
        # /DRF/... → www.law.go.kr/DRF/...
        target_url = LAW_API_BASE + self.path
        print(f"[프록시] 요청: {target_url[:80]}...")

        try:
            # 프록시 없이 직접 접속
            env_backup = {}
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                if key in os.environ:
                    env_backup[key] = os.environ.pop(key)

            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; LawProxy/1.0)",
                    "Accept": "application/xml, text/xml, */*",
                }
            )
            # 프록시 없이 직접 opener 생성
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=20) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "application/xml")

            # 환경변수 복원
            os.environ.update(env_backup)

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            print(f"[프록시] 성공 ({len(data)} bytes)")

        except Exception as e:
            os.environ.update(env_backup)
            print(f"[프록시] 오류: {e}")
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"프록시 오류: {e}".encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PROXY_PORT
    server = http.server.HTTPServer(("127.0.0.1", port), LawProxyHandler)
    print(f"=" * 50)
    print(f"  법제처 API 로컬 프록시 서버")
    print(f"  http://localhost:{port} 에서 실행 중")
    print(f"  종료: Ctrl+C")
    print(f"=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n프록시 서버를 종료합니다.")
