from dotenv import load_dotenv
import os
import json
import logging
import sys

# 현재 스크립트의 디렉토리를 기준으로 경로 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EQ5D_CSV_PATH = os.path.join(SCRIPT_DIR, 'eq5d_value_k.csv')
print(f"Script directory: {SCRIPT_DIR}")

# 기본 설정값
DEFAULT_CONFIG = {
    "CLAUDE_API_KEY": "",
    "INPUT_FOLDER": "input_pdfs",
    "OUTPUT_FOLDER": "output_csv",
    "TEMP_FOLDER": "temp_images"
}

def load_config():
    """설정 파일 로드"""
    config_path = os.path.join(SCRIPT_DIR, 'config.json')
    print(f"Looking for config at: {config_path}")
    
    try:
        # .env 파일에서 환경 변수 로드
        print("Trying to load .env file...")
        load_dotenv(override=True)
        
        # API 키를 환경 변수에서 가져오기
        api_key = os.getenv('CLAUDE_API_KEY')
        if api_key:
            print("Found API key in environment variables")
        
        # config.json이 없으면 생성
        if not os.path.exists(config_path):
            print(f"Config file not found at: {config_path}")
            default_config = DEFAULT_CONFIG.copy()
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created default config at: {config_path}")
        
        # config.json 로드
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        # API 키 처리
        if api_key:
            config['CLAUDE_API_KEY'] = api_key
        elif not config.get('CLAUDE_API_KEY'):
            print("API key not found in environment variables or config.json")
            print("Please set CLAUDE_API_KEY in .env file or config.json")
            sys.exit(1)
            
        # 설정 내용 출력 (API 키는 제외)
        safe_config = config.copy()
        safe_config['CLAUDE_API_KEY'] = '********'
        print(f"Loaded config: {safe_config}")
            
        return config
        
    except Exception as e:
        print(f"Error loading config: {str(e)}")
        sys.exit(1)


# 설정 로드 및 전역 변수 설정
CONFIG = load_config()
CLAUDE_API_KEY = CONFIG['CLAUDE_API_KEY']
INPUT_FOLDER = CONFIG['INPUT_FOLDER']
OUTPUT_FOLDER = CONFIG['OUTPUT_FOLDER']
TEMP_FOLDER = CONFIG['TEMP_FOLDER']

# 로깅 설정
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # 파일 핸들러
    if not os.path.exists('logs'):
        os.makedirs('logs')
    file_handler = logging.FileHandler('logs/survey_processor.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# 폴더 생성
def setup_folders():
    folders = [INPUT_FOLDER, OUTPUT_FOLDER, TEMP_FOLDER]
    for folder in folders:
        os.makedirs(folder, exist_ok=True)