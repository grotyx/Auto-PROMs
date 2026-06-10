# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Auto Spine Survey v2.2.3 — AI 기반 척추 설문지(PROMs) 데이터 자동 추출 시스템.
PDF → 이미지(300 DPI) → AI Vision API → JSON → 검증 → CSV

**Platform**: Windows (macOS/Linux 호환)
**Default Provider**: Google Gemini 3.5 Flash (`gemini-3.5-flash`, `thinking_level: minimal`)

## Common Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt

# Run
python app.py

# Build executable
python scripts/build_executable.py
```

## Architecture

```
Auto_PROMs_PSM_4_GUI/
├── app.py                    # Entry point: ui.run(native=True)
├── README.md
├── CLAUDE.md
├── requirements.txt
├── config.json               # Runtime settings, NO API keys (tracked)
├── .env                      # API keys only (git-ignored)
├── .env.example              # API key template (committed)
│
├── core/                     # 핵심 처리 모듈
│   ├── __init__.py           # PROJECT_ROOT, DATA_DIR 정의
│   ├── config.py             # ConfigManager (dotenv + pathlib)
│   ├── base_processor.py     # Abstract base: instructions, encode, process
│   ├── gemini_processor.py   # Gemini API (_call_api) — default
│   ├── claude_processor.py   # Claude API (_call_api)
│   ├── openai_processor.py   # OpenAI API (_call_api)
│   ├── validators.py         # SurveyValidator + EQ-5D cache
│   ├── pdf_processor.py      # PDF → image (PyMuPDF 300 DPI)
│   └── csv_generator.py      # Dict → CSV (35+ fields)
│
├── gui_ng/                   # NiceGUI-based GUI 모듈
│   ├── __init__.py
│   ├── styles.css            # CSS variables + component styles
│   ├── main_page.py          # Main UI + background pipeline
│   └── settings.py           # Settings dialog (4 tabs)
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
  ↓ _call_api() → Gemini / Claude / OpenAI Vision API
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

- **Strategy Pattern**: `BaseProcessor` ABC → `GeminiProcessor` (default) / `ClaudeProcessor` / `OpenAIProcessor`
- **Concurrency**: `ThreadPoolExecutor` + `SimpleRateLimiter` (semaphore), config에서 on/off
- **Auto-retry**: API 호출 실패 시 최대 2회 재시도, 지수 백오프 (1s, 2s)
- **GUI Framework**: NiceGUI 3.x + pywebview (native desktop window, no browser needed)
- **CSS**: Inline `<style>` injection (`_QUASAR_STYLE_OVERRIDES`) + cache-busted static CSS
- **Upload**: `ui.upload` for file selection + drag-and-drop; files staged in `uploaded_pdfs/` (separate from `temp_images/` which is wiped per-file)
- **Config**: `python-dotenv` for API keys, `config.json` for runtime settings
- **EQ-5D Caching**: `SurveyValidator._eq5d_table` class variable, loaded once
- **Package structure**: `core/` (relative imports), `gui_ng/` (relative imports), `data/` (static)

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
GEMINI_API_KEY=xxx
```

### config.json (runtime settings, tracked in git)
```json
{
  "api_settings": {
    "provider": "gemini",
    "openai_model": "gpt-5-mini",
    "claude_model": "claude-haiku-4-5-20251001",
    "gemini_model": "gemini-3.5-flash",
    "gemini_thinking_level": "minimal"
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

- **Window**: 640x820, native via pywebview (no browser)
- **Fonts**: AppleSDGothicNeo (macOS), 맑은 고딕 (Windows), Noto Sans CJK KR (Linux) — CSS font-family
- **Color Scheme**: "Refreshing Summer Fun" — CSS variables in `gui_ng/styles.css`
- **Icons**: Material Icons throughout (no emoji)
- **Components**: `gui_ng/main_page.py` (UI + pipeline), `gui_ng/settings.py` (settings dialog)

## Build Notes

- `scripts/build_executable.py` generates `.spec` dynamically — do NOT pass `--onefile`, `--windowed`, `--name` to PyInstaller
- Build mode: **onedir** (COLLECT step) — faster startup than onefile
- NiceGUI static assets bundled via hidden imports (nicegui, webview, fastapi, uvicorn, google.genai)
- `.env` is excluded from builds; `config.json` is bundled directly
- Portable package copies entire `dist/AutoSpineSurvey/` dir + `config.json`, `.env.example`

## Platform Notes

- **Path**: `pathlib.Path` throughout (cross-platform backslash handling)
- **Upload**: `ui.upload` with drag-and-drop; staged in `uploaded_pdfs/` (cross-platform)
- **Build**: PyInstaller onedir executable
- **Native Window**: pywebview — WKWebView (macOS), Edge WebView2 (Windows)
