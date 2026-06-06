import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

from . import PROJECT_ROOT

# 프로젝트 루트 기준 경로
SCRIPT_DIR = PROJECT_ROOT

# .env 파일 로드
_env_path = SCRIPT_DIR / ".env"
load_dotenv(dotenv_path=_env_path)

# 기본 설정값 (API 키는 .env에서 관리)
DEFAULT_CONFIG = {
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
        "concurrent_enabled": True,
        "max_concurrent_requests": 6
    },
    "output": {
        "csv_filename": "spine_survey_results.csv",
        "include_timestamps": True,
        "backup_results": True
    }
}

class ConfigManager:
    def __init__(self, config_filename: str = "config.json"):
        self.config_path = SCRIPT_DIR / config_filename
        self.config = self._load_or_create_config()

    def _load_or_create_config(self) -> Dict[str, Any]:
        """설정 파일 로드 또는 생성"""
        try:
            if not self.config_path.exists():
                print(f"Config file not found at: {self.config_path}")
                self._create_default_config()
                print(f"Created default config at: {self.config_path}")
                # GUI 모드에서는 종료하지 않고 기본 설정 사용
                if any(m in sys.modules for m in ('gui', 'tkinter', 'nicegui')):
                    print("Using default configuration. Please update API key in Settings.")
                    return DEFAULT_CONFIG
                else:
                    print("Please update the API key in .env file and run again.")
                    sys.exit(1)

            # config.json 로드
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 설정 유효성 검사
            self._validate_config(config)

            # 설정 내용 출력
            self._print_config_summary(config)

            return config

        except Exception as e:
            print(f"Error loading config: {str(e)}")
            sys.exit(1)

    def _create_default_config(self):
        """기본 설정 파일 생성"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error creating default config: {str(e)}")
            sys.exit(1)

    def _validate_config(self, config: Dict[str, Any]):
        """설정 유효성 검사"""
        # 필수 섹션 확인
        required_sections = ["api_settings", "folders", "processing", "output"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")

        # API 설정 확인
        api_provider = config["api_settings"].get("provider", "").lower()
        if api_provider not in ["openai", "claude", "gemini"]:
            raise ValueError("API provider must be 'openai', 'claude', or 'gemini'")

        # .env 파일 존재 확인 (CLI 모드에서만 경고)
        is_gui_mode = any(m in sys.modules for m in ('gui', 'tkinter', 'nicegui'))
        if not is_gui_mode:
            api_key = self.get_api_key_for_provider(api_provider)
            if not api_key:
                env_var = "OPENAI_API_KEY" if api_provider == "openai" else "CLAUDE_API_KEY"
                raise ValueError(
                    f"{env_var} not found. "
                    f"Please create a .env file at {_env_path} with your API key."
                )

    def _print_config_summary(self, config: Dict[str, Any]):
        """설정 요약 출력"""
        provider = config["api_settings"]["provider"].lower()
        if provider == "openai":
            model = config["api_settings"].get("openai_model", "Unknown")
        elif provider == "claude":
            model = config["api_settings"].get("claude_model", "Unknown")
        elif provider == "gemini":
            model = config["api_settings"].get("gemini_model", "Unknown")
        else:
            model = "Unknown"

        # API 키 상태 확인
        api_key = self.get_api_key_for_provider(provider)
        key_status = f"{api_key[:8]}...{api_key[-4:]}" if api_key else "Not set (check .env file)"

        print("=== Configuration Summary ===")
        print(f"API Provider: {config['api_settings']['provider']}")
        print(f"Model: {model}")
        print(f"API Key: {key_status}")
        print(f"Input Folder: {config['folders']['input_folder']}")
        print(f"Output Folder: {config['folders']['output_folder']}")
        print("=============================")

    @staticmethod
    def get_api_key_for_provider(provider: str) -> str:
        """주어진 제공자의 API 키를 환경변수에서 반환"""
        provider = provider.lower()
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY", "")
        elif provider == "claude":
            return os.getenv("CLAUDE_API_KEY", "")
        elif provider == "gemini":
            return os.getenv("GEMINI_API_KEY", "")
        return ""

    def get_api_key(self) -> str:
        """현재 설정된 API 제공자의 API 키 반환 (환경변수에서)"""
        provider = self.config["api_settings"]["provider"].lower()
        key = self.get_api_key_for_provider(provider)
        if not key:
            env_vars = {
                "openai": "OPENAI_API_KEY",
                "claude": "CLAUDE_API_KEY",
                "gemini": "GEMINI_API_KEY",
            }
            env_var = env_vars.get(provider, "API_KEY")
            raise ValueError(
                f"{env_var} not found in environment. "
                f"Please set it in the .env file at {_env_path}"
            )
        return key

    def get_model(self) -> str:
        """현재 설정된 API 제공자의 모델명 반환"""
        provider = self.config["api_settings"]["provider"].lower()
        if provider == "openai":
            return self.config["api_settings"].get("openai_model", "gpt-5-mini")
        elif provider == "claude":
            return self.config["api_settings"].get("claude_model", "claude-haiku-4-5-20251001")
        elif provider == "gemini":
            return self.config["api_settings"].get("gemini_model", "gemini-3.5-flash")
        else:
            raise ValueError(f"Unknown API provider: {provider}")

    def get_gemini_thinking_level(self) -> str:
        """Gemini thinking_level 반환 (없으면 'minimal')"""
        return self.config["api_settings"].get("gemini_thinking_level", "minimal")

    def get_provider(self) -> str:
        """현재 설정된 API 제공자 반환"""
        return self.config["api_settings"]["provider"].lower()

    def get_folders(self) -> Dict[str, str]:
        """폴더 경로들을 절대 경로로 반환"""
        folders = {}
        for key, folder_name in self.config["folders"].items():
            folder_path = str(SCRIPT_DIR / folder_name)
            folders[key] = folder_path

            # output_folder와 logs_folder는 자동 생성
            if key in ['output_folder', 'logs_folder'] and not os.path.exists(folder_path):
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    print(f"Auto-created {key}: {folder_path}")
                except Exception as e:
                    print(f"Failed to create {key}: {e}")

        return folders

    def get_processing_config(self) -> Dict[str, Any]:
        """처리 관련 설정 반환"""
        return self.config["processing"]

    def get_output_config(self) -> Dict[str, Any]:
        """출력 관련 설정 반환"""
        return self.config["output"]

def setup_logging(log_folder: str) -> logging.Logger:
    """로깅 설정"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 파일 핸들러
    log_path = Path(log_folder)
    if not log_path.exists():
        log_path.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(str(log_path / 'spine_survey_processor.log'))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def setup_folders(folders: Dict[str, str]):
    """필요한 폴더들 생성"""
    for folder_name, folder_path in folders.items():
        try:
            # 절대 경로로 변환
            abs_path = Path(folder_path).resolve()
            # 폴더가 없으면 생성
            if not abs_path.exists():
                abs_path.mkdir(parents=True, exist_ok=True)
                print(f"Created folder: {abs_path}")
            else:
                print(f"Folder exists: {abs_path}")
        except Exception as e:
            print(f"Error creating folder {abs_path}: {str(e)}")
            # 권한 문제 등으로 생성 실패시 현재 디렉토리에 생성 시도
            try:
                fallback_path = Path.cwd() / Path(folder_path).name
                if not fallback_path.exists():
                    fallback_path.mkdir(parents=True, exist_ok=True)
                    print(f"Created fallback folder: {fallback_path}")
            except:
                raise

# 전역 설정 관리자 인스턴스를 지연 초기화
_config_manager = None

def load_config() -> 'ConfigManager':
    """설정 관리자 인스턴스 반환 (지연 초기화)"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config() -> 'ConfigManager':
    """설정 관리자를 강제로 다시 로드 (설정 변경 후 호출)"""
    global _config_manager
    _config_manager = ConfigManager()
    return _config_manager

