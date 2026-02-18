"""
Auto Spine Survey v2.1 - Main Page (NiceGUI)
Migrated from CustomTkinter gui/main_window.py to NiceGUI.
"""

import asyncio
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from nicegui import app, run, ui

from core.config import ConfigManager, load_config

# ---------------------------------------------------------------------------
# Shared state: background thread writes here, UI timer reads it.
# ---------------------------------------------------------------------------
_state: Dict = {
    "is_processing": False,
    "stop_requested": False,
    "progress": 0.0,
    "current_file": "\ub300\uae30 \uc911...",
    "page_detail": "0 / 0 \ud398\uc774\uc9c0 \uc644\ub8cc",
    "log_lines": [],
    "result": None,       # {"output_file": str, "count": int}
    "error": None,
    "processed_files": set(),
    "_log_last_len": 0,
    "_last_poll_processing": False,
}

_ui: Dict = {}  # UI element references
_log_visible: List[bool] = [False]  # track log panel visibility


# ===================================================================
# Public entry point - called from @ui.page('/')
# ===================================================================

def build_page() -> None:
    """Build the entire main page layout."""
    pdf_files: List[str] = []
    file_card_elements: Dict[str, object] = {}

    with ui.column().classes('w-full max-w-3xl mx-auto gap-3 p-4'):
        _build_header()
        _build_drop_zone(pdf_files, file_card_elements)
        _build_file_list(pdf_files, file_card_elements)
        _build_controls(pdf_files, file_card_elements)
        _build_progress_section()
        _build_log_panel()
        _build_status_bar()

    ui.timer(0.1, lambda: _poll_state(pdf_files, file_card_elements))


# ===================================================================
# Header
# ===================================================================

def _build_header() -> None:
    config = ConfigManager()
    provider = config.get_provider()
    model_name = "Claude Haiku 4.5" if provider == "claude" else "GPT-5 mini"

    with ui.row().classes('app-header w-full items-center justify-between'):
        # Left: title + subtitle
        with ui.column().classes('gap-0'):
            ui.label('Auto Spine Survey v2.1').classes('app-title')
            ui.label('AI \uae30\ubc18 \uc124\ubb38\uc9c0 \ub370\uc774\ud130 \uc790\ub3d9 \ucd94\ucd9c').classes('app-subtitle')

        # Right: settings button + provider badge
        with ui.row().classes('items-center gap-2'):
            ui.button(icon='settings', on_click=open_settings).props(
                'flat round dense'
            ).classes('btn-icon')

            with ui.element('div').classes('provider-badge'):
                ui.label('AI').classes('text-xs')
                _ui['provider_label'] = ui.label(model_name).classes('provider-value')


# ===================================================================
# Drop Zone
# ===================================================================

def _build_drop_zone(pdf_files: List[str], file_card_elements: Dict) -> None:
    with ui.element('div').classes('drop-zone w-full') as zone:
        zone.on('dragover.prevent', lambda: None)
        zone.on('dragover', js_handler='(e) => e.currentTarget.classList.add("drag-over")')
        zone.on('dragleave', js_handler='(e) => e.currentTarget.classList.remove("drag-over")')
        zone.on('drop', js_handler='''(event) => {
            event.preventDefault();
            event.currentTarget.classList.remove("drag-over");
            const items = [...event.dataTransfer.files];
            const paths = items
                .filter(f => f.name.toLowerCase().endsWith(".pdf"))
                .map(f => f.path || "");
            const names = items
                .filter(f => f.name.toLowerCase().endsWith(".pdf"))
                .map(f => f.name);
            if (paths.length > 0) {
                $emit("files_dropped", {paths: paths, names: names});
            }
        }''')

        with ui.column().classes('items-center gap-2 py-6'):
            ui.icon('folder_open').classes('drop-icon')
            ui.label('PDF \ud30c\uc77c\uc744 \ub4dc\ub798\uadf8\ud558\uc138\uc694').classes('drop-main-text')
            ui.label('\ub610\ub294 \ud074\ub9ad\ud558\uc5ec \uc120\ud0dd').classes('drop-sub-text')

        uploader = ui.upload(
            multiple=True,
            on_upload=lambda e: _handle_upload(e, pdf_files, file_card_elements),
            auto_upload=True,
        ).props('accept=.pdf').classes('hidden')

        zone.on('click', lambda: uploader.run_method('pickFiles'))
        zone.on('files_dropped', lambda e: _handle_drop_event(e, pdf_files, file_card_elements))


