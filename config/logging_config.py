import logging
import os
from logging.handlers import RotatingFileHandler

from colorlog import ColoredFormatter

# 로그 디렉토리 생성
os.makedirs("logs", exist_ok=True)

# root logger 초기화
logger = logging.getLogger("request_time_logger")
logger.setLevel(logging.INFO)

# 이미 핸들러 있으면 중복 등록 안 하도록
if not logger.handlers:
    # 콘솔 핸들러 (컬러)
    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s | %(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    console_handler.setFormatter(console_formatter)

    # 파일 핸들러
    file_handler = RotatingFileHandler(
        "logs/request_time.log", maxBytes=5_000_000, backupCount=3
    )
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
