"""Bounded supervised subprocesses shared by tasks, CI, and model adapters.

Shell-free; caller chooses credentials and permissions. Not a sandbox. POSIX process
sessions are terminated, including descendants retaining pipes. Deliberately escaped
sessions need container/OS enforcement. Windows uses taskkill /T while the parent is
alive; robust containment on that platform requires a Job Object/container.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from typing import BinaryIO

from .common import finite_number


@dataclass
class ProcessResult:
    status: str
    exit_code: int | None
    stdout: bytes = b''
    stderr: bytes = b''
    reason: str | None = None
    duration_seconds: float = 0
    output_bytes: int = 0


def terminate(process: subprocess.Popen) -> None:
    """Terminate the supervised group, even after its leader has exited on POSIX."""
    if os.name == 'posix':
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        try:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.SubprocessError):
            process.kill()
    if process.poll() is None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def supervise(argv: list[str], *, cwd: Path, timeout: float, env: dict | None = None,
              stdin: bytes | None = None, stop_file: Path | None = None,
              max_output_bytes: int = 2_000_000, log: BinaryIO | None = None) -> ProcessResult:
    if not isinstance(argv, list) or not argv or not isinstance(argv[0], str) or not argv[0]:
        raise ValueError('argv needs a nonempty executable')
    if not all(isinstance(a, str) and '\x00' not in a for a in argv):
        raise ValueError('argv must contain NUL-free strings')
    finite_number(timeout)
    if timeout <= 0 or type(max_output_bytes) is not int or not 1 <= max_output_bytes <= 16_000_000:
        raise ValueError('Invalid execution bounds')
    if stop_file is not None and stop_file.exists():
        return ProcessResult('STOPPED', None, reason='STOPPED')
    start = time.monotonic()
    try:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=os.name == 'posix')
    except OSError as exc:
        return ProcessResult('BLOCKED', None, reason=type(exc).__name__)
    buffers = [bytearray(), bytearray()]
    lock = threading.Lock()
    exceeded = threading.Event()
    read_failed = threading.Event()
    consumed = 0

    def drain(pipe, target):
        nonlocal consumed
        try:
            while True:
                chunk = pipe.read1(8192)
                if not chunk:
                    break
                with lock:
                    available = max(0, max_output_bytes - consumed)
                    kept = chunk[:available]
                    buffers[target].extend(kept)
                    if log is not None:
                        log.write(kept)
                    consumed += len(kept)
                    if len(kept) != len(chunk):
                        exceeded.set()
        except (OSError, ValueError):
            read_failed.set()
        finally:
            pipe.close()

    def send():
        try:
            if stdin is not None:
                process.stdin.write(stdin)
                process.stdin.flush()
        except (OSError, ValueError):
            pass
        finally:
            process.stdin.close()

    readers = [threading.Thread(target=drain, args=(process.stdout, 0), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, 1), daemon=True)]
    writer = threading.Thread(target=send, daemon=True)
    reason = None
    for thread in readers + [writer]:
        thread.start()
    try:
        while True:
            if stop_file is not None and stop_file.exists():
                reason = 'STOPPED'
                break
            if exceeded.is_set():
                reason = 'OUTPUT_LIMIT'
                break
            if time.monotonic() - start >= timeout:
                reason = 'TIMEOUT'
                break
            if process.poll() is not None:
                # Background descendants are not permitted to outlive a managed command.
                terminate(process)
                for thread in readers:
                    thread.join(timeout=1)
                if exceeded.is_set():
                    reason = 'OUTPUT_LIMIT'
                elif any(t.is_alive() for t in readers):
                    reason = 'DESCENDANT_PIPE_OPEN'
                elif read_failed.is_set():
                    reason = 'OUTPUT_READ_FAILED'
                break
            time.sleep(.025)
    finally:
        terminate(process)
        for thread in readers + [writer]:
            thread.join(timeout=1)
    status = ('STOPPED' if reason == 'STOPPED' else
              'FAIL' if reason or process.returncode != 0 else 'PASS')
    return ProcessResult(status, process.returncode, bytes(buffers[0]), bytes(buffers[1]),
                         reason, round(time.monotonic() - start, 4), consumed)