def _handle_upload(event, pdf_files: List[str], file_card_elements: Dict) -> None:
    """Handle file selected via the upload widget (click-to-browse)."""
    from core import PROJECT_ROOT

    temp_dir = PROJECT_ROOT / 'temp_images'
    temp_dir.mkdir(parents=True, exist_ok=True)

    name = event.name
    content = event.content.read()
    dest = temp_dir / name
    dest.write_bytes(content)
    _add_files([str(dest)], pdf_files, file_card_elements)


def _handle_drop_event(event, pdf_files: List[str], file_card_elements: Dict) -> None:
    """Handle files dropped via drag-and-drop (Electron / NiceGUI desktop)."""
    args = event.args
    paths = [p for p in args.get('paths', []) if p]
    if paths:
        _add_files(paths, pdf_files, file_card_elements)


# ===================================================================
# File List
# ===================================================================

def _build_file_list(pdf_files: List[str], file_card_elements: Dict) -> None:
    with ui.row().classes('w-full items-center justify-between'):
        _ui['file_count_label'] = ui.label('\ud30c\uc77c \ubaa9\ub85d (0\uac1c)').classes(
            'text-sm font-bold'
        )
        ui.button('\ubaa8\ub450 \uc81c\uac70', on_click=lambda: _clear_all(pdf_files, file_card_elements)).props(
            'flat dense size=sm'
        ).classes('text-xs')

    with ui.scroll_area().classes('w-full').style('max-height: 200px'):
        _ui['file_list_column'] = ui.column().classes('w-full gap-1')


def _add_files(paths: List[str], pdf_files: List[str], file_card_elements: Dict) -> None:
    added = 0
    for p in paths:
        if p not in pdf_files:
            pdf_files.append(p)
            _create_file_card(p, 'waiting', file_card_elements, pdf_files)
            added += 1
    if added:
        _update_file_count(pdf_files)
        _update_start_btn(pdf_files)
        _set_status(f'{added}\uac1c \ud30c\uc77c \ucd94\uac00\ub428')


def _create_file_card(
    path: str, status: str, file_card_elements: Dict, pdf_files: List[str]
) -> None:
    status_icons = {'waiting': '\u23f3', 'processing': '\ud83d\udd04', 'complete': '\u2705', 'error': '\u274c'}
    icon_text = status_icons.get(status, '\u23f3')
    fname = os.path.basename(path)

    with _ui['file_list_column']:
        with ui.row().classes(f'file-card status-{status} w-full items-center justify-between') as row:
            with ui.row().classes('items-center gap-2 flex-grow'):
                icon_el = ui.label(icon_text).classes('text-base')
                ui.label(fname).classes('file-name')
                detail_el = ui.label('').classes('file-detail')
            ui.button(
                icon='close',
                on_click=lambda p=path: _remove_file(p, pdf_files, file_card_elements),
            ).props('flat round dense size=sm')

    file_card_elements[path] = {'row': row, 'icon': icon_el, 'detail': detail_el}


def _update_file_card_status(
    path: str, status: str, detail: str, file_card_elements: Dict
) -> None:
    if path not in file_card_elements:
        return
    elems = file_card_elements[path]
    status_icons = {'waiting': '\u23f3', 'processing': '\ud83d\udd04', 'complete': '\u2705', 'error': '\u274c'}
    elems['icon'].set_text(status_icons.get(status, '\u23f3'))
    elems['detail'].set_text(detail)

    row = elems['row']
    for s in ('waiting', 'processing', 'complete', 'error'):
        row.classes(remove=f'status-{s}')
    row.classes(add=f'status-{status}')


def _remove_file(path: str, pdf_files: List[str], file_card_elements: Dict) -> None:
    if path in file_card_elements:
        file_card_elements[path]['row'].delete()
        del file_card_elements[path]
    if path in pdf_files:
        pdf_files.remove(path)
    _update_file_count(pdf_files)
    _update_start_btn(pdf_files)


