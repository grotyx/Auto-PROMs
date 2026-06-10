#!/usr/bin/env python3
"""
Auto Spine Survey v2.2.3 — NiceGUI entry point

Runs as a native desktop window via pywebview (no separate browser needed).
Usage:
    python app.py
"""

import logging
import sys
import time
import traceback
from pathlib import Path

# Frozen exe: logs next to the .exe; dev mode: project root
if getattr(sys, "frozen", False):
    _APP_ROOT = Path(sys.executable).parent
else:
    _APP_ROOT = Path(__file__).resolve().parent

_LOG_DIR = _APP_ROOT / "logs"
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

# Serve only styles.css (never the whole gui_ng/ dir — that would expose .py sources)
if getattr(sys, "frozen", False):
    _GUI_NG_DIR = Path(getattr(sys, "_MEIPASS", "")) / "gui_ng"
else:
    _GUI_NG_DIR = Path(__file__).resolve().parent / "gui_ng"
app.add_static_file(local_file=str(_GUI_NG_DIR / "styles.css"), url_path="/static/styles.css")


def _clean_leftover_data() -> None:
    """Remove patient data left behind by a previous crashed run."""
    import shutil
    for folder in ("temp_images", "uploaded_pdfs"):
        target = _APP_ROOT / folder
        if not target.exists():
            continue
        for item in target.iterdir():
            if item.name == ".gitkeep":
                continue
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            except Exception as exc:
                logging.warning("Could not clean %s: %s", item, exc)


@ui.page("/")
def main_page() -> None:
    # Cache-bust: append timestamp so pywebview never serves stale CSS
    ui.add_head_html(
        f'<link rel="stylesheet" href="/static/styles.css?v={int(time.time())}">'
    )
    from gui_ng.main_page import build_page
    build_page()


if __name__ == "__main__":
    _clean_leftover_data()
    try:
        logging.info("Starting Auto Spine Survey (native=True)")
        ui.run(
            native=True,
            host="127.0.0.1",
            window_size=(640, 820),
            title="Auto Spine Survey",
            reload=False,
        )
    except Exception as exc:
        logging.critical("Startup failed: %s", exc, exc_info=True)
        # Fallback: try browser mode if native window fails (e.g. no WebView2).
        # host must stay 127.0.0.1 — NiceGUI defaults to 0.0.0.0 when native=False,
        # which would expose the app (and patient data) to the whole LAN.
        print(f"[WARNING] 네이티브 창 실행 실패: {exc}")
        print("브라우저 모드로 재시도합니다...")
        logging.info("Retrying in browser mode (native=False)")
        try:
            ui.run(
                native=False,
                host="127.0.0.1",
                window_size=(640, 820),
                title="Auto Spine Survey",
                reload=False,
            )
        except Exception as exc2:
            logging.critical("Browser fallback also failed: %s", exc2, exc_info=True)
            print(f"[FATAL] 실행 실패: {exc2}")
            print(f"상세 로그: {_STARTUP_LOG}")
            sys.exit(1)
