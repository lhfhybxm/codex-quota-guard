from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .redaction import redact
from .security import (
    is_allowed_incoming_notification,
    require_allowed_outgoing_notification,
    require_allowed_request,
)


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RpcError(RuntimeError):
    code: int | str | None
    message: str
    retry_after_seconds: float | None = None

    def __str__(self) -> str:
        return f"App Server RPC error {self.code}: {redact(self.message)}"


class RpcTimeoutError(TimeoutError):
    pass


class AppServerTransport:
    """Strict, newline-delimited JSON transport for read-only quota RPCs."""

    def __init__(
        self,
        executable: str = "codex",
        timeout_seconds: float = 20.0,
        notification_callback: Callable[[str, dict[str, Any]], None] | None = None,
        process_factory: Callable[..., subprocess.Popen[str]] = subprocess.Popen,
    ) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds
        self.notification_callback = notification_callback
        self._process_factory = process_factory
        self._process: subprocess.Popen[str] | None = None
        self._pending: dict[str, queue.Queue[dict[str, Any]]] = {}
        self._pending_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._next_id = 1
        self._reader: threading.Thread | None = None
        self._stderr_reader: threading.Thread | None = None
        self._closed = threading.Event()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        if self.running:
            return
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._closed.clear()
        self._process = self._process_factory(
            [self.executable, "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=False,
            creationflags=creationflags,
        )
        self._reader = threading.Thread(
            target=self._read_stdout, name="codex-app-server-rpc", daemon=True
        )
        self._stderr_reader = threading.Thread(
            target=self._read_stderr, name="codex-app-server-stderr", daemon=True
        )
        self._reader.start()
        self._stderr_reader.start()
        self.request(
            "initialize",
            {
                "clientInfo": {"name": "codex-quota-guard", "version": "0.1.0"},
                "capabilities": {"experimentalApi": True},
            },
        )
        self.notify("initialized")

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        require_allowed_request(method)
        if not self.running and method != "initialize":
            self.start()
        if not self.running:
            raise ConnectionError("Codex App Server is not running")

        with self._pending_lock:
            request_id = str(self._next_id)
            self._next_id += 1
            response_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
            self._pending[request_id] = response_queue

        message: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        try:
            self._write(message)
            try:
                response = response_queue.get(
                    timeout=timeout_seconds or self.timeout_seconds
                )
            except queue.Empty as exc:
                raise RpcTimeoutError(f"Timed out waiting for {method}") from exc
            if "error" in response:
                error = response.get("error") or {}
                raise RpcError(error.get("code"), redact(error.get("message", "Unknown error")))
            result = response.get("result")
            if not isinstance(result, dict):
                raise RpcError("malformed", "RPC result was not an object")
            return result
        finally:
            with self._pending_lock:
                self._pending.pop(request_id, None)

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        require_allowed_outgoing_notification(method)
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        self._write(message)

    def _write(self, message: dict[str, Any]) -> None:
        process = self._process
        if process is None or process.stdin is None or process.poll() is not None:
            raise ConnectionError("Codex App Server stdin is unavailable")
        payload = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
        with self._write_lock:
            process.stdin.write(payload + "\n")
            process.stdin.flush()

    def _read_stdout(self) -> None:
        process = self._process
        if process is None or process.stdout is None:
            return
        try:
            for line in process.stdout:
                try:
                    message = json.loads(line)
                except (TypeError, json.JSONDecodeError):
                    LOGGER.warning("Ignored malformed App Server output")
                    continue
                request_id = message.get("id")
                if request_id is not None:
                    with self._pending_lock:
                        target = self._pending.get(str(request_id))
                    if target is not None:
                        target.put(message)
                    continue
                method = message.get("method")
                params = message.get("params")
                if (
                    isinstance(method, str)
                    and isinstance(params, dict)
                    and is_allowed_incoming_notification(method)
                    and self.notification_callback is not None
                ):
                    try:
                        self.notification_callback(method, params)
                    except Exception as exc:  # callback failures must not kill RPC I/O
                        LOGGER.warning("Notification callback failed: %s", redact(exc))
        finally:
            self._closed.set()
            self._fail_pending("App Server stdout closed")

    def _read_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        for line in process.stderr:
            if line.strip():
                LOGGER.debug("Codex App Server: %s", redact(line.strip()))

    def _fail_pending(self, message: str) -> None:
        with self._pending_lock:
            targets = list(self._pending.values())
        for target in targets:
            try:
                target.put_nowait(
                    {"error": {"code": "connection_closed", "message": message}}
                )
            except queue.Full:
                pass

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin:
                process.stdin.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        finally:
            self._closed.set()

    def __enter__(self) -> "AppServerTransport":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
