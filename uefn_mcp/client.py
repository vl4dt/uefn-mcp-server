"""HTTP client for the UEFN in-editor listener."""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_PORT = int(os.environ.get("UEFN_MCP_PORT", "8765"))
MAX_PORT = int(os.environ.get("UEFN_MCP_MAX_PORT", "8770"))
REQUEST_TIMEOUT = float(os.environ.get("UEFN_MCP_TIMEOUT", "30.0"))
HEARTBEAT_INTERVAL = float(os.environ.get("UEFN_MCP_HEARTBEAT_INTERVAL", "10.0"))


class UEFNListenerError(RuntimeError):
    """Raised when the UEFN listener reports a command failure."""


@dataclass
class UEFNClient:
    """Small JSON-over-HTTP client for the UEFN listener."""

    default_port: int = DEFAULT_PORT
    max_port: int = MAX_PORT
    request_timeout: float = REQUEST_TIMEOUT
    host: str = "127.0.0.1"
    discovered_port: int | None = None

    def set_port(self, port: int) -> None:
        self.discovered_port = port

    def ping_port(self, port: int) -> bool:
        try:
            req = urllib.request.Request(f"http://{self.host}:{port}", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                body = json.loads(resp.read().decode())
                return body.get("status") == "ok"
        except Exception:
            return False

    def discover_port(self) -> int:
        if self.discovered_port is not None:
            if self.ping_port(self.discovered_port):
                return self.discovered_port
            self.discovered_port = None

        for port in range(self.default_port, self.max_port + 1):
            if self.ping_port(port):
                self.discovered_port = port
                return port

        raise ConnectionError(
            f"UEFN listener not found on ports {self.default_port}-{self.max_port}. "
            'Start it in UEFN with: py "path/to/uefn_listener.py"'
        )

    def send_command(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        port = self.discover_port()
        payload = json.dumps({"command": command, "params": params or {}}).encode()
        req = urllib.request.Request(
            f"http://{self.host}:{port}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout or self.request_timeout) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            if self.discovered_port is not None:
                self.discovered_port = None
                return self.send_command(command, params, timeout)
            raise ConnectionError(
                'UEFN listener is not running. Start it in UEFN with: py "path/to/uefn_listener.py"'
            ) from exc
        except Exception as exc:
            if "timed out" in str(exc).lower():
                raise TimeoutError(f"Command '{command}' timed out after {timeout or self.request_timeout}s") from exc
            raise

        if not body.get("success", False):
            error_msg = body.get("error", "Unknown error")
            traceback_text = body.get("traceback", "")
            raise UEFNListenerError(f"UEFN command '{command}' failed: {error_msg}\n{traceback_text}".strip())

        return body.get("result", {})

    def check_connection(self) -> str:
        try:
            port = self.discover_port()
            return f"Connected to UEFN on port {port}"
        except ConnectionError:
            return "NOT CONNECTED - UEFN listener is not running"
        except Exception as exc:
            return f"Connection error: {exc}"

    def heartbeat_once(self) -> None:
        port = self.discover_port()
        req = urllib.request.Request(f"http://{self.host}:{port}", method="GET")
        urllib.request.urlopen(req, timeout=2.0).close()


def start_heartbeat(client: UEFNClient, interval: float = HEARTBEAT_INTERVAL) -> threading.Thread:
    """Start a daemon heartbeat thread so the listener can show client status."""

    def loop() -> None:
        time.sleep(3.0)
        while True:
            try:
                client.heartbeat_once()
            except Exception:
                pass
            time.sleep(interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread

