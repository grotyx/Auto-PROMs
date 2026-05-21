# Auto Spine Survey v2.1

AI 기반 척추 수술 PROMs (환자 보고형 결과 측정) PDF 데이터 자동 추출 시스템.

> English: [README.md](README.md)

## 개요

AI Vision API를 활용해 척추 수술 PROMs PDF를 자동으로 분석하고, 구조화된 데이터를 CSV로 추출합니다.

### 지원 설문지
- **VAS** (Visual Analog Scale) — 통증 점수 (허리, 엉덩이, 하지)
- **ODI** (Oswestry Disability Index) — 10개 장애 항목
- **EQ-5D-5L** — 삶의 질 5개 영역 + 한국형 가치(value) 자동 계산
- **painDETECT** — 신경병증성 통증 평가

### 지원 AI 모델
- **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — Anthropic (기본값)
- **GPT-5 mini** (`gpt-5-mini`) — OpenAI

## 빠른 시작

### 1. 설치

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. API 키 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력하세요:
```
CLAUDE_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
```

기본 Provider는 Claude입니다. 변경하려면 `config.json`을 수정하세요:
```json
{
    "api_settings": {
        "provider": "claude"
    }
}
```

### 3. 실행

```bash
python main_gui.py
```

## 주요 기능

- **모던 GUI** — CustomTkinter, 다크/라이트 모드 전환
- **드래그 앤 드롭** — Windows에서 PDF 직접 드롭 (다른 OS는 클릭 선택)
- **병렬 처리** — ThreadPoolExecutor로 페이지 단위 동시 API 호출
- **이중 AI 지원** — 실행 중 Claude (기본) ↔ OpenAI 전환
- **EQ-5D 가치 계산** — 한국형 가치 표 자동 조회
- **실시간 진행률** — 페이지별 처리 진행 표시

## 사용 방법

1. `python main_gui.py` 실행
2. 드롭 영역에 PDF를 끌어놓거나 클릭으로 선택
3. "처리 시작" 버튼 클릭
4. 결과는 `output_csv/`에 저장됨

### PDF 포맷
설문 PDF는 환자 1회 방문당 **6페이지** 구성:
| 페이지 | 설문 |
|------|--------|
| 0 | VAS (통증 점수) |
| 1-2 | ODI (장애 지수) |
| 3 | EQ-5D-5L (삶의 질) |
| 4-5 | painDETECT (신경병증성 통증) |

여러 설문이 포함된 PDF는 자동으로 6페이지 단위로 분할 처리됩니다.

## 실행 파일 빌드

```bash
python scripts/build_executable.py
```

출력:
- `dist/AutoSpineSurvey` (Windows의 경우 `.exe`)
- `AutoSpineSurvey_Portable/` — 배포용 패키지

### Portable 패키지 구성
```
AutoSpineSurvey_Portable/
├── AutoSpineSurvey(.exe)
├── config.json              # 설정 (API 키 미포함)
├── .env.example             # API 키 템플릿
├── data/
│   ├── page_instruction.json
│   └── eq5d_value_k.csv
├── input_pdfs/
├── output_csv/
├── logs/
└── README.txt
```

> **참고**: 사용자는 별도로 `.env`를 생성해 API 키를 입력해야 합니다. 배포 패키지에는 키가 절대 포함되지 않습니다.

## 프로젝트 구조

```
Auto_PROMs_PSM_4_GUI/
├── main_gui.py               # GUI 진입점
├── README.md                 # 영문 문서
├── README.ko.md              # 한글 문서
├── LICENSE                   # MIT License
├── requirements.txt
├── .env.example              # API 키 템플릿 (git tracked)
│
├── core/                     # 처리 모듈
│   ├── __init__.py           # PROJECT_ROOT, DATA_DIR 정의
│   ├── config.py             # ConfigManager (dotenv + pathlib)
│   ├── base_processor.py     # 추상 AI processor 베이스
│   ├── claude_processor.py   # Claude API processor (기본)
│   ├── openai_processor.py   # OpenAI API processor
│   ├── validators.py         # 설문 검증 + EQ-5D 캐시
│   ├── pdf_processor.py      # PDF → 이미지 변환 (PyMuPDF)
│   └── csv_generator.py      # CSV 출력 생성
│
├── gui/                      # GUI 모듈
│   ├── main_window.py        # CustomTkinter 메인 윈도우
│   ├── settings_dialog.py    # 설정 다이얼로그 (.env 관리 포함)
│   └── widgets.py            # FileCard, LogPanel, DropZone
│
├── data/                     # 정적 데이터 파일
│   ├── page_instruction.json # 페이지별 AI 프롬프트
│   └── eq5d_value_k.csv      # EQ-5D 한국형 가치 룩업 테이블
│
└── scripts/                  # 빌드/배포 스크립트
    └── build_executable.py   # PyInstaller 빌드 스크립트
```

## 설정

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

API 키는 `.env`에만 저장되며, `config.json`에는 절대 포함되지 않습니다.

## 문제 해결

| 문제 | 해결 방법 |
|---------|----------|
| `CLAUDE_API_KEY not found` | `.env` 파일을 만들고 API 키 입력. `.env.example` 참고. |
| PDF 파일이 인식되지 않음 | `input_pdfs/`에 PDF 배치 또는 GUI 드래그 앤 드롭 사용. |
| 의존성 오류 | Python 3.9+ 확인, 가상환경 활성화 후 `pip install -r requirements.txt`. |
| GUI가 실행되지 않음 | `customtkinter` 설치: `pip install customtkinter>=5.3.0` |
| 빌드 실패 | PyInstaller 설치 확인: `pip install pyinstaller>=6.0.0` |

상세 로그: `logs/spine_survey_*.log`

## 버전 히스토리

### v2.1 (현재)
- 기본 Provider를 Claude Haiku 4.5로 변경
- 프로젝트 구조 재정비: `core/`, `data/`, `scripts/` 패키지
- CLI 제거 (GUI 전용)
- `core/__init__.py`의 `PROJECT_ROOT` / `DATA_DIR` 기반 경로 관리

### v2.0
- 보안: API 키를 `.env`로 이동 (python-dotenv)
- 구조: 추상 베이스 processor, validators 모듈, EQ-5D 캐싱
- 성능: 페이지 병렬 처리 (ThreadPoolExecutor, 최대 6 worker)
- GUI: CustomTkinter로 재작성 (다크/라이트 모드, 접이식 로그 패널)
- 빌드: PyInstaller 빌드 스크립트

### v1.1
- GUI 시각 개선
- AI 모델 업데이트 (Claude Haiku 4.5, GPT-5 mini)

### v1.0
- 초기 릴리스 (GUI + CLI)
- Claude 및 OpenAI 지원
- 드래그 앤 드롭 PDF 처리

## 라이선스

본 프로젝트는 [MIT License](LICENSE)로 배포됩니다.

Copyright (c) 2025-2026 박상민 (Sang-Min Park)

### 제3자 콘텐츠 안내
- **EQ-5D-5L** 한국어판 및 가치 변환표: EuroQol Research Foundation의 라이선스 조건이 적용됩니다. 상업적/비상업적 사용자는 <https://euroqol.org> 에서 적절한 라이선스를 취득해야 합니다.
- **ODI** (Oswestry Disability Index) 한국어 번역본: 재배포 전 원저자의 저작권/라이선스 조건을 확인하세요.
- **painDETECT** 설문지: 원저작권자(Pfizer / Freynhagen 등)의 사용 조건이 적용됩니다.

MIT License는 본 저장소의 소스 코드에만 적용되며, 위 임상 평가도구 자체에는 적용되지 않습니다.
