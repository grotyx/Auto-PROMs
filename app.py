#!/usr/bin/env python3
"""
Auto Spine Survey v2.1.1 — NiceGUI entry point

Runs as a native desktop window via pywebview (no separate browser needed).
Usage:
    python app.py
"""

import logging
import sys
import time
import traceback
from pathlib import Path

_LOG_DIR = Path(__file__).parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_STARTUP_LOG = _LOG_DIR / "startup.log"

logging.basicConfig(
    filename=str(_STARTUP_LOG),
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)

try:
    from nicegui import app, ui
except Exception as exc:
    logging.critical("NiceGUI import failed: %s", exc, exc_info=True)
    print(f"[FATAL] NiceGUI를 불러올 수 없습니다: {exc}")
    print(f"pip install nicegui pywebview 실행 후 다시 시도하세요.")
    print(f"상세 로그: {_STARTUP_LOG}")
    sys.exit(1)

# Serve gui_ng/ directory as /static so styles.css is accessible
_GUI_NG_DIR = Path(__file__).parent / "gui_ng"
app.add_static_files("/static", str(_GUI_NG_DIR))


@ui.page("/")
def main_page() -> None:
    # Cache-bust: append timestamp so pywebview never serves stale CSS
    ui.add_head_html(
        f'<link rel="stylesheet" href="/static/styles.css?v={int(time.time())}">'
    )
    from gui_ng.main_page import build_page
    build_page()


if __name__ == "__main__":
    try:
        logging.info("Starting Auto Spine Survey (native=True)")
        ui.run(
            native=True,
            window_size=(640, 820),
            title="Auto Spine Survey",
            reload=False,
        )
    except Exception as exc:
        logging.critical("Startup failed: %s", exc, exc_info=True)
        # Fallback: try browser mode if native window fails (e.g. no WebView2)
        print(f"[WARNING] 네이티브 창 실행 실패: {exc}")
        print("브라우저 모드로 재시도합니다...")
        logging.info("Retrying in browser mode (native=False)")
        try:
            ui.run(
                native=False,
                window_size=(640, 820),
                title="Auto Spine Survey",
                reload=False,
            )
        except Exception as exc2:
            logging.critical("Browser fallback also failed: %s", exc2, exc_info=True)
            print(f"[FATAL] 실행 실패: {exc2}")
            print(f"상세 로그: {_STARTUP_LOG}")
            sys.exit(1)
