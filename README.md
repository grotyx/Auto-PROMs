# Auto Spine Survey v2.2.1

AI-powered spine surgery PROMs (Patient-Reported Outcome Measures) PDF data extraction system.

## Overview

Automatically analyzes spine surgery PROMs PDF files using AI vision APIs and extracts structured data into CSV format.

### Supported Surveys
- **VAS** (Visual Analog Scale) — Pain scores (back, buttock, lower extremity)
- **ODI** (Oswestry Disability Index) — 10 disability items
- **EQ-5D-5L** — Quality of life, 5 domains + calculated Korean value
- **painDETECT** — Neuropathic pain assessment

### Supported AI Models
- **Gemini 3.1 Flash Lite** (`gemini-3.1-flash-lite-preview`) — Google (default)
- **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — Anthropic
- **GPT-5 mini** (`gpt-5-mini`) — OpenAI

## Quick Start

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. API Key Setup

```bash
cp .env.example .env
```

Edit `.env` with your API keys (only the provider you use is required):
```
CLAUDE_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
GEMINI_API_KEY=your-gemini-key-here
```

### 3. Run

```bash
python app.py
```

## Features

- **Native desktop window** — NiceGUI + pywebview (no browser needed)
- **Modern UI** — "Refreshing Summer Fun" color scheme with card-based layout
- **Click to select** — PDF file picker via native OS dialog
- **Drag-and-drop** — Drop PDF files directly onto the upload zone
- **Concurrent processing** — Parallel page API calls via ThreadPoolExecutor
- **Triple AI support** — Switch between Gemini (default), Claude, and OpenAI at runtime
- **Auto-retry** — Failed API calls automatically retry up to 2 times with backoff
- **EQ-5D value calculation** — Automatic lookup from Korean value set table
- **Real-time progress** — Per-page progress bar during AI processing
- **Processing summary** — Completion dialog with success/fail counts, surveys, elapsed time

## Usage

1. Run `python app.py`
2. Click the upload zone or drag-and-drop PDF files
3. Click "처리 시작" (Start Processing)
4. Results saved to `output_csv/`

### PDF Format
Each survey PDF contains **6 pages** per patient visit:
| Page | Survey |
|------|--------|
| 0 | VAS (pain scores) |
| 1-2 | ODI (disability index) |
| 3 | EQ-5D-5L (quality of life) |
| 4-5 | painDETECT (neuropathic pain) |

Multi-survey PDFs are automatically split into 6-page segments.

## Project Structure

```
Auto_PROMs_PSM_4_GUI/
├── app.py                    # Entry point: ui.run(native=True)
├── README.md
├── requirements.txt
├── config.json               # Runtime settings (no API keys)
├── .env                      # API keys only (git-ignored)
├── .env.example              # API key template (committed)
│
├── core/                     # Processing modules
│   ├── __init__.py           # PROJECT_ROOT, DATA_DIR
│   ├── config.py             # ConfigManager (dotenv + pathlib)
│   ├── base_processor.py     # Abstract base AI processor
│   ├── gemini_processor.py   # Gemini API processor (default)
│   ├── claude_processor.py   # Claude API processor
│   ├── openai_processor.py   # OpenAI API processor
│   ├── validators.py         # Survey data validation + EQ-5D cache
│   ├── pdf_processor.py      # PDF → image conversion (PyMuPDF)
│   └── csv_generator.py      # CSV output generation
│
├── gui_ng/                   # NiceGUI-based GUI modules
│   ├── __init__.py
│   ├── styles.css            # CSS variables + component styles
│   ├── main_page.py          # Main UI + background pipeline
│   └── settings.py           # Settings dialog (4 tabs)
│
├── data/                     # Static data files
│   ├── page_instruction.json # AI prompts per survey page
│   └── eq5d_value_k.csv      # EQ-5D Korean value lookup table
│
└── scripts/                  # Build tools
    └── build_executable.py   # PyInstaller build script
```

