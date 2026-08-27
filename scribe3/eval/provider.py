"""Injected complete_fn switch. Default coding; hermes only when named."""
from __future__ import annotations


def complete_for_provider(name: str = "coding"):
    """Return a live complete_fn. coding is inject-only so we never silently bill tonglu."""
    key = (name or "coding").strip().lower()
    if key in ("hermes", "tonglu"):
        from scribe3.eval.run_r1 import live_complete

        return live_complete
    if key == "coding":
        raise SystemExit(
            "provider=coding: inject complete_fn in-process; refusing to default to hermes"
        )
    raise SystemExit(f"unknown provider {key}")
