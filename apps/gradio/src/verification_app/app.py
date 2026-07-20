"""Backward-compatible imports for the Phase 3 form application."""

from .form_app import build_app, main

__all__ = ["build_app", "main"]


if __name__ == "__main__":
    main()