## Color Scheme — "Refreshing Summer Fun"

| Color | Hex | Usage |
|-------|-----|-------|
| Ocean Blue | `#219EBC` | Primary — header, progress bar, folder button |
| Dark Navy | `#023047` | Text, stop button |
| Amber | `#FFB703` | Settings icon accent |
| Orange | `#FB8500` | Start/action button |
| Light Sky | `#8ECAE6` | Borders, secondary button, badges |
| Sky Tint | `#EBF5FA` | Page background |

## Configuration

### config.json

```json
{
    "api_settings": {
        "provider": "gemini",
        "openai_model": "gpt-5-mini",
        "claude_model": "claude-haiku-4-5-20251001",
        "gemini_model": "gemini-3.1-flash-lite-preview"
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

API keys are stored separately in `.env`, never in `config.json`.

## Building Executable

```bash
python scripts/build_executable.py
```

Output:
- `dist/AutoSpineSurvey/` — onedir build (exe + dependencies)
- `AutoSpineSurvey_Portable/` — ready-to-distribute package

### Portable Package Contents
```
AutoSpineSurvey_Portable/
├── AutoSpineSurvey(.exe)    # + bundled dependencies
├── _internal/               # PyInstaller runtime files
├── config.json              # Settings (no API keys)
├── .env.example             # API key template
├── input_pdfs/
├── output_csv/
├── logs/
└── temp_images/
```

> **Note**: Users must create their own `.env` with API keys. The portable package never includes secrets.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `API_KEY not found` | Create `.env` file with your API key for the selected provider. See `.env.example`. |
| No PDF files found | Use the upload zone in GUI to select files. |
| Dependency errors | Ensure Python 3.9+, activate virtualenv, then `pip install -r requirements.txt`. |
| GUI won't start | Install GUI deps: `pip install nicegui pywebview` |
| Build fails | Ensure PyInstaller is installed: `pip install pyinstaller>=6.0.0` |

Detailed logs: `logs/spine_survey_*.log`

## Version History

### v2.2.1 (Current)
- Fixed CSV generation crash when `rc_id` extraction fails (`'0000None'` literal-int error)
- Survey data preserved when `rc_id` is missing — only `rc_id` cell left blank, all other fields kept
- Build script: added `--noconfirm` to PyInstaller call to avoid stale `dist/` overwrite failures

### v2.2.0
- Google Gemini support added (`gemini-3.1-flash-lite-preview` as new default)
- Triple AI provider support: Gemini, Claude, OpenAI — switchable at runtime
- Settings UI simplified: unified model dropdown per provider, API keys managed via `.env` only
- Build changed from PyInstaller onefile to onedir for faster startup
- PDF files sorted by filename before processing
- Auto-retry for failed API calls (2 retries with exponential backoff)
- Processing summary dialog: success/fail counts, survey count, elapsed time
- Config hot-reload (`reload_config()`) for seamless provider switching

### v2.1.1
- GUI migrated from CustomTkinter to NiceGUI 3.x + pywebview (native desktop window)
- Color scheme: "Refreshing Summer Fun" (ocean blue + amber + orange)
- Material Icons throughout (replaced emoji icons)
- No separate browser required — runs as a native OS window
- Default provider changed to Claude Haiku 4.5
- Project structure reorganized: `core/`, `data/`, `scripts/` packages
- CLI removed (GUI only)

### v2.0
- Security: API keys moved to `.env` file (python-dotenv)
- Architecture: Abstract base processor class, validators module, EQ-5D caching
- Performance: Concurrent page processing (ThreadPoolExecutor, max 6 workers)
- GUI: Rewritten with CustomTkinter (dark/light mode, collapsible log panel)
- Build: PyInstaller build script

### v1.0
- Initial release with GUI and CLI
- Claude and OpenAI support
- Drag-and-drop PDF processing

## License

Copyright 2025-2026 Sang-Min Park, Department of Orthopaedic Surgery, Seoul National University College of Medicine. All rights reserved.
