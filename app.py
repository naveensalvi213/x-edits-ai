import os
import sys
import time
import json
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

import config
from main import run_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Render_App")

monitor_lock = threading.Lock()
last_run_time = "Never"
last_run_status = "Initialized"
run_count = 0

def background_monitor_worker():
    global last_run_time, last_run_status, run_count
    logger.info("Background monitor worker started. Waiting 10s for server warm-up...")
    time.sleep(10)
    
    while True:
        try:
            logger.info("Starting scheduled monitor check...")
            with monitor_lock:
                last_run_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                run_monitor()
                run_count += 1
                last_run_status = "Success"
        except Exception as e:
            logger.error(f"Error during monitor check: {e}", exc_info=True)
            last_run_status = f"Error: {str(e)}"
        
        logger.info("Monitor cycle finished. Next run in 300 seconds (5 minutes)...")
        time.sleep(300)

class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_GET(self):
        global last_run_time, last_run_status, run_count
        
        if self.path in ["/", "/health", "/ping"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {
                "status": "healthy",
                "service": "X (Twitter) Hiring Post Monitor 24/7",
                "uptime_keepalive": "active",
                "last_run": last_run_time,
                "last_status": last_run_status,
                "total_runs": run_count,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            }
            self.wfile.write(json.dumps(response_data, indent=2).encode("utf-8"))
            logger.info(f"Keepalive ping received from {self.client_address[0]}")
            
        elif self.path in ["/run", "/trigger"]:
            if monitor_lock.locked():
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "busy", "message": "Run already in progress"}).encode("utf-8"))
            else:
                threading.Thread(target=run_monitor, daemon=True).start()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "triggered", "message": "Monitor run started in background"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, HealthHandler)
    logger.info(f"Render HTTP server listening on port {port}...")

    worker_thread = threading.Thread(target=background_monitor_worker, daemon=True)
    worker_thread.start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
