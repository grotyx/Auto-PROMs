"""gui_ng/settings.py — NiceGUI settings dialog"""

import json
import os
from typing import Callable, Optional

from dotenv import load_dotenv
from nicegui import ui

from core import PROJECT_ROOT

_ENV_PATH = PROJECT_ROOT / '.env'
_CONFIG_PATH = PROJECT_ROOT / 'config.json'


# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------

def _load_env_key(key: str) -> str:
    """Load an API key from .env (re-read file each time)."""
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    return os.getenv(key, '')


def _save_env_keys(claude_key: str, openai_key: str):
    """Save API keys to .env file and update os.environ."""
    lines = []
    if claude_key:
        lines.append(f'CLAUDE_API_KEY={claude_key}')
    if openai_key:
        lines.append(f'OPENAI_API_KEY={openai_key}')

    with open(_ENV_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    if claude_key:
        os.environ['CLAUDE_API_KEY'] = claude_key
    if openai_key:
        os.environ['OPENAI_API_KEY'] = openai_key


def _load_config() -> dict:
    """Load config.json and return as dict."""
    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(cfg: dict) -> bool:
    """Save config dict to config.json. Returns True on success."""
    try:
        with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        ui.notify(f'설정 파일 저장 실패: {e}', type='negative')
        return False


# ------------------------------------------------------------------
# Folder browser helper
# ------------------------------------------------------------------

def _browse_folder_native(input_el):
    """Open a native folder picker and set the input value."""
    try:
        from nicegui import app as ng_app
        import webview
        result = ng_app.native.main_window.create_file_dialog(
            webview.OPEN_FOLDER, allow_multiple=False
        )
        if result:
            input_el.set_value(result[0])
    except Exception:
        pass  # fallback: user types the path manually


# ------------------------------------------------------------------
# Save logic
# ------------------------------------------------------------------

def _save_and_close(dialog, config, api_state, folder_state, proc_state, out_state, on_saved):
    """Collect all state, write .env + config.json, close dialog."""
    config['api_settings'] = {
        'provider': api_state['provider'],
        'claude_model': api_state['claude_model'],
        'openai_model': api_state['openai_model'],
    }
    config['folders'] = dict(folder_state)
    config['processing'] = dict(proc_state)
    config['output'] = dict(out_state)

    _save_env_keys(api_state['claude_key'], api_state['openai_key'])

    if _save_config(config):
        ui.notify('설정이 저장되었습니다.', type='positive')
        dialog.close()
        if on_saved:
            on_saved()


# ------------------------------------------------------------------
# Main dialog builder
# ------------------------------------------------------------------

def build_settings_dialog(on_saved: Optional[Callable] = None):
    """Create and open the settings modal dialog."""

    config = _load_config()
    api_cfg = config.get('api_settings', {})
    folders_cfg = config.get('folders', {})
    proc_cfg = config.get('processing', {})
    out_cfg = config.get('output', {})

    # Reactive state dicts
    api_state = {
        'provider': api_cfg.get('provider', 'claude'),
        'claude_key': _load_env_key('CLAUDE_API_KEY'),
        'claude_model': api_cfg.get('claude_model', 'claude-haiku-4-5-20251001'),
        'openai_key': _load_env_key('OPENAI_API_KEY'),
        'openai_model': api_cfg.get('openai_model', 'gpt-5-mini'),
    }

    folder_state = {
        'input_folder': folders_cfg.get('input_folder', 'input_pdfs'),
        'output_folder': folders_cfg.get('output_folder', 'output_csv'),
        'temp_folder': folders_cfg.get('temp_folder', 'temp_images'),
        'logs_folder': folders_cfg.get('logs_folder', 'logs'),
    }

    proc_state = {
        'pages_per_survey': proc_cfg.get('pages_per_survey', 6),
        'max_tokens': proc_cfg.get('max_tokens', 2000),
        'temperature': proc_cfg.get('temperature', 0.0),
        'concurrent_enabled': proc_cfg.get('concurrent_enabled', True),
        'max_concurrent_requests': proc_cfg.get('max_concurrent_requests', 6),
    }

    out_state = {
        'csv_filename': out_cfg.get('csv_filename', 'spine_survey_results.csv'),
        'include_timestamps': out_cfg.get('include_timestamps', True),
        'backup_results': out_cfg.get('backup_results', False),
    }

    # ---- Dialog ----
    with ui.dialog() as dialog, ui.card().classes('settings-dialog'):

        # -- Tabs --
        with ui.tabs().classes('w-full') as tabs:
            api_tab = ui.tab('API 설정')
            folder_tab = ui.tab('폴더 설정')
            proc_tab = ui.tab('처리 설정')
            out_tab = ui.tab('출력 설정')

        with ui.tab_panels(tabs, value=api_tab).classes('w-full'):

            # ============================================================
            # API 설정 탭
            # ============================================================
            with ui.tab_panel(api_tab):
                ui.label('AI 프로바이더').classes('settings-section-title')
                provider_radio = ui.radio(
                    {'claude': 'Claude (기본)', 'openai': 'OpenAI GPT'},
                    value=api_state['provider'],
                ).props('inline')
                provider_radio.on_value_change(
                    lambda e: api_state.update({'provider': e.value})
                )

                # Claude section
                ui.label('Claude 설정').classes('settings-section-title mt-4')
                claude_key_input = ui.input(
                    'API Key',
                    value=api_state['claude_key'],
                    password=True,
                    password_toggle_button=True,
                ).classes('w-full')
                claude_key_input.on_value_change(
                    lambda e: api_state.update({'claude_key': e.value})
                )

                claude_model_input = ui.input(
                    '모델',
                    value=api_state['claude_model'],
                ).classes('w-full')
                claude_model_input.on_value_change(
                    lambda e: api_state.update({'claude_model': e.value})
                )

                # OpenAI section
                ui.label('OpenAI 설정').classes('settings-section-title mt-4')
                openai_key_input = ui.input(
                    'API Key',
                    value=api_state['openai_key'],
                    password=True,
                    password_toggle_button=True,
                ).classes('w-full')
                openai_key_input.on_value_change(
                    lambda e: api_state.update({'openai_key': e.value})
                )

                openai_model_input = ui.input(
                    '모델',
                    value=api_state['openai_model'],
                ).classes('w-full')
                openai_model_input.on_value_change(
                    lambda e: api_state.update({'openai_model': e.value})
                )

            # ============================================================
            # 폴더 설정 탭
            # ============================================================
            with ui.tab_panel(folder_tab):
                ui.label('폴더 경로').classes('settings-section-title')

                folder_items = [
                    ('input_folder', '입력 폴더'),
                    ('output_folder', '출력 폴더'),
                    ('temp_folder', '임시 폴더'),
                    ('logs_folder', '로그 폴더'),
                ]

                for key, label_text in folder_items:
                    with ui.row().classes('w-full items-center gap-2'):
                        ui.label(label_text).classes('w-20')
                        inp = ui.input(
                            value=folder_state[key],
                        ).classes('flex-grow')
                        _key = key  # capture for closure
                        inp.on_value_change(
                            lambda e, k=_key: folder_state.update({k: e.value})
                        )
                        ui.button(
                            icon='folder_open',
                            on_click=lambda _, el=inp: _browse_folder_native(el),
                        ).props('flat dense')

            # ============================================================
            # 처리 설정 탭
            # ============================================================
            with ui.tab_panel(proc_tab):
                ui.label('페이지 설정').classes('settings-section-title')
                pages_input = ui.number(
                    '설문당 페이지 수',
                    value=proc_state['pages_per_survey'],
                    min=1, max=20, precision=0,
                ).classes('w-full')
                pages_input.on_value_change(
                    lambda e: proc_state.update({'pages_per_survey': int(e.value) if e.value else 6})
                )

                ui.label('AI 설정').classes('settings-section-title mt-4')
                tokens_input = ui.number(
                    '최대 토큰',
                    value=proc_state['max_tokens'],
                    min=100, max=8000, step=100, precision=0,
                ).classes('w-full')
                tokens_input.on_value_change(
                    lambda e: proc_state.update({'max_tokens': int(e.value) if e.value else 2000})
                )

                with ui.row().classes('w-full items-center gap-4 mt-2'):
                    ui.label('Temperature')
                    temp_slider = ui.slider(
                        value=proc_state['temperature'],
                        min=0, max=1, step=0.1,
                    ).classes('flex-grow')
                    temp_label = ui.label(f"{proc_state['temperature']:.1f}")

                    def _on_temp_change(e):
                        proc_state['temperature'] = e.value
                        temp_label.set_text(f'{e.value:.1f}')

                    temp_slider.on_value_change(_on_temp_change)

                ui.label('동시 처리').classes('settings-section-title mt-4')
                conc_switch = ui.switch(
                    '동시 처리 활성화',
                    value=proc_state['concurrent_enabled'],
                )
                conc_switch.on_value_change(
                    lambda e: proc_state.update({'concurrent_enabled': e.value})
                )

                max_req_input = ui.number(
                    '최대 동시 요청 수',
                    value=proc_state['max_concurrent_requests'],
                    min=1, max=10, precision=0,
                ).classes('w-full')
                max_req_input.on_value_change(
                    lambda e: proc_state.update({
                        'max_concurrent_requests': int(e.value) if e.value else 6
                    })
                )

            # ============================================================
            # 출력 설정 탭
            # ============================================================
            with ui.tab_panel(out_tab):
                ui.label('파일명 설정').classes('settings-section-title')
                filename_input = ui.input(
                    '기본 파일명',
                    value=out_state['csv_filename'],
                ).classes('w-full')
                filename_input.on_value_change(
                    lambda e: out_state.update({'csv_filename': e.value})
                )

                ui.label('출력 옵션').classes('settings-section-title mt-4')
                ts_switch = ui.switch(
                    '파일명에 타임스탬프 포함',
                    value=out_state['include_timestamps'],
                )
                ts_switch.on_value_change(
                    lambda e: out_state.update({'include_timestamps': e.value})
                )

                backup_switch = ui.switch(
                    '백업 파일 생성',
                    value=out_state['backup_results'],
                )
                backup_switch.on_value_change(
                    lambda e: out_state.update({'backup_results': e.value})
                )

        # ---- Bottom buttons ----
        with ui.row().classes('w-full justify-end gap-2 mt-2'):
            ui.button('취소', on_click=dialog.close).classes('btn-secondary')
            ui.button('저장', on_click=lambda: _save_and_close(
                dialog, config, api_state, folder_state, proc_state, out_state, on_saved,
            )).classes('btn-start')

        # ---- Copyright ----
        ui.label(
            '\u00a9 2025 Seoul National University College of Medicine, '
            'Department of Orthopaedic Surgery\n'
            'Developed by Sang-Min Park | All rights reserved'
        ).classes('text-xs text-center text-gray-400 mt-2 whitespace-pre-line')

    dialog.open()
    return dialog
