import logging
import os
from pdf_processor import PDFProcessor
from claude_processor import ClaudeProcessor
from csv_generator import CSVGenerator
from config import load_config, setup_logging, setup_folders

def main():
    try:
        print("Starting main function...")
        
        # 스크립트 디렉토리 경로 가져오기
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        print(f"Starting program in directory: {SCRIPT_DIR}")

        # 설정 로드
        print("About to load config...")
        config = load_config()
        print("Config loaded, getting API key...")
        CLAUDE_API_KEY = config.get('CLAUDE_API_KEY')
        if not CLAUDE_API_KEY:
            raise ValueError("API key not found in config")
        print("API key loaded successfully")

        # 절대 경로로 폴더 경로 설정
        print("Setting up folder paths...")
        INPUT_FOLDER = os.path.join(SCRIPT_DIR, config['INPUT_FOLDER'])
        OUTPUT_FOLDER = os.path.join(SCRIPT_DIR, config['OUTPUT_FOLDER'])
        TEMP_FOLDER = os.path.join(SCRIPT_DIR, config['TEMP_FOLDER'])
        
        print(f"Input folder: {INPUT_FOLDER}")
        print(f"Output folder: {OUTPUT_FOLDER}")
        print(f"Temp folder: {TEMP_FOLDER}")
        
        # 폴더 생성
        print("Creating folders if they don't exist...")
        for folder in [INPUT_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]:
            if not os.path.exists(folder):
                print(f"Creating folder: {folder}")
                os.makedirs(folder)
            print(f"Folder exists: {folder}")

        print("Setting up logging...")
        # 로깅 설정
        logger = setup_logging()
        setup_folders()
        
        logger.info("Starting survey processing...")
    
        # 입력 PDF 처리
        pdf_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.pdf')]
        if not pdf_files:
            logger.error("No PDF files found in input folder")
            return
                    
        # 모든 PDF의 결과를 저장할 리스트
        all_survey_data = []
                
        for pdf_file in pdf_files:
            pdf_path = os.path.join(INPUT_FOLDER, pdf_file)
            logger.info(f"Processing PDF file: {pdf_path}")
                
            try:
                # PDF 처리
                pdf_processor = PDFProcessor(pdf_path, TEMP_FOLDER)
                processed_images = pdf_processor.process_pdf()
                
                # Claude API 처리
                logger.info("Starting CLAUDE API processing...")
                claude_processor = ClaudeProcessor(CLAUDE_API_KEY)
                survey_data = claude_processor.process_images(processed_images)
                
                # survey_data가 None이 아니고 데이터가 있는 경우에만 추가
                if survey_data and len(survey_data) > 0:
                    all_survey_data.extend(survey_data)
                    logger.info(f"Successfully added {len(survey_data)} surveys from {pdf_file}")
                else:
                    logger.warning(f"No valid survey data found in {pdf_file}")
                
                logger.info(f"Completed processing {pdf_file}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                continue
                
            finally:
                # 임시 파일 정리
                logger.info("Cleaning up temporary files...")
                import shutil
                if os.path.exists(TEMP_FOLDER):
                    shutil.rmtree(TEMP_FOLDER)
                    os.makedirs(TEMP_FOLDER)
        
        # 모든 PDF 처리가 완료된 후 하나의 CSV 생성
        try:
            if all_survey_data and len(all_survey_data) > 0:
                logger.info(f"Generating combined CSV file with {len(all_survey_data)} surveys...")
                output_path = os.path.join(OUTPUT_FOLDER, 'combined_results.csv')
                csv_generator = CSVGenerator(output_path)
                df = csv_generator.generate_csv(all_survey_data)
                if df is not None:
                    logger.info(f"Combined CSV file generated at {output_path}")
                else:
                    logger.warning("No CSV file was generated due to invalid data")
            else:
                logger.warning("No valid survey data to generate CSV file")
        except Exception as e:
            logger.error(f"Error generating CSV file: {str(e)}")
            
        logger.info("All processing completed successfully")
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        print("Starting program...")
        main()
        print("Program completed successfully")
    except Exception as e:
        print(f"Program failed with error: {str(e)}")
        raise