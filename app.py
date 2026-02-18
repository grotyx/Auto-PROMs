#!/usr/bin/env python3
"""
Auto Spine Survey v2.1 — NiceGUI entry point

Runs as a native desktop window via pywebview (no separate browser needed).
Usage:
    python app.py
"""

from pathlib import Path

from nicegui import app, ui

# Serve gui_ng/ directory as /static so styles.css is accessible
_GUI_NG_DIR = Path(__file__).parent / "gui_ng"
app.add_static_files("/static", str(_GUI_NG_DIR))


@ui.page("/")
def main_page() -> None:
    ui.add_head_html('<link rel="stylesheet" href="/static/styles.css">')
    from gui_ng.main_page import build_page
    build_page()


if __name__ == "__main__":
    ui.run(
        native=True,
        window_size=(900, 820),
        title="Auto Spine Survey v2.1",
        reload=False,
    )
