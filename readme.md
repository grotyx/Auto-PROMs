# Auto_PROMs_PSM

자동화된 임상 설문지 PDF 처리 애플리케이션입니다. 이 프로그램은 설문지 PDF를 분석하여 구조화된 데이터로 변환합니다.

## 기능

- PDF 설문지를 이미지로 변환하고 전처리
- Claude API를 활용하여 설문지 내용 추출
- 추출된 데이터를 CSV 파일로 변환
- 웹 인터페이스를 통한 파일 업로드 및 결과 다운로드

## 필수 요구사항

- Docker 및 Docker Compose 설치
- Claude API 키 (Anthropic)

## 실행 방법

### Docker Compose로 실행하기

1. 이 저장소를 복제합니다:
   ```bash
   git clone https://github.com/grotyx/Auto_PROMs.git
   cd Auto_PROMs
   ```

2. `.env.example` 파일을 `.env`로 복사하고 API 키를 설정합니다:
   ```bash
   cp .env.example .env
   # .env 파일을 편집하여 CLAUDE_API_KEY 값을 설정하세요
   ```

3. Docker Compose로 애플리케이션을 실행합니다:
   ```bash
   docker-compose up -d
   ```

4. 웹 브라우저에서 http://localhost:8000 으로 접속합니다.

### 입력 및 출력

- PDF 파일을 `input_pdfs` 디렉토리에 넣거나 웹 인터페이스를 통해 업로드하세요
- 처리된 CSV 파일은 `output_csv` 디렉토리에 저장되지만, 다운로드 가능합니다.

## 개발 환경 설정

Docker 없이 로컬에서 개발하려면:

1. Python 3.9 이상 설치
2. 가상 환경 생성 및 활성화:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```
4. 시스템 의존성 설치:
   - Ubuntu/Debian: `sudo apt-get install poppler-utils libgl1-mesa-glx`
   - macOS: `brew install poppler`
   - Windows: poppler 바이너리 수동 설치 필요

5. 애플리케이션 실행:
   ```bash
   python -m uvicorn app:app --reload
   ```

## 라이선스

[라이선스 정보를 여기에 추가하세요]