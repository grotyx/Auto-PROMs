# Auto Spine Survey v2.2.3

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
- **Gemini 3.5 Flash** (`gemini-3.5-flash`) — Google (기본값)
- **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — Anthropic
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

`.env` 파일에 사용할 제공자의 API 키만 입력하면 됩니다:
```
CLAUDE_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-proj-your-key-here
GEMINI_API_KEY=your-gemini-key-here
```

### 3. 실행

```bash
python app.py
```

## 주요 기능

- **네이티브 데스크톱 창** — NiceGUI + pywebview (브라우저 불필요)
- **모던 UI** — "Refreshing Summer Fun" 컬러 스킴, 카드 기반 레이아웃
- **클릭 선택** — OS 네이티브 다이얼로그로 PDF 파일 선택
- **드래그 앤 드롭** — 업로드 영역에 PDF 파일을 직접 드롭
- **동시 처리** — ThreadPoolExecutor 기반 병렬 페이지 API 호출
- **3개 AI 제공자** — Gemini(기본), Claude, OpenAI 런타임 전환
- **자동 재시도** — API 호출 실패 시 최대 2회 지수 백오프 재시도
- **EQ-5D 가치 계산** — 한국형 가치 세트 테이블 자동 룩업
- **실시간 진행률** — AI 처리 중 페이지 단위 진행 표시
- **처리 요약** — 성공/실패 수, 설문 수, 소요 시간 완료 다이얼로그

## 사용 방법

1. `python app.py` 실행
2. 업로드 영역 클릭 또는 PDF 드래그 앤 드롭
3. "처리 시작" 클릭
4. 결과는 `output_csv/`에 저장

### PDF 형식
설문 PDF는 환자 방문당 **6페이지**로 구성됩니다:
| 페이지 | 설문 |
|------|--------|
| 0 | VAS (통증 점수) |
| 1-2 | ODI (장애 지수) |
| 3 | EQ-5D-5L (삶의 질) |
| 4-5 | painDETECT (신경병증성 통증) |

여러 설문이 담긴 PDF는 자동으로 6페이지 단위로 분할됩니다.

## 프로젝트 구조

```
Auto_PROMs_PSM_4_GUI/
├── app.py                    # 진입점: ui.run(native=True)
├── README.md                 # 영문 문서
├── README.ko.md              # 한글 문서
├── LICENSE                   # MIT 라이선스
├── requirements.txt
├── config.json               # 런타임 설정 (API 키 없음)
├── .env                      # API 키 전용 (git 제외)
├── .env.example              # API 키 템플릿 (커밋됨)
│
├── core/                     # 처리 모듈
│   ├── __init__.py           # PROJECT_ROOT, DATA_DIR
│   ├── config.py             # ConfigManager (dotenv + pathlib)
│   ├── base_processor.py     # 추상 베이스 AI 프로세서
│   ├── gemini_processor.py   # Gemini API 프로세서 (기본값)
│   ├── claude_processor.py   # Claude API 프로세서
│   ├── openai_processor.py   # OpenAI API 프로세서
│   ├── validators.py         # 설문 데이터 검증 + EQ-5D 캐시
│   ├── pdf_processor.py      # PDF → 이미지 변환 (PyMuPDF)
│   └── csv_generator.py      # CSV 출력 생성
│
├── gui_ng/                   # NiceGUI 기반 GUI 모듈
│   ├── __init__.py
│   ├── styles.css            # CSS 변수 + 컴포넌트 스타일
│   ├── main_page.py          # 메인 UI + 백그라운드 파이프라인
│   └── settings.py           # 설정 다이얼로그 (4개 탭)
│
├── data/                     # 정적 데이터 파일
│   ├── page_instruction.json # 페이지별 AI 프롬프트
│   └── eq5d_value_k.csv      # EQ-5D 한국형 가치 룩업 테이블
│
└── scripts/                  # 빌드 도구
    └── build_executable.py   # PyInstaller 빌드 스크립트
```

## 설정

### config.json

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

API 키는 `.env`에만 저장하며, `config.json`에는 절대 넣지 않습니다.

## 실행 파일 빌드

```bash
python scripts/build_executable.py
```

출력:
- `dist/AutoSpineSurvey/` — onedir 빌드 (exe + 의존성)
- `AutoSpineSurvey_Portable/` — 배포용 패키지

### 포터블 패키지 구성
```
AutoSpineSurvey_Portable/
├── AutoSpineSurvey(.exe)    # + 번들 의존성
├── _internal/               # PyInstaller 런타임 파일
├── config.json              # 설정 (API 키 없음)
├── .env.example             # API 키 템플릿
├── input_pdfs/
├── output_csv/
├── logs/
└── temp_images/
```

> **참고**: 사용자가 직접 `.env` 파일을 만들어 API 키를 넣어야 합니다. 포터블 패키지에는 어떤 비밀 정보도 포함되지 않습니다.

## 문제 해결

| 문제 | 해결 방법 |
|---------|----------|
| `API_KEY not found` | 선택한 제공자의 API 키로 `.env` 파일 생성. `.env.example` 참고. |
| PDF 파일 없음 | GUI 업로드 영역에서 파일 선택. |
| 의존성 오류 | Python 3.9+ 확인, 가상환경 활성화 후 `pip install -r requirements.txt`. |
| GUI 실행 안 됨 | GUI 의존성 설치: `pip install nicegui pywebview` |
| 빌드 실패 | PyInstaller 설치 확인: `pip install pyinstaller>=6.0.0` |

상세 로그: `logs/spine_survey_*.log`

## 버전 이력

전체 버전 이력은 [README.md](README.md#version-history)를 참고하세요.

### v2.2.3 (현재)

**보안**
- 서버를 `127.0.0.1`에만 바인딩 (브라우저 폴백 모드가 LAN 전체에 노출되던 문제 수정)
- 정적 파일 서빙을 `styles.css`로 제한 (소스 코드 노출 차단)
- 업로드 파일명 경로 탐색 방지 및 중복 파일명 처리
- 환자 데이터(PHI)를 로그에 기록하지 않음 — 필드명/개수만 기록
- 비정상 종료 시 남은 환자 데이터를 시작 시 자동 정리

**수정**
- `config.json`의 출력 폴더·타임스탬프 설정 실제 반영
- 설정 저장 시 `gemini_thinking_level` 유실 수정
- CSV의 `rc_id`를 0-패딩 문자열로 출력 (REDCap ID 매칭)
- 전 페이지 실패 설문이 성공으로 집계되던 문제 수정
- `max_tokens`/`temperature` 설정이 API 호출에 반영
- `nicegui>=3.0.0` 요구사항 명시

## 저자

**박상민 (Sang-Min Park, MD)**
서울대학교 의과대학 정형외과학교실
Email: <psmini@snu.ac.kr>

## 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE)로 배포됩니다.

Copyright (c) 2025-2026 Sang-Min Park

### 제3자 콘텐츠
- **EQ-5D-5L** 한국어판 및 가치 세트: EuroQol Research Foundation의 라이선스 조건을 따릅니다.
  상업적/비상업적 사용자는 <https://euroqol.org>에서 적절한 라이선스를 취득해야 합니다.
- **ODI** (Oswestry Disability Index) 한국어 번역: 재배포 전 원 도구의 저작권/라이선스 조건을 확인하세요.
- **painDETECT** 설문지: 원 저작권자(Pfizer / Freynhagen et al.)의 조건을 따릅니다.

MIT 라이선스는 이 저장소의 소스 코드에만 적용되며, 기반 임상 도구에는 적용되지 않습니다.
