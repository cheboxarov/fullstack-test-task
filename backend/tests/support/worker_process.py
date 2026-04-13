import os
import signal
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
READY_MARKERS = (
    "ready",
    "mingle: all alone",
    "connected to redis",
)


@dataclass
class WorkerHandle:
    process: subprocess.Popen[str]
    _lines: list[str] = field(default_factory=list)
    _reader: threading.Thread | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add_line(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)

    def output(self) -> str:
        with self._lock:
            return "".join(self._lines)

    def stop(self, timeout: float = 10.0) -> None:
        if self.process.poll() is not None:
            return

        self.process.send_signal(signal.SIGTERM)
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)


def _reader_loop(handle: WorkerHandle) -> None:
    assert handle.process.stdout is not None
    for line in handle.process.stdout:
        handle.add_line(line)


def start_worker(
    *, env: dict[str, str] | None = None, timeout: float = 20.0
) -> WorkerHandle:
    worker_env = os.environ.copy()
    if env:
        worker_env.update(env)

    command = [
        "uv",
        "run",
        "celery",
        "-A",
        "src.tasks.celery_app",
        "worker",
        "-l",
        "info",
        "--pool=solo",
    ]

    process = subprocess.Popen(
        command,
        cwd=BACKEND_DIR,
        env=worker_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    handle = WorkerHandle(process=process)
    reader = threading.Thread(target=_reader_loop, args=(handle,), daemon=True)
    handle._reader = reader
    reader.start()

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"Celery worker exited during startup:\n{handle.output()}"
            )

        lowered = handle.output().lower()
        if any(marker in lowered for marker in READY_MARKERS):
            return handle

        time.sleep(0.2)

    handle.stop()
    raise TimeoutError(
        f"Timed out waiting for Celery worker readiness:\n{handle.output()}"
    )


def stop_worker(handle: WorkerHandle, *, timeout: float = 10.0) -> None:
    handle.stop(timeout=timeout)


@contextmanager
def running_worker(
    *, env: dict[str, str] | None = None, timeout: float = 20.0
) -> Iterator[WorkerHandle]:
    handle = start_worker(env=env, timeout=timeout)
    try:
        yield handle
    finally:
        stop_worker(handle)
