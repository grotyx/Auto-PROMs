"""
Auto Spine Survey v2.1.1 - Main Page (NiceGUI)
Migrated from CustomTkinter gui/main_window.py to NiceGUI.
"""

import asyncio
import logging
import os
import shutil
import subprocess
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
    "current_file": "대기 중...",
    "page_detail": "0 / 0 페이지 완료",
    "log_lines": [],
    "result": None,       # {"output_file": str, "count": int}
    "error": None,
    "processed_files": set(),
    "_log_last_len": 0,
    "_output_file": "",   # set before opening result dialog
}

_ui: Dict = {}  # UI element references
_log_visible: List[bool] = [False]  # track log panel visibility

# File card status → Material Icon name + color
_STATUS_ICON = {
    'waiting':    ('schedule',      '#94a3b8'),
    'processing': ('sync',          '#219EBC'),
    'complete':   ('check_circle',  '#10b981'),
    'error':      ('error',         '#ef4444'),
}

# ---------------------------------------------------------------------------
# Quasar component color overrides (injected as inline <style> — never cached)
# ---------------------------------------------------------------------------
_QUASAR_STYLE_OVERRIDES = '''<style>
/* --- Quasar Button Colors --- */
.q-btn.btn-start,
button.q-btn.btn-start { background: #FB8500 !important; color: #fff !important; }
.q-btn.btn-start:hover { background: #d97000 !important; }
.q-btn.btn-start.disabled,
.q-btn.btn-start[disabled] { background: #FB8500 !important; opacity: 0.45 !important; }

.q-btn.btn-stop,
button.q-btn.btn-stop { background: #023047 !important; color: #fff !important; }
.q-btn.btn-stop:hover { background: #034c6e !important; }
.q-btn.btn-stop.disabled,
.q-btn.btn-stop[disabled] { background: #023047 !important; opacity: 0.45 !important; }

.q-btn.btn-folder,
button.q-btn.btn-folder { background: #219EBC !important; color: #fff !important; }
.q-btn.btn-folder:hover { background: #1a7d96 !important; }

.q-btn.btn-secondary,
button.q-btn.btn-secondary { background: #8ECAE6 !important; color: #023047 !important; }
.q-btn.btn-secondary:hover { background: #72c2da !important; }

/* --- Quasar Uploader Header --- */
.q-uploader__header { background: #219EBC !important; color: #fff !important; }

/* --- Settings Icon (amber on ocean-blue header) --- */
.btn-icon-accent,
.btn-icon-accent .q-btn__content,
.btn-icon-accent .q-icon,
.btn-icon-accent .material-icons { color: #FFB703 !important; background: transparent !important; }
.btn-icon-accent:hover { background: rgba(255,255,255,0.15) !important; }
</style>'''


# ===================================================================
# Public entry point - called from @ui.page('/')
# ===================================================================

def build_page() -> None:
    """Build the entire main page layout."""
    pdf_files: List[str] = []
    file_card_elements: Dict[str, object] = {}

    # Pre-create result dialog (must exist in page context, not async task context)
    _build_result_dialog()

    # Inject Quasar overrides as inline <style> (bypasses static file caching)
    ui.add_head_html(_QUASAR_STYLE_OVERRIDES)

    # Block browser from EVER opening a dropped file (prevents PDF rendering in webview).
    # Capture phase (3rd arg = true) ensures this runs BEFORE any child handlers.
    # The Quasar uploader still reads dataTransfer.files in its own bubble handler.
    ui.add_head_html('''<script>
    ["dragover","drop","dragenter"].forEach(function(evt){
        document.addEventListener(evt, function(e){
            e.preventDefault();
        }, true);
    });
    </script>''')

    with ui.column().classes('w-full gap-3 px-4 py-3'):
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
        with ui.column().classes('gap-0'):
            ui.label('Auto Spine Survey').classes('app-title')
            ui.label('AI 기반 설문지 데이터 자동 추출').classes('app-subtitle')

        with ui.row().classes('items-center gap-2'):
            ui.button(icon='settings', on_click=open_settings).props(
                'flat round dense'
            ).classes('btn-icon-accent')

            with ui.element('div').classes('provider-badge'):
                ui.label('AI').classes('text-xs')
                _ui['provider_label'] = ui.label(model_name).classes('provider-value')


# ===================================================================
# Drop Zone
# ===================================================================

