"""
Dashboard Server — Sirve el frontend React y la API de datos.

Uso:
  python dashboard/dashboard_server.py

Sirve:
  - GET /api/dashboard → data/dashboard_data.json
  - Static files del build de React
  - En dev: proxy a Vite (puerto 5173)
"""

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_FILE = "data/dashboard_data.json"
DASHBOARD_DIR = Path(__file__).parent / "dist"
PORT = 8050


class DashboardHandler(SimpleHTTPRequestHandler):
    """Sirve la API de datos y el frontend build"""

    def do_GET(self):
        if self.path == "/api/dashboard":
            self._serve_dashboard_data()
        elif self.path.startswith("/assets/"):
            self._serve_static()
        else:
            self._serve_index()

    def _serve_dashboard_data(self):
        data_file = Path(os.getcwd()) / DATA_FILE
        if not data_file.exists():
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "total": {
                    "balance_inicial": 0, "balance_actual": 0,
                    "pnl_total": 0, "pnl_pct": 0,
                    "total_trades": 0, "win_rate": 0,
                    "agentes_activos": 0, "total_agentes": 0,
                },
                "agents": [],
                "status": "no_data",
            }).encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(data_file) as f:
            self.wfile.write(f.read().encode())

    def _serve_static(self):
        filepath = DASHBOARD_DIR / self.path.lstrip("/")
        if not filepath.exists():
            self.send_response(404)
            self.end_headers()
            return
        ext = filepath.suffix
        content_types = {
            ".js": "application/javascript",
            ".css": "text/css",
            ".html": "text/html",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".json": "application/json",
        }
        self.send_response(200)
        self.send_header("Content-Type", content_types.get(ext, "application/octet-stream"))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())

    def _serve_index(self):
        index = DASHBOARD_DIR / "index.html"
        if not index.exists():
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>PolypastaBot Dashboard</h1><p>Build the dashboard first: <code>cd dashboard && npm run build</code></p></body></html>")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with open(index) as f:
            self.wfile.write(f.read().encode())

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            print(f"📡 {args[0]}")
        elif "/assets/" not in str(args[0]):
            print(f"🌐 {args[0]}")


def run_server(port: int = PORT):
    print(f"\n{'='*50}")
    print(f"📊 PolypastaBot Dashboard")
    print(f"{'='*50}")
    print(f"\n🔗 http://localhost:{port}")
    print(f"📡 API: http://localhost:{port}/api/dashboard")
    print(f"\n⚠️  Asegúrate de que el bot esté corriendo para ver datos en vivo.")
    print(f"{'='*50}\n")

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.server_close()


if __name__ == "__main__":
    run_server()