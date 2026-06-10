"""Core processing modules for Auto Spine Survey v2.2.3"""

import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    # PyInstaller frozen executable
    PROJECT_ROOT = Path(sys.executable).parent
    DATA_DIR = Path(getattr(sys, '_MEIPASS', PROJECT_ROOT)) / 'data'
else:
    # Development: core/ -> project root
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_ROOT / 'data'
