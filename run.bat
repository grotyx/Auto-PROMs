@echo off
REM 필요한 디렉토리 생성
mkdir templates 2>nul
mkdir static\css 2>nul
mkdir logs 2>nul
mkdir input_pdfs 2>nul
mkdir output_csv 2>nul
mkdir temp_images 2>nul

REM HTML 파일 생성
echo ^<!DOCTYPE html^> > templates\index.html
echo ^<html lang="ko"^> >> templates\index.html
REM ... (templates/index.html 내용 계속) ...

REM CSS 파일 생성
echo /* 기본 설정 */ > static\css\styles.css
REM ... (static/css/styles.css 내용 계속) ...

REM 패키지 설치
pip install -r requirements.txt

REM 애플리케이션 실행
uvicorn app:app --host 0.0.0.0 --port 8000 --reload