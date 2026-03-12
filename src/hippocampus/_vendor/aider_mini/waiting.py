"""Small terminal spinner used by the embedded RepoMap adapter."""

from __future__ import annotations

import sys
import time


class Spinner:
    """Low-overhead spinner that only renders when stdout is interactive."""

    _frames = ("|", "/", "-", "\\")

    def __init__(self, text: str):
        self.text = text
        self._visible = False
        self._isatty = sys.stdout.isatty()
        self._frame_index = 0
        self._last_update = 0.0
        self._line_width = 0
        self._start_time = time.time()

    def step(self, text: str | None = None) -> None:
        if text is not None:
            self.text = text
        if not self._isatty:
            return

        now = time.time()
        if not self._visible and now - self._start_time < 0.5:
            return
        if now - self._last_update < 0.1:
            return

        self._visible = True
        self._last_update = now
        frame = self._frames[self._frame_index]
        self._frame_index = (self._frame_index + 1) % len(self._frames)
        line = f"{frame} {self.text}"
        padding = " " * max(0, self._line_width - len(line))
        sys.stdout.write(f"\r{line}{padding}")
        sys.stdout.flush()
        self._line_width = len(line)

    def end(self) -> None:
        if not self._visible or not self._isatty:
            return
        sys.stdout.write("\r" + (" " * self._line_width) + "\r")
        sys.stdout.flush()
        self._visible = False