def _clear_all(pdf_files: List[str], file_card_elements: Dict) -> None:
    for p in list(pdf_files):
        _remove_file(p, pdf_files, file_card_elements)
    if not _state['is_processing']:
        _reset_progress()


# ===================================================================
# Controls
# ===================================================================

def _build_controls(pdf_files: List[str], file_card_elements: Dict) -> None:
    with ui.row().classes('w-full items-center justify-between'):
        with ui.row().classes('gap-2'):
            _ui['start_btn'] = ui.button(
                '\u25b6  \ucc98\ub9ac \uc2dc\uc791',
                on_click=lambda: asyncio.ensure_future(
                    _start_processing(pdf_files, file_card_elements)
                ),
            ).classes('btn-start')
            _ui['start_btn'].disable()

            _ui['stop_btn'] = ui.button(
                '\u23f9  \uc911\uc9c0',
                on_click=_stop_processing,
            ).classes('btn-stop')
            _ui['stop_btn'].disable()

        with ui.row().classes('gap-2'):
            ui.button(
                '\ud83d\udcc1 \uacb0\uacfc \ud3f4\ub354', on_click=_open_output_folder
            ).classes('btn-secondary')
            ui.button(
                '\u2699 \uc124\uc815', on_click=open_settings
            ).classes('btn-secondary')


# ===================================================================
# Progress Section
# ===================================================================

def _build_progress_section() -> None:
    with ui.card().classes('progress-section w-full'):
        _ui['current_file_label'] = ui.label('\u23f3 \ub300\uae30 \uc911...').classes(
            'progress-file-label'
        )
        _ui['progress_bar'] = ui.linear_progress(
            value=0, show_value=False
        ).props('color=teal')
        _ui['page_label'] = ui.label('0 / 0 \ud398\uc774\uc9c0 \uc644\ub8cc').classes(
            'progress-page-label'
        )


# ===================================================================
# Log Panel (collapsible)
# ===================================================================

def _build_log_panel() -> None:
    with ui.column().classes('w-full gap-0'):
        with ui.row().classes('log-panel-header w-full items-center justify-between').on(
            'click', _toggle_log
        ):
            ui.label('\ud83d\udcdd \uc2e4\ud589 \ub85c\uadf8').classes('text-sm font-semibold')
            _ui['log_toggle_icon'] = ui.icon('expand_more').classes('text-base')

        _ui['log_container'] = ui.column().classes('w-full hidden')
        with _ui['log_container']:
            _ui['log_area'] = ui.html('').classes('log-body w-full')


# ===================================================================
# Status Bar
# ===================================================================

def _build_status_bar() -> None:
    with ui.row().classes('status-bar w-full items-center justify-between'):
        with ui.row().classes('items-center gap-3'):
            _ui['status_label'] = ui.label('\u2705 \uc900\ube44\ub428').classes('text-xs')
            ui.label('v2.1').classes('text-xs font-bold')

            config = ConfigManager()
            provider = config.get_provider()
            model_text = "Claude Haiku 4.5" if provider == "claude" else "GPT-5 mini"
            _ui['model_label'] = ui.label(model_text).classes('text-xs')

        _ui['time_label'] = ui.label('').classes('text-xs')
        ui.timer(1.0, _update_clock)


def _update_clock() -> None:
    if 'time_label' in _ui:
        _ui['time_label'].set_text(datetime.now().strftime('%H:%M:%S'))


# ===================================================================
# Processing (async entry + blocking pipeline)
# ===================================================================

