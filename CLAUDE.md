# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auto Spine Survey v2.1 — AI 기반 척추 설문지(PROMs) 데이터 자동 추출 시스템.
PDF → 이미지(300 DPI) → AI Vision API → JSON → 검증 → CSV

**Platform**: Windows (macOS/Linux 호환)
**Default Provider**: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)

## Common Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt

# Run
python main_gui.py

# Build executable
python scripts/build_executable.py
```

## Architecture

```
Auto_PROMs_PSM_4_GUI/
├── main_gui.py               # GUI entry point (root에 유일한 실행 파일)
├── README.md
├── CLAUDE.md
├── requirements.txt
├── config.json               # Runtime settings, NO API keys (git-ignored)
├── config_template.json      # Config template (committed)
├── .env                      # API keys only (git-ignored)
├── .env.example              # API key template (committed)
│
├── core/                     # 핵심 처리 모듈
│   ├── __init__.py           # PROJECT_ROOT, DATA_DIR 정의
│   ├── config.py             # ConfigManager (dotenv + pathlib)
│   ├── base_processor.py     # Abstract base: instructions, encode, process
│   ├── claude_processor.py   # Claude API (_call_api) — default
│   ├── openai_processor.py   # OpenAI API (_call_api)
│   ├── validators.py         # SurveyValidator + EQ-5D cache
│   ├── pdf_processor.py      # PDF → image (PyMuPDF 300 DPI)
│   └── csv_generator.py      # Dict → CSV (35+ fields)
│
├── gui/                      # GUI 모듈
│   ├── __init__.py
│   ├── main_window.py        # CustomTkinter main window
│   ├── settings_dialog.py    # Settings with .env management
│   └── widgets.py            # FileCard, LogPanel, DropZone
│
├── data/                     # 정적 데이터 파일
│   ├── page_instruction.json # AI prompts per page (DO NOT MODIFY)
│   └── eq5d_value_k.csv      # EQ-5D value lookup (DO NOT MODIFY)
│
└── scripts/                  # 빌드/배포 스크립트
    └── build_executable.py   # PyInstaller build script
```

## Data Pipeline

```
PDF (6 pages = 1 survey)
  ↓ PDFProcessor (PyMuPDF, 300 DPI)
Image[]
  ↓ BaseProcessor.process_images()
  ↓   → concurrent: ThreadPoolExecutor (max_workers=6)
  ↓   → sequential: fallback
  ↓ _call_api() → Claude / OpenAI Vision API
JSON responses
  ↓ SurveyValidator.validate_page_data()
  ↓ EQ-5D value lookup (class-level cache)
Validated Dict
  ↓ CSVGenerator
CSV output (35+ fields)
```

## Critical Rules

### DO NOT MODIFY
- `data/page_instruction.json` — AI 프롬프트 (설문지 해석 지시)
- `data/eq5d_value_k.csv` — EQ-5D 값 룩업 테이블
- **validate_page_data() 로직** — 검증/보정 로직 (이동 OK, 수정 NO)
- **Survey data fields** — VAS, ODI, EQ-5D-5L, painDETECT 필드 구조
- **6페이지 = 1세트** 설문 그룹화 로직

### Security
- API 키는 `.env` 파일에서만 로드 (`python-dotenv`)
- `config.json`에 API 키 저장 금지
- `.env`는 git에 커밋하지 않음

### Path Management
- `core/__init__.py`에서 `PROJECT_ROOT`, `DATA_DIR` 정의
- 개발 모드: `PROJECT_ROOT = core/../` (프로젝트 루트)
- PyInstaller frozen: `PROJECT_ROOT = sys.executable.parent`, `DATA_DIR = sys._MEIPASS/data`
- 모든 파일 경로는 이 두 변수 기준으로 해석

## Key Design Decisions

- **Strategy Pattern**: `BaseProcessor` ABC → `ClaudeProcessor` (default) / `OpenAIProcessor`
- **Concurrency**: `ThreadPoolExecutor` + `SimpleRateLimiter` (semaphore), config에서 on/off
- **GUI Framework**: CustomTkinter 5.3.0 (dark/light mode, HighDPI)
- **DnD**: `tkinterdnd2` (Windows only), click-to-browse fallback (macOS/Linux)
- **Config**: `python-dotenv` for API keys, `config.json` for runtime settings
- **EQ-5D Caching**: `SurveyValidator._eq5d_table` class variable, loaded once
- **Package structure**: `core/` (relative imports), `gui/` (relative imports), `data/` (static)

## Survey Fields Reference

| Page | Type | Fields | Range |
|------|------|--------|-------|
| 0 | VAS | rc_id, visit_day, redcap_event_name, redcap_repeat_instance, lbp_vas, buttock_vas, le_vas_rt, le_vas_lt | 0-100 |
| 1-2 | ODI | odi_pain, odi_personal, odi_lifting, odi_walking, odi_sitting, odi_standing, odi_sleeping, odi_social, odi_travelling, odi_sexlife, odi_sexlifeyn | 0-5 |
| 3 | EQ-5D-5L | eq5d_mobility, eq5d_selfcare, eq5d_activities, eq5d_pain, eq5d_anxiety, eq5d_value | 1-5 |
| 4-5 | painDETECT | pndtct_buring, pndtct_tingling, pndtct_touching, pndtct_shock, pndtct_cold, pndtct_numbness, pndtct_pressure, pndtct_pattern, pndtct_radiating | 0-5, -1/0/1, 0/2 |

## Config Structure

### .env (API keys only, git-ignored)
```env
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-proj-xxx
```

### config.json (runtime settings, git-ignored)
```json
{
  "api_settings": {
    "provider": "claude",
    "claude_model": "claude-haiku-4-5-20251001",
    "openai_model": "gpt-5-mini"
  },
  "folders": {
    "input_folder": "input_pdfs",
    "output_folder": "output_csv",
    "temp_folder": "temp_images",
    "logs_folder": "logs"
  },
  "processing": {
    "pages_per_survey": 6,
    "max_tokens": 2000,
    "temperature": 0,
    "concurrent_enabled": true,
    "max_concurrent_requests": 6
  },
  "output": {
    "csv_filename": "spine_survey_results.csv",
    "include_timestamps": true,
    "backup_results": false
  }
}
```

## GUI Customization

- **Window**: 800x900, min 700x750
- **Fonts**: 맑은 고딕 (Windows), AppleSDGothicNeo (macOS), Noto Sans CJK KR (Linux)
- **Theme**: system/dark/light via `ctk.set_appearance_mode()`
- **Widgets**: `gui/widgets.py` — FileCard, LogPanel, DropZone

## Build Notes

- `scripts/build_executable.py` generates `.spec` dynamically — do NOT pass `--onefile`, `--windowed`, `--name` to PyInstaller
- CustomTkinter resources are auto-bundled via `get_ctk_data_path()`
- `.env` and `config.json` are excluded from builds; `config_template.json` is included
- Portable package includes `config.json` (from template), `.env.example`, `data/` files

## Platform Notes

- **Path**: `pathlib.Path` throughout (cross-platform backslash handling)
- **DnD**: Windows only via `tkinterdnd2`; macOS/Linux use click-to-browse
- **Build**: PyInstaller single-file executable
- **Fonts**: Platform-detected in `gui/widgets.py:get_platform_font()`

# currentDate
Today's date is 2026-02-17.

      IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.