def _build_drop_zone(pdf_files: List[str], file_card_elements: Dict) -> None:
    with ui.element('div').classes('drop-zone w-full'):
        with ui.column().classes('items-center gap-1 py-2 w-full'):
            ui.label('upload_file').classes('material-icons drop-icon')
            ui.label('PDF 파일을 드래그하거나 클릭하여 선택').classes('drop-main-text')
            ui.label('PDF, 각 6페이지 / 최대 50개').classes('drop-sub-text')

        _ui['uploader'] = ui.upload(
            multiple=True,
            on_upload=lambda e: _handle_upload(e, pdf_files, file_card_elements),
            auto_upload=True,
        ).props('accept=.pdf flat label="파일 선택 또는 이곳에 드래그"').classes('w-full')


async def _handle_upload(event, pdf_files: List[str], file_card_elements: Dict) -> None:
    """Handle file selected via the upload widget (click-to-browse or drag-and-drop).
    NiceGUI 3.x: event.file is a FileUpload with async .save() / .read().
    """
    from core import PROJECT_ROOT

    temp_dir = PROJECT_ROOT / 'temp_images'
    temp_dir.mkdir(parents=True, exist_ok=True)

    name = event.file.name
    dest = temp_dir / name
    await event.file.save(str(dest))
    _add_files([str(dest)], pdf_files, file_card_elements)


# ===================================================================
# File List
# ===================================================================

def _build_file_list(pdf_files: List[str], file_card_elements: Dict) -> None:
    with ui.element('div').classes('file-list-section w-full'):
        with ui.row().classes('w-full items-center justify-between'):
            _ui['file_count_label'] = ui.label('파일 목록 (0개)').classes(
                'text-sm font-bold'
            )
            ui.button(
                '모두 제거',
                on_click=lambda: _clear_all(pdf_files, file_card_elements),
            ).props('flat dense size=sm').classes('text-xs')

        with ui.scroll_area().classes('w-full').style('max-height: 180px'):
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
        _set_status(f'{added}개 파일 추가됨')


def _create_file_card(
    path: str, status: str, file_card_elements: Dict, pdf_files: List[str]
) -> None:
    icon_name, icon_color = _STATUS_ICON.get(status, ('schedule', '#94a3b8'))
    fname = os.path.basename(path)

    with _ui['file_list_column']:
        with ui.row().classes(f'file-card status-{status} w-full items-center justify-between') as row:
            with ui.row().classes('items-center gap-2 flex-grow'):
                icon_el = ui.label(icon_name).classes(
                    'material-icons text-base'
                ).style(f'color: {icon_color}')
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
    icon_name, icon_color = _STATUS_ICON.get(status, ('schedule', '#94a3b8'))
    elems['icon'].set_text(icon_name)
    elems['icon'].style(f'color: {icon_color}')
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
    if 'uploader' in _ui:
        _ui['uploader'].run_method('reset')
    if not _state['is_processing']:
        _reset_progress()


# ===================================================================
# Controls
# ===================================================================

def _build_controls(pdf_files: List[str], file_card_elements: Dict) -> None:
    with ui.row().classes('w-full items-center justify-between'):
        with ui.row().classes('gap-2'):
            _ui['start_btn'] = ui.button(
                '처리 시작',
                icon='play_arrow',
                on_click=lambda: asyncio.ensure_future(
                    _start_processing(pdf_files, file_card_elements)
                ),
            ).props('unelevated no-caps').classes('btn-start')
            _ui['start_btn'].disable()

            _ui['stop_btn'] = ui.button(
                '중지',
                icon='stop',
                on_click=_stop_processing,
            ).props('unelevated no-caps').classes('btn-stop')
            _ui['stop_btn'].disable()

        ui.button(
            '결과 폴더',
            icon='folder_open',
            on_click=_open_output_folder,
        ).props('unelevated no-caps').classes('btn-folder')


# ===================================================================
# Progress Section
# ===================================================================