async def _start_processing(pdf_files: List[str], file_card_elements: Dict) -> None:
    if not pdf_files:
        ui.notify('\ucc98\ub9ac\ud560 PDF \ud30c\uc77c\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.', type='warning')
        return

    # Reset state
    _state['is_processing'] = True
    _state['stop_requested'] = False
    _state['progress'] = 0.0
    _state['log_lines'] = []
    _state['result'] = None
    _state['error'] = None
    _state['_log_last_len'] = 0
    _state['processed_files'] = set()

    _ui['start_btn'].disable()
    _ui['stop_btn'].enable()
    _set_status('\ud83d\udd04 \ucc98\ub9ac \uc911...')
    _state['log_lines'].append(f"[{datetime.now().strftime('%H:%M:%S')}] \ucc98\ub9ac \uc2dc\uc791")

    # Mark all files as processing
    for p in pdf_files:
        _update_file_card_status(p, 'processing', '', file_card_elements)

    # Run blocking pipeline in a thread
    await run.io_bound(_run_pipeline, list(pdf_files), _state)

    _state['is_processing'] = False
    _ui['stop_btn'].disable()

    if _state['result']:
        _complete_processing(
            _state['result']['output_file'],
            _state['result']['count'],
            pdf_files,
            file_card_elements,
        )
    elif _state['error']:
        ui.notify(f"\uc624\ub958: {_state['error']}", type='negative', close_button=True)
        _set_status('\u274c \uc624\ub958 \ubc1c\uc0dd')

    _update_start_btn(pdf_files)


def _run_pipeline(pdf_files: List[str], state: Dict) -> None:
    """BLOCKING function -- runs in a thread. Never call ui.* here."""
    from core.pdf_processor import PDFProcessor
    from core.claude_processor import ClaudeProcessor
    from core.openai_processor import OpenAIProcessor
    from core.csv_generator import CSVGenerator
    from core.config import load_config
    from core import PROJECT_ROOT

    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    base_dir = str(PROJECT_ROOT)
    logs_dir = os.path.join(base_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(
        logs_dir, f"spine_survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_formatter)

    loggers = [
        logging.getLogger('PDFProcessor'),
        logging.getLogger('ClaudeProcessor'),
        logging.getLogger('CSVGenerator'),
        logging.getLogger(),
    ]
    for logger in loggers:
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)

    try:
        config_manager = load_config()
        api_key = config_manager.get_api_key()
        folders = config_manager.get_folders()
        output_folder = folders['output_folder']
        os.makedirs(output_folder, exist_ok=True)

        _log(state, f"\ucc98\ub9ac \uc2dc\uc791 - \ucd1d {len(pdf_files)}\uac1c \ud30c\uc77c")

        all_survey_data = []
        total_pages = 0
        file_page_counts = []

        for pdf_path in pdf_files:
            try:
                pdf_proc = PDFProcessor(pdf_path, folders['temp_folder'])
                pc = pdf_proc.get_page_count()
                file_page_counts.append((pdf_path, pc))
                total_pages += pc
            except Exception:
                file_page_counts.append((pdf_path, 0))

        processed_pages = 0

        for idx, (pdf_path, page_count) in enumerate(file_page_counts):
            if state['stop_requested']:
                _log(state, "\ucc98\ub9ac \uc911\uc9c0\ub428")
                break

            fname = os.path.basename(pdf_path)
            state['current_file'] = f"\ud83d\udd04 PDF \ubcc0\ud658 \uc911: {fname} ({idx + 1}/{len(pdf_files)})"
            _log(state, f"\ud30c\uc77c \uc2dc\uc791: {fname}")

            try:
                pdf_processor = PDFProcessor(pdf_path, folders['temp_folder'])
                processed_images = pdf_processor.process_pdf()
                logging.info(f"PDF \ubcc0\ud658 \uc644\ub8cc: {len(processed_images)}\uac1c \ud398\uc774\uc9c0")

                provider = config_manager.get_provider()
                if provider == 'openai':
                    ai_processor = OpenAIProcessor(api_key)
                else:
                    ai_processor = ClaudeProcessor(api_key)

                state['current_file'] = f"\ud83e\udd16 AI \ucc98\ub9ac \uc911: {fname} ({len(processed_images)}\ud398\uc774\uc9c0)"

                def progress_callback(page_idx, total_pages_in_file, _pp=None):
                    nonlocal processed_pages
                    processed_pages += 1
                    if total_pages > 0:
                        state['progress'] = processed_pages / total_pages
                    state['page_detail'] = (
                        f"{processed_pages} / {total_pages} "
                        f"\ud398\uc774\uc9c0 \uc644\ub8cc ({state['progress'] * 100:.1f}%)"
                    )
                    state['current_file'] = (
                        f"\ud83e\udd16 AI \ucc98\ub9ac \uc911: {fname} - "
                        f"{page_idx + 1}/{total_pages_in_file} \ud398\uc774\uc9c0"
                    )

                survey_data = ai_processor.process_images(
                    processed_images, progress_callback=progress_callback
                )

                if survey_data:
                    all_survey_data.extend(survey_data)
                    state['processed_files'].add(pdf_path)
                    _log(state, f"\uc644\ub8cc: {fname} - {len(survey_data)}\uac1c \ub370\uc774\ud130")

            except Exception as e:
                error_msg = f"\uc624\ub958 ({fname}): {str(e)}"
                logging.error(error_msg, exc_info=True)
                _log(state, f"ERROR: {error_msg}")

            finally:
                temp_folder = folders['temp_folder']
                if os.path.exists(temp_folder):
                    try:
                        shutil.rmtree(temp_folder)
                        os.makedirs(temp_folder)
                    except PermissionError:
                        try:
                            for fn in os.listdir(temp_folder):
                                fp = os.path.join(temp_folder, fn)
                                if os.path.isfile(fp):
                                    try:
                                        os.remove(fp)
                                    except Exception:
                                        pass
                        except Exception:
                            pass

        # CSV generation
        if all_survey_data and not state['stop_requested']:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_config = config_manager.get_output_config()
            filename = f"{timestamp}_{output_config['csv_filename']}"

            output_dir = os.path.join(base_dir, 'output_csv')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)

            csv_generator = CSVGenerator(output_path)
            df = csv_generator.generate_csv(all_survey_data)

            if df is not None:
                count = len(state['processed_files'])
                _log(state, f"CSV \uc0dd\uc131 \uc644\ub8cc: {output_path}")
                _log(state, f"\ucd1d {count}\uac1c \ud30c\uc77c \ucc98\ub9ac \uc644\ub8cc")
                state['result'] = {'output_file': output_path, 'count': count}

    except Exception as e:
        logging.error(f"\uce58\uba85\uc801 \uc624\ub958: {str(e)}", exc_info=True)
        state['error'] = str(e)
        _log(state, f"FATAL: {str(e)}")

    finally:
        state['is_processing'] = False
        for logger in loggers:
            logger.removeHandler(file_handler)
        file_handler.close()


