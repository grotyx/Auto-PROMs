from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
import tempfile
from datetime import datetime
import logging
import uuid
from pathlib import Path

# Import existing processor classes
from pdf_processor import PDFProcessor
from claude_processor import ClaudeProcessor
from csv_generator import CSVGenerator
from config import CLAUDE_API_KEY, setup_logging, setup_folders, INPUT_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER

# Initialize FastAPI
app = FastAPI(title="임상 설문지 PDF 처리기")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup logging
logger = setup_logging()

# Ensure directories exist
setup_folders()

# Track processing status
processing_jobs = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """홈페이지 렌더링"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload/")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """PDF 파일 업로드 처리"""
    # 파일 확장자 확인
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
    
    # 고유한 작업 ID 생성
    job_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"results_{timestamp}.csv"
    
    # 임시 PDF 파일 경로
    pdf_path = os.path.join(INPUT_FOLDER, f"upload_{job_id}.pdf")
    
    try:
        # 업로드된 파일 저장
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 상태 추적
        processing_jobs[job_id] = {
            "status": "processing",
            "filename": output_filename,
            "progress": 0
        }
        
        # 백그라운드에서 PDF 처리
        background_tasks.add_task(process_pdf_background, pdf_path, job_id, output_filename)
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "PDF 처리가 시작되었습니다."
        }
    except Exception as e:
        logger.error(f"파일 업로드 오류: {str(e)}")
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    """작업 상태 확인"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    
    return processing_jobs[job_id]

@app.get("/download/{filename}")
async def download_csv(filename: str):
    """CSV 파일 다운로드"""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    
    return FileResponse(
        file_path,
        media_type="text/csv",
        filename=filename
    )

async def process_pdf_background(pdf_path: str, job_id: str, output_filename: str):
    """백그라운드에서 PDF 파일 처리"""
    temp_dir = os.path.join(TEMP_FOLDER, job_id)
    os.makedirs(temp_dir, exist_ok=True)
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    
    # 작업 진행 상태 업데이트 콜백 함수
    def update_progress(progress: int, status_message: str = None):
        # 실시간으로 상태 업데이트를 위해 즉시 딕셔너리 업데이트
        processing_jobs[job_id]["progress"] = progress
        if status_message:
            processing_jobs[job_id]["status_message"] = status_message
            logger.info(f"Job {job_id}: {progress}% - {status_message}")
    
    try:
        # PDF 처리 시작
        logger.info(f"PDF 처리 중: {pdf_path}")
        update_progress(0, "PDF 파일 분석 중...")
        processing_jobs[job_id]["status"] = "processing_pdf"
        
        pdf_processor = PDFProcessor(pdf_path, temp_dir)
        processed_images = pdf_processor.process_pdf()
        
        # 총 페이지 수와 설문지 수 계산
        total_pages = len(processed_images)
        total_surveys = total_pages // 6
        
        update_progress(10, f"PDF 분석 완료. 총 {total_pages}페이지 발견.")
        
        # Claude API 처리
        processing_jobs[job_id]["status"] = "analyzing"
        update_progress(10, "페이지 분석 시작...")
        
        claude_processor = ClaudeProcessor(CLAUDE_API_KEY)
        # 진행 상태 콜백 함수 전달
        survey_data = claude_processor.process_images(processed_images, update_progress)
        
        # CSV 생성
        update_progress(70, "CSV 파일 생성 중...")
        processing_jobs[job_id]["status"] = "generating_csv"
        
        if survey_data and len(survey_data) > 0:
            csv_generator = CSVGenerator(output_path)
            csv_generator.generate_csv(survey_data)
            logger.info(f"CSV 생성 완료: {output_path}")
            
            update_progress(100, "처리 완료!")
            processing_jobs[job_id]["status"] = "completed"
            processing_jobs[job_id]["download_url"] = f"/download/{output_filename}"
        else:
            logger.warning("유효한 설문 데이터를 찾을 수 없습니다.")
            processing_jobs[job_id]["status"] = "error"
            processing_jobs[job_id]["error"] = "유효한 설문 데이터를 찾을 수 없습니다."
    except Exception as e:
        logger.error(f"처리 오류: {str(e)}")
        processing_jobs[job_id]["status"] = "error"
        processing_jobs[job_id]["error"] = str(e)
    finally:
        # 임시 파일 정리
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)