def _build_progress_section() -> None:
    with ui.card().classes('progress-section w-full'):
        _ui['current_file_label'] = ui.label('대기 중...').classes(
            'progress-file-label'
        )
        _ui['progress_bar'] = ui.linear_progress(value=0, show_value=False)
        _ui['page_label'] = ui.label('0 / 0 페이지 완료').classes(
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
            with ui.row().classes('items-center gap-1'):
                ui.label('article').classes('material-icons text-sm').style('color: #219EBC')
                ui.label('실행 로그').classes('text-sm font-semibold')
            _ui['log_toggle_icon'] = ui.label('expand_more').classes('material-icons text-base')

        _ui['log_container'] = ui.column().classes('w-full hidden')
        with _ui['log_container']:
            _ui['log_area'] = ui.html('').classes('log-body w-full')


# ===================================================================
# Status Bar
# ===================================================================

def _build_status_bar() -> None:
    config = ConfigManager()
    provider = config.get_provider()
    model_text = "Claude Haiku 4.5" if provider == "claude" else "GPT-5 mini"

    with ui.row().classes('status-bar w-full items-center justify-between'):
        with ui.row().classes('items-center gap-3'):
            _ui['status_label'] = ui.label('준비됨').classes('text-xs')
            ui.label('v2.1.1').classes('text-xs font-bold')
            _ui['model_label'] = ui.label(model_text).classes('text-xs')

        _ui['time_label'] = ui.label('').classes('text-xs')
        ui.timer(1.0, _update_clock)


def _update_clock() -> None:
    if 'time_label' in _ui:
        _ui['time_label'].set_text(datetime.now().strftime('%H:%M:%S'))


# ===================================================================
# Result Dialog (pre-created at page build time)
# ===================================================================

def _build_result_dialog() -> None:
    """Pre-create the completion dialog so it can be opened from async context."""
    with ui.dialog() as dlg:
        with ui.card().classes('p-6'):
            with ui.row().classes('items-center gap-2 mb-1'):
                ui.label('check_circle').classes('material-icons').style(
                    'color: #10b981; font-size: 22px'
                )
                _ui['result_title'] = ui.label('').classes('text-base font-semibold')
            _ui['result_filename'] = ui.label('').classes('text-sm text-gray-500 mt-1')
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(
                    'CSV 열기',
                    icon='open_in_new',
                    on_click=lambda: _open_file(_state['_output_file']),
                ).props('unelevated no-caps').classes('btn-start')
                ui.button(
                    '닫기',
                    icon='close',
                    on_click=dlg.close,
                ).props('unelevated no-caps').classes('btn-secondary')
    _ui['result_dialog'] = dlg


# ===================================================================
# Processing (async entry + blocking pipeline)
# ===================================================================

async def _start_processing(pdf_files: List[str], file_card_elements: Dict) -> None:
    if not pdf_files:
        ui.notify('처리할 PDF 파일이 없습니다.', type='warning')
        return

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
    _set_status('처리 중...')
    _state['log_lines'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 처리 시작")

    for p in pdf_files:
        _update_file_card_status(p, 'processing', '', file_card_elements)

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
        ui.notify(f"오류: {_state['error']}", type='negative', close_button=True)
        _set_status('오류 발생')

    _update_start_btn(pdf_files)


def _run_pipeline(pdf_files: List[str], state: Dict) -> None:
    """BLOCKING function -- runs in a thread. Never call ui.* here."""
    from core.pdf_processor import PDFProcessor
    from core.claude_processor import ClaudeProcessor
    from core.openai_processor import OpenAIProcessor
    from core.csv_generator import CSVGenerator
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

        _log(state, f"처리 시작 - 총 {len(pdf_files)}개 파일")

        all_survey_data = []
        total_pages = 0
        file_page_counts = []

        # Pre-scan page counts
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
                _log(state, "처리 중지됨")
                break

            fname = os.path.basename(pdf_path)
            state['current_file'] = f"PDF 변환 중: {fname} ({idx + 1}/{len(pdf_files)})"
            _log(state, f"파일 시작: {fname}")

            try:
                pdf_processor = PDFProcessor(pdf_path, folders['temp_folder'])
                processed_images = pdf_processor.process_pdf()
                logging.info(f"PDF 변환 완료: {len(processed_images)}개 페이지")

                provider = config_manager.get_provider()
                if provider == 'openai':
                    ai_processor = OpenAIProcessor(api_key)
                else:
                    ai_processor = ClaudeProcessor(api_key)

                state['current_file'] = f"AI 처리 중: {fname} ({len(processed_images)}페이지)"

                def progress_callback(page_idx, total_pages_in_file, _pp=None):
                    nonlocal processed_pages
                    processed_pages += 1
                    if total_pages > 0:
                        state['progress'] = processed_pages / total_pages
                    state['page_detail'] = (
                        f"{processed_pages} / {total_pages} "
                        f"페이지 완료 ({state['progress'] * 100:.1f}%)"
                    )
                    state['current_file'] = (
                        f"AI 처리 중: {fname} - "
                        f"{page_idx + 1}/{total_pages_in_file} 페이지"
                    )

                survey_data = ai_processor.process_images(
                    processed_images, progress_callback=progress_callback
                )

                if survey_data:
                    all_survey_data.extend(survey_data)
                    state['processed_files'].add(pdf_path)
                    _log(state, f"완료: {fname} - {len(survey_data)}개 데이터")

            except Exception as e:
                error_msg = f"오류 ({fname}): {str(e)}"
                logging.error(error_msg, exc_info=True)
                _log(state, f"ERROR: {error_msg}")

            finally:
                temp_folder = folders['temp_folder']
                if os.path.exists(temp_folder):
                    try:
                        shutil.rmtree(temp_folder)
                        os.makedirs(temp_folder)
                    except PermissionError:
                        for fn in os.listdir(temp_folder):
                            fp = os.path.join(temp_folder, fn)
                            if os.path.isfile(fp):
                                try:
                                    os.remove(fp)
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
                _log(state, f"CSV 생성 완료: {output_path}")
                _log(state, f"총 {count}개 파일 처리 완료")
                state['result'] = {'output_file': output_path, 'count': count}

    except Exception as e:
        logging.error(f"치명적 오류: {str(e)}", exc_info=True)
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

    # Update file card statuses
    if _state['is_processing']:
        for p in list(_state.get('processed_files', set())):
            if p in file_card_elements:
                _update_file_card_status(p, 'complete', '완료', file_card_elements)


# ===================================================================
# Processing Completion
# ===================================================================

def _complete_processing(
    output_file: str, count: int, pdf_files: List[str], file_card_elements: Dict
) -> None:
    _set_status(f'완료: {count}개 파일 처리됨')
    _state['log_lines'].append(
        f"[{datetime.now().strftime('%H:%M:%S')}] 처리 완료: {count}개 파일"
    )

    _state['_output_file'] = output_file
    _ui['result_title'].set_text(f'{count}개 파일이 성공적으로 처리되었습니다.')
    _ui['result_filename'].set_text(f'결과: {os.path.basename(output_file)}')
    _ui['result_dialog'].open()

    _clear_all(pdf_files, file_card_elements)
    ui.timer(2.0, _reset_progress, once=True)


# ===================================================================
# Helper Functions
# ===================================================================

def _set_status(text: str) -> None:
    if 'status_label' in _ui:
        _ui['status_label'].set_text(text)


def _update_file_count(pdf_files: List[str]) -> None:
    if 'file_count_label' in _ui:
        _ui['file_count_label'].set_text(f'파일 목록 ({len(pdf_files)}개)')


def _update_start_btn(pdf_files: List[str]) -> None:
    if 'start_btn' not in _ui:
        return
    if pdf_files and not _state['is_processing']:
        _ui['start_btn'].enable()
    else:
        _ui['start_btn'].disable()


def _stop_processing() -> None:
    _state['stop_requested'] = True
    _set_status('처리 중지됨')
    _state['current_file'] = '중지됨'
    _state['log_lines'].append(
        f"[{datetime.now().strftime('%H:%M:%S')}] 처리 중지"
    )


def _open_output_folder() -> None:
    from core import PROJECT_ROOT
    output_folder = str(PROJECT_ROOT / 'output_csv')
    os.makedirs(output_folder, exist_ok=True)
    _open_path(output_folder)


def _open_file(path: str) -> None:
    _open_path(path)


def _open_path(path: str) -> None:
    """Open a file or folder using the platform's default handler (safe, no shell)."""
    if sys.platform == 'darwin':
        subprocess.Popen(['open', path])
    elif os.name == 'nt':
        os.startfile(path)
    else:
        subprocess.Popen(['xdg-open', path])


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
    _state['current_file'] = '대기 중...'
    _state['page_detail'] = '0 / 0 페이지 완료'
    if 'progress_bar' in _ui:
        _ui['progress_bar'].set_value(0)
    if 'current_file_label' in _ui:
        _ui['current_file_label'].set_text('대기 중...')
    if 'page_label' in _ui:
        _ui['page_label'].set_text('0 / 0 페이지 완료')
    _set_status('준비됨')


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
