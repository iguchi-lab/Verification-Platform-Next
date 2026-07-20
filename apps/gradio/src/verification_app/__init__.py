from __future__ import annotations

from typing import Any


def build_app() -> Any:
    from .form_app import build_app as _build_app

    return _build_app()


__all__ = ["build_app"]
