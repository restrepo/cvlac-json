"""Progress bar on standard error for the command line (standard library only).

The work is a list of named stages (download, parse, each Scienti request, ROR...). Some stages are
one long request, so a background thread redraws the line every 0.1 s with a spinner and the elapsed
time, and the bar never looks frozen. It is drawn only when the stream is a terminal.
"""

import os
import shutil
import sys
import threading
import time


class Progress:
    """Callable progress reporter: ``progress(stage, done=None, total=None)``.

    stages: ordered stage names. Calling it with a stage name moves the bar to that stage; ``done`` and
    ``total`` give the advance inside the stage (e.g. ROR lookup 3 of 7). Unknown names are ignored.
    """

    FRAMES_UNICODE = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    FRAMES_ASCII = "|/-\\"

    def __init__(self, stages, stream=None, enabled=None, interval=0.1):
        self.stages = list(stages)
        self.stream = stream if stream is not None else sys.stderr
        if enabled is None:
            enabled = _is_terminal(self.stream)
        self.enabled = bool(enabled) and bool(self.stages)
        self.interval = interval
        unicode_ok = _can_encode(self.stream, "█░⠋")
        self.frames = self.FRAMES_UNICODE if unicode_ok else self.FRAMES_ASCII
        self.fill, self.empty = ("█", "░") if unicode_ok else ("#", "-")
        self.index, self.done, self.total = 0, None, None
        self.t0 = time.monotonic()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._frame = 0
        self._shown = False

    # -- public API
    def __call__(self, stage, done=None, total=None):
        if stage in self.stages:
            with self._lock:
                self.index = self.stages.index(stage)
                self.done, self.total = done, total
        self._draw()

    def start(self):
        self.t0 = time.monotonic()
        if self.enabled and self._thread is None:
            self._thread = threading.Thread(target=self._tick, name="cvlac-json-progress", daemon=True)
            self._thread.start()
        self._draw()
        return self

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        self._clear()

    def write(self, message):
        """Print a message line without breaking the bar (used for log messages)."""
        with self._lock:
            if self.enabled and self._shown:
                self.stream.write("\r\x1b[2K")
            self.stream.write(f"{message}\n")
            self.stream.flush()
        self._draw()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.close()
        return False

    # -- drawing
    def fraction(self):
        n = len(self.stages)
        if not n:
            return 1.0
        inner = (self.done / self.total) if self.total else 0.0
        return min(1.0, (self.index + max(0.0, min(1.0, inner))) / n)

    def render(self, width=80):
        """The bar as one line of at most ``width`` characters."""
        elapsed = time.monotonic() - self.t0
        frac = self.fraction()
        label = self.stages[self.index] if self.stages else ""
        if self.total:
            label += f" {self.done}/{self.total}"
        spin = self.frames[self._frame % len(self.frames)]
        right = f" {frac * 100:3.0f}% {self.index + 1}/{len(self.stages)} {label} {_clock(elapsed)}"
        barw = max(10, min(30, width - len(right) - 4))
        full = round(frac * barw)
        line = f"{spin} {self.fill * full}{self.empty * (barw - full)}{right}"
        return line[: max(1, width - 1)]

    def _draw(self):
        if not self.enabled:
            return
        with self._lock:
            width = shutil.get_terminal_size((80, 20)).columns
            self.stream.write("\r\x1b[2K" + self.render(width))
            self.stream.flush()
            self._shown = True

    def _clear(self):
        if self.enabled and self._shown:
            with self._lock:
                self.stream.write("\r\x1b[2K")
                self.stream.flush()
                self._shown = False

    def _tick(self):
        while not self._stop.wait(self.interval):
            self._frame += 1
            self._draw()


def null_progress(stage, done=None, total=None):
    """Progress callback that does nothing (library use)."""


def _is_terminal(stream):
    if os.environ.get("TERM") == "dumb":
        return False
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
        return False


def _can_encode(stream, chars):
    try:
        chars.encode(getattr(stream, "encoding", None) or "ascii")
        return True
    except (LookupError, UnicodeEncodeError):
        return False


def _clock(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}" if m else f"{seconds:4.1f}s"