def _log(state: Dict, message: str) -> None:
    """Append a timestamped log line to state (thread-safe for append)."""
    ts = datetime.now().strftime('%H:%M:%S')
    state['log_lines'].append(f"[{ts}] {message}")


# ===================================================================
# UI Timer - poll shared state
# ===================================================================

def _poll_state(pdf_files: List[str], file_card_elements: Dict) -> None:
    """Called every 100ms. Read _state, update UI."""
    if 'progress_bar' in _ui:
        _ui['progress_bar'].set_value(_state['progress'])
    if 'current_file_label' in _ui:
        _ui['current_file_label'].set_text(_state['current_file'])
    if 'page_label' in _ui:
        _ui['page_label'].set_text(_state['page_detail'])

    # Append new log lines only
    cur_len = len(_state['log_lines'])
    last_len = _state['_log_last_len']
    if cur_len > last_len and 'log_area' in _ui:
        new_lines = _state['log_lines'][last_len:cur_len]
        escaped = '<br>'.join(
            line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            for line in new_lines
        )
        current_html = _ui['log_area'].content
        if current_html:
            _ui['log_area'].set_content(current_html + '<br>' + escaped)
        else:
            _ui['log_area'].set_content(escaped)
        _state['_log_last_len'] = cur_len

    # Update file card statuses from processed_files set
    for p in list(_state.get('processed_files', set())):
        if p in file_card_elements:
            _update_file_card_status(p, 'complete', '\uc644\ub8cc', file_card_elements)


# ===================================================================
# Processing Completion
# ===================================================================

