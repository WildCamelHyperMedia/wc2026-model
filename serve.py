#!/usr/bin/env python3
"""
Replit / any-host runner: serves the dashboard on port 8080 and keeps the
watcher running in the background (rebuilds whenever a match finishes).

    python3 serve.py
"""
import http.server
import os
import socketserver
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
PORT = int(os.environ.get("PORT", 8080))


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/wc2026_dashboard.html"
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # always fresh
        super().end_headers()

    def log_message(self, *a):
        pass


def watcher():
    import update
    # initial build if missing
    if not os.path.exists("wc2026_dashboard.html"):
        update.run_once()
    while True:
        try:
            sig, _ = update.feed_signature()
            if sig is not None and sig != update.cached_signature():
                print("⚽ new result — rebuilding")
                update.run_once()
        except Exception as e:
            print("watch error:", e)
        time.sleep(15 * 60)


threading.Thread(target=watcher, daemon=True).start()
print(f"Serving dashboard on http://0.0.0.0:{PORT} (watcher active, 15 min)")
with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), Handler) as httpd:
    httpd.serve_forever()
