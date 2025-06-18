'''
pytest 설정 파일
이 파일은 pytest의 설정과 fixture를 정의합니다.
주로 테스트 환경을 구성하고, 데이터베이스 연결, OpenAI 클라이언트 모킹 등을 포함합니다.
'''
import pytest
import asyncio
import tempfile
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

# pytest 설정
pytest_plugins = ['pytest_asyncio']

# conftest.py
import sys
import os

# src 폴더의 절대 경로를 PYTHONPATH에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))