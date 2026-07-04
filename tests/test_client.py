import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from uefn_mcp.client import UEFNClient, UEFNListenerError


class FakeListener(BaseHTTPRequestHandler):
    response_mode = "success"

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode())
        if self.response_mode == "error":
            payload = {"success": False, "error": "boom", "traceback": "trace"}
        else:
            payload = {"success": True, "result": {"command": body["command"], "params": body["params"]}}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, fmt, *args):
        pass


class ClientTests(unittest.TestCase):
    def setUp(self):
        FakeListener.response_mode = "success"
        self.server = HTTPServer(("127.0.0.1", 0), FakeListener)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()

    def test_discovers_and_sends_command(self):
        client = UEFNClient(default_port=self.port, max_port=self.port)
        result = client.send_command("ping", {"x": 1})
        self.assertEqual(result["command"], "ping")
        self.assertEqual(result["params"], {"x": 1})
        self.assertEqual(client.discovered_port, self.port)

    def test_listener_error_raises(self):
        FakeListener.response_mode = "error"
        client = UEFNClient(default_port=self.port, max_port=self.port)
        with self.assertRaises(UEFNListenerError):
            client.send_command("bad")

    def test_missing_listener_raises_connection_error(self):
        client = UEFNClient(default_port=self.port + 1, max_port=self.port + 1)
        with self.assertRaises(ConnectionError):
            client.discover_port()


if __name__ == "__main__":
    unittest.main()
