"""CSV artifact output that can be deferred by web frontends.

The calculation engine still writes CSV files immediately by default.  A caller
may enter :func:`capture_csv_exports` to retain the completed DataFrames in
memory and serialize them only when the user requests a download.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

import pandas as pd


@dataclass(frozen=True, slots=True)
class _PendingCsv:
    path: Path
    frame: pd.DataFrame
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


@dataclass(slots=True)
class DeferredCsvExports:
    """Completed DataFrames waiting to be serialized as CSV files."""

    _items: dict[Path, _PendingCsv] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def capture(
        self,
        frame: pd.DataFrame,
        path: str | Path,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        resolved_path = Path(path).resolve()
        self._items[resolved_path] = _PendingCsv(
            path=resolved_path,
            # Calculation frames are occasionally extended after an intermediate
            # export.  Keep the exact state that an immediate to_csv call saw.
            frame=frame.copy(deep=True),
            args=args,
            kwargs=dict(kwargs),
        )

    def dataframe(self, path: str | Path) -> pd.DataFrame | None:
        item = self._items.get(Path(path).resolve())
        return None if item is None else item.frame

    def write_all(self) -> tuple[str, ...]:
        """Write every pending CSV once and return the absolute paths."""
        with self._lock:
            for item in self._items.values():
                if item.path.is_file():
                    continue
                item.path.parent.mkdir(parents=True, exist_ok=True)
                item.frame.to_csv(item.path, *item.args, **item.kwargs)
            return tuple(str(path) for path in sorted(self._items))

    def __len__(self) -> int:
        return len(self._items)

    def __deepcopy__(self, memo: dict[int, Any]) -> DeferredCsvExports:
        # Gradio may deepcopy state values when creating a browser session.  The
        # captured frames are immutable after calculation, while the lock itself
        # cannot be copied safely, so the session may share this collection.
        memo[id(self)] = self
        return self


_ACTIVE_EXPORTS: ContextVar[DeferredCsvExports | None] = ContextVar(
    "jjjexperiment_active_csv_exports",
    default=None,
)


@contextmanager
def capture_csv_exports() -> Iterator[DeferredCsvExports]:
    """Capture engine CSV exports without changing normal engine behavior."""
    exports = DeferredCsvExports()
    token = _ACTIVE_EXPORTS.set(exports)
    try:
        yield exports
    finally:
        _ACTIVE_EXPORTS.reset(token)


def write_dataframe_csv(
    frame: pd.DataFrame,
    path: str | Path,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Write now, or capture the DataFrame when a deferred session is active."""
    exports = _ACTIVE_EXPORTS.get()
    if exports is None:
        frame.to_csv(path, *args, **kwargs)
        return
    exports.capture(frame, path, *args, **kwargs)
