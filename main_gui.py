#!/usr/bin/env python3
"""
Spine Survey Processor - GUI Version
척추 설문지 자동 데이터 추출 프로그램 (GUI 버전)
"""

import sys
import os

def check_dependencies():
    """필수 의존성 확인"""
    missing_deps = []

    try:
        import tkinter
    except ImportError:
        missing_deps.append("tkinter")

    try:
        import customtkinter
    except ImportError:
        missing_deps.append("customtkinter")

    try:
        import dotenv
    except ImportError:
        missing_deps.append("python-dotenv")

    try:
        import fitz  # PyMuPDF
    except ImportError:
        missing_deps.append("PyMuPDF")

    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")

    try:
        import pandas
    except ImportError:
        missing_deps.append("pandas")

    try:
        import anthropic
    except ImportError:
        missing_deps.append("anthropic")

    if missing_deps:
        print("❌ 다음 패키지들이 설치되지 않았습니다:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\n다음 명령어로 설치해주세요:")
        print("pip install " + " ".join(missing_deps))
        return False

    return True

def main():
    """메인 실행 함수"""
    # 실행파일에서는 의존성 체크 건너뛰기
    if not hasattr(sys, 'frozen'):  # 개발 환경에서만 체크
        if not check_dependencies():
            print("\n필수 패키지를 설치한 후 다시 실행해주세요.")
            input("엔터 키를 눌러 종료...")
            sys.exit(1)
        
    # GUI 모듈 임포트 및 실행
    try:
        from gui.main_window import MainWindow
        from core.config import load_config, setup_folders
        
        print("🚀 Spine Survey Processor GUI 시작 중...")
        
        # 설정 로드 및 필요한 폴더 생성
        config = load_config()
        folders = config.get_folders()
        setup_folders(folders)
        
        # 메인 윈도우 생성 및 실행
        app = MainWindow()
        app.run()
        
    except Exception as e:
        print(f"❌ 프로그램 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        # GUI 모드에서는 input() 사용 불가
        if hasattr(sys, 'frozen'):  # 실행파일로 실행중인 경우
            import tkinter.messagebox as messagebox
            messagebox.showerror("프로그램 오류", f"프로그램 실행 중 오류가 발생했습니다:\n{str(e)}")
        else:
            input("\n엔터 키를 눌러 종료...")
        sys.exit(1)

if __name__ == "__main__":
    main()