def _complete_processing(
    output_file: str, count: int, pdf_files: List[str], file_card_elements: Dict
) -> None:
    _set_status(f'\u2705 \uc644\ub8cc: {count}\uac1c \ud30c\uc77c \ucc98\ub9ac\ub428')
    _state['log_lines'].append(
        f"[{datetime.now().strftime('%H:%M:%S')}] \ucc98\ub9ac \uc644\ub8cc: {count}\uac1c \ud30c\uc77c"
    )

    with ui.dialog() as dlg, ui.card().classes('p-6'):
        ui.label(f'\ud83c\udf89 {count}\uac1c \ud30c\uc77c\uc774 \uc131\uacf5\uc801\uc73c\ub85c \ucc98\ub9ac\ub418\uc5c8\uc2b5\ub2c8\ub2e4.').classes(
            'text-base font-semibold'
        )
        ui.label(f'\uacb0\uacfc: {os.path.basename(output_file)}').classes('text-sm text-gray-500 mt-2')
        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('CSV \uc5f4\uae30', on_click=lambda: _open_file(output_file)).classes('btn-start')
            ui.button('\ub2eb\uae30', on_click=dlg.close).classes('btn-secondary')
    dlg.open()

    # Clear file list
    _clear_all(pdf_files, file_card_elements)

    # Reset progress after 2 seconds
    ui.timer(2.0, _reset_progress, once=True)


# ===================================================================
# Helper Functions
# ===================================================================

def _set_status(text: str) -> None:
    if 'status_label' in _ui:
        _ui['status_label'].set_text(text)


def _update_file_count(pdf_files: List[str]) -> None:
    count = len(pdf_files)
    if 'file_count_label' in _ui:
        _ui['file_count_label'].set_text(f'\ud30c\uc77c \ubaa9\ub85d ({count}\uac1c)')


def _update_start_btn(pdf_files: List[str]) -> None:
    if 'start_btn' not in _ui:
        return
    if pdf_files and not _state['is_processing']:
        _ui['start_btn'].enable()
    else:
        _ui['start_btn'].disable()


def _stop_processing() -> None:
    _state['stop_requested'] = True
    _set_status('\u26d4 \ucc98\ub9ac \uc911\uc9c0\ub428')
    _state['current_file'] = '\u23f9\ufe0f \uc911\uc9c0\ub428'
    _state['log_lines'].append(
        f"[{datetime.now().strftime('%H:%M:%S')}] \ucc98\ub9ac \uc911\uc9c0"
    )


def _open_output_folder() -> None:
    from core import PROJECT_ROOT
    output_folder = str(PROJECT_ROOT / 'output_csv')
    os.makedirs(output_folder, exist_ok=True)

    if os.name == 'nt':
        os.startfile(output_folder)
    elif sys.platform == 'darwin':
        os.system(f'open "{output_folder}"')
    else:
        os.system(f'xdg-open "{output_folder}"')


def _open_file(path: str) -> None:
    if os.name == 'nt':
        os.startfile(path)
    elif sys.platform == 'darwin':
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


def open_settings() -> None:
    from gui_ng.settings import build_settings_dialog
    build_settings_dialog(on_saved=_refresh_provider_label)


def _refresh_provider_label() -> None:
    config = ConfigManager()
    provider = config.get_provider()
    model_name = "Claude Haiku 4.5" if provider == "claude" else "GPT-5 mini"
    if 'provider_label' in _ui:
        _ui['provider_label'].set_text(model_name)
    if 'model_label' in _ui:
        _ui['model_label'].set_text(model_name)


def _reset_progress() -> None:
    _state['progress'] = 0.0
    _state['current_file'] = '\u23f3 \ub300\uae30 \uc911...'
    _state['page_detail'] = '0 / 0 \ud398\uc774\uc9c0 \uc644\ub8cc'
    if 'progress_bar' in _ui:
        _ui['progress_bar'].set_value(0)
    if 'current_file_label' in _ui:
        _ui['current_file_label'].set_text('\u23f3 \ub300\uae30 \uc911...')
    if 'page_label' in _ui:
        _ui['page_label'].set_text('0 / 0 \ud398\uc774\uc9c0 \uc644\ub8cc')
    _set_status('\u2705 \uc900\ube44\ub428')


def _toggle_log() -> None:
    if 'log_container' not in _ui:
        return
    _log_visible[0] = not _log_visible[0]
    container = _ui['log_container']
    if _log_visible[0]:
        container.classes(remove='hidden')
        if 'log_toggle_icon' in _ui:
            _ui['log_toggle_icon'].set_text('expand_less')
    else:
        container.classes(add='hidden')
        if 'log_toggle_icon' in _ui:
            _ui['log_toggle_icon'].set_text('expand_more')
