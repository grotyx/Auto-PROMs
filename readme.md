# Auto Spine Survey v2.1

AI-powered spine surgery PROMs (Patient-Reported Outcome Measures) PDF data extraction system.

## Overview

Automatically analyzes spine surgery PROMs PDF files using AI vision APIs and extracts structured data into CSV format.

### Supported Surveys
- **VAS** (Visual Analog Scale) — Pain scores (back, buttock, lower extremity)
- **ODI** (Oswestry Disability Index) — 10 disability items
- **EQ-5D-5L** — Quality of life, 5 domains + calculated Korean value
- **painDETECT** — Neuropathic pain assessment

### Supported AI Models
- **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — Anthropic (default)
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

Edit `.env` with your API keys:
```
CLAUDE_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
```

On first run, `config_template.json` is copied to `config.json` automatically.
Default provider is Claude. To switch provider, edit `config.json`:
```json
{
    "api_settings": {
        "provider": "claude"
    }
}
```

### 3. Run

```bash
python main_gui.py
```

## Features

- **Modern GUI** — CustomTkinter with dark/light mode toggle
- **Drag-and-drop** — Drop PDF files directly (Windows); click to select (all platforms)
- **Concurrent processing** — Parallel page API calls via ThreadPoolExecutor
- **Dual AI support** — Switch between Claude (default) and OpenAI at runtime
- **EQ-5D value calculation** — Automatic lookup from Korean value set table
- **Real-time progress** — Per-page progress bar during AI processing

## Usage

1. Run `python main_gui.py`
2. Drag PDF files onto the drop zone (or click to select)
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

## Building Executable

```bash
python scripts/build_executable.py
```

Output:
- `dist/AutoSpineSurvey` (or `.exe` on Windows)
- `AutoSpineSurvey_Portable/` — ready-to-distribute package

### Portable Package Contents
```
AutoSpineSurvey_Portable/
├── AutoSpineSurvey(.exe)
├── config.json              # Template config (no API keys)
├── .env.example             # API key template
├── data/
│   ├── page_instruction.json
│   └── eq5d_value_k.csv
├── input_pdfs/
├── output_csv/
├── logs/
└── README.txt
```

> **Note**: Users must create their own `.env` with API keys. The portable package never includes secrets.

## Project Structure

```
Auto_PROMs_PSM_4_GUI/
├── main_gui.py               # GUI entry point
├── README.md
├── requirements.txt
├── config_template.json      # Config template (committed)
├── .env.example              # API key template (committed)
│
├── core/                     # Processing modules
│   ├── __init__.py           # PROJECT_ROOT, DATA_DIR
│   ├── config.py             # ConfigManager (dotenv + pathlib)
│   ├── base_processor.py     # Abstract base AI processor
│   ├── claude_processor.py   # Claude API processor (default)
│   ├── openai_processor.py   # OpenAI API processor
│   ├── validators.py         # Survey data validation + EQ-5D cache
│   ├── pdf_processor.py      # PDF → image conversion (PyMuPDF)
│   └── csv_generator.py      # CSV output generation
│
├── gui/                      # GUI modules
│   ├── main_window.py        # CustomTkinter main window
│   ├── settings_dialog.py    # Settings dialog (tabs, .env management)
│   └── widgets.py            # FileCard, LogPanel, DropZone
│
├── data/                     # Static data files
│   ├── page_instruction.json # AI prompts per survey page
│   └── eq5d_value_k.csv      # EQ-5D Korean value lookup table
│
└── scripts/                  # Build tools
    └── build_executable.py   # PyInstaller build script
```

## Configuration

### config.json

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

API keys are stored separately in `.env`, never in `config.json`.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `CLAUDE_API_KEY not found` | Create `.env` file with your API key. See `.env.example`. |
| No PDF files found | Place PDFs in `input_pdfs/` or use drag-and-drop in GUI. |
| Dependency errors | Ensure Python 3.9+, activate virtualenv, then `pip install -r requirements.txt`. |
| GUI won't start | Install `customtkinter`: `pip install customtkinter>=5.3.0` |
| Build fails | Ensure PyInstaller is installed: `pip install pyinstaller>=6.0.0` |

Detailed logs: `logs/spine_survey_*.log`

## Version History

### v2.1 (Current)
- Default provider changed to Claude Haiku 4.5
- Project structure reorganized: `core/`, `data/`, `scripts/` packages
- CLI removed (GUI only)
- Path management via `PROJECT_ROOT` / `DATA_DIR` in `core/__init__.py`

### v2.0
- Security: API keys moved to `.env` file (python-dotenv)
- Architecture: Abstract base processor class, validators module, EQ-5D caching
- Performance: Concurrent page processing (ThreadPoolExecutor, max 6 workers)
- GUI: Rewritten with CustomTkinter (dark/light mode, collapsible log panel)
- Build: PyInstaller build script

### v1.1
- GUI visual improvements
- API model updates (Claude Haiku 4.5, GPT-5 mini)

### v1.0
- Initial release with GUI and CLI
- Claude and OpenAI support
- Drag-and-drop PDF processing

## License

Copyright 2025 Sang-Min Park, Department of Orthopaedic Surgery, Seoul National University College of Medicine. All rights reserved.
