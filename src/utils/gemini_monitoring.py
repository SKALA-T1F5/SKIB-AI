"""
Gemini 모델 토큰 사용량 및 비용 모니터링 유틸리티

Google Gemini API 공식 문서 기반으로 구현:
https://ai.google.dev/gemini-api/docs/tokens?hl=ko&lang=python
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import google.generativeai as genai
from langsmith import traceable


class GeminiMonitor:
    """Gemini 모델 토큰 사용량 및 비용 모니터링 클래스"""
    
    # 2024년 기준 Gemini API 가격 정보 (USD per 1M tokens)
    PRICING = {
        # Gemini 1.5 Pro
        "gemini-1.5-pro": {
            "input": 1.25,  # $1.25 per 1M tokens
            "output": 5.00,  # $5.00 per 1M tokens
            "context_cache": 0.3125,  # $0.3125 per 1M tokens
        },
        "gemini-1.5-pro-latest": {
            "input": 1.25,
            "output": 5.00,
            "context_cache": 0.3125,
        },
        
        # Gemini 1.5 Flash (Free tier available)
        "gemini-1.5-flash": {
            "input": 0.075,  # $0.075 per 1M tokens (after free tier)
            "output": 0.30,   # $0.30 per 1M tokens (after free tier)
            "context_cache": 0.01875,
        },
        "gemini-1.5-flash-latest": {
            "input": 0.075,
            "output": 0.30,
            "context_cache": 0.01875,
        },
        "gemini-1.5-flash-8b": {
            "input": 0.0375,  # $0.0375 per 1M tokens
            "output": 0.15,   # $0.15 per 1M tokens
            "context_cache": 0.009375,
        },
        
        # Gemini 2.0 Flash
        "gemini-2.0-flash": {
            "input": 0.10,   # $0.10 per 1M tokens
            "output": 0.40,  # $0.40 per 1M tokens
        },
        "gemini-2.0-flash-exp": {
            "input": 0.10,
            "output": 0.40,
        },
        
        # Gemini 2.5 Flash
        "gemini-2.5-flash": {
            "input": 0.075,
            "output": 0.30,
        },
        "gemini-2.5-flash-exp": {
            "input": 0.075,
            "output": 0.30,
        },
        
        # Gemini 2.5 Pro (Most expensive)
        "gemini-2.5-pro": {
            "input": 1.25,   # $1.25 per 1M tokens (up to 200k tokens)
            "output": 10.00,  # $10.00 per 1M tokens (up to 200k tokens)
            "input_large": 2.50,   # $2.50 per 1M tokens (>200k tokens)
            "output_large": 15.00,  # $15.00 per 1M tokens (>200k tokens)
        },
        
        # Gemini 1.0 Pro (Legacy)
        "gemini-1.0-pro": {
            "input": 0.50,   # $0.50 per 1M tokens
            "output": 1.50,  # $1.50 per 1M tokens
        },
        "gemini-pro": {  # Alias for gemini-1.0-pro
            "input": 0.50,
            "output": 1.50,
        },
    }
    
    # 멀티모달 토큰 비용
    MULTIMODAL_TOKENS = {
        "image_small": 258,      # Images ≤ 384x384
        "video_per_second": 263, # Video tokens per second
        "audio_per_second": 32,  # Audio tokens per second
    }
    
    def __init__(self, log_file: str = "data/logs/gemini_usage.jsonl"):
        """
        Args:
            log_file: 사용량 로그를 저장할 파일 경로
        """
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def count_tokens_before_request(self, model_name: str, prompt: str) -> int:
        """
        요청 전 토큰 수 계산 (공식 API 사용)
        
        Args:
            model_name: Gemini 모델명
            prompt: 입력 프롬프트
            
        Returns:
            예상 토큰 수
        """
        try:
            model = genai.GenerativeModel(model_name)
            result = model.count_tokens(prompt)
            return result.total_tokens
        except Exception as e:
            print(f"⚠️ 토큰 계산 실패: {e}")
            # 대략적인 추정치 반환 (4자당 1토큰)
            return len(prompt) // 4
    
    def calculate_cost(self, model_name: str, usage_metadata: Any) -> Dict[str, float]:
        """
        사용량 기반 비용 계산
        
        Args:
            model_name: 사용된 Gemini 모델명
            usage_metadata: response.usage_metadata 객체
            
        Returns:
            비용 정보 딕셔너리
        """
        if model_name not in self.PRICING:
            print(f"⚠️ 알 수 없는 모델: {model_name}")
            return {
                "input_cost": 0.0,
                "output_cost": 0.0,
                "total_cost": 0.0,
                "currency": "USD"
            }
        
        pricing = self.PRICING[model_name]
        
        # 토큰 수 추출
        input_tokens = getattr(usage_metadata, 'prompt_token_count', 0)
        output_tokens = getattr(usage_metadata, 'candidates_token_count', 0)
        
        # Gemini 2.5 Pro의 경우 대용량 컨텍스트 요금 적용
        if model_name == "gemini-2.5-pro" and input_tokens > 200000:
            input_price = pricing["input_large"]
            output_price = pricing["output_large"]
        else:
            input_price = pricing["input"]
            output_price = pricing["output"]
        
        # 비용 계산 (1M 토큰당 가격)
        input_cost = (input_tokens / 1_000_000) * input_price
        output_cost = (output_tokens / 1_000_000) * output_price
        total_cost = input_cost + output_cost
        
        return {
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "currency": "USD",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_price_per_1m": input_price,
            "output_price_per_1m": output_price,
        }
    
    def log_usage(
        self, 
        model_name: str, 
        usage_metadata: Any, 
        function_name: str = None,
        additional_metadata: Dict = None
    ):
        """
        사용량 로그 저장
        
        Args:
            model_name: 모델명
            usage_metadata: 사용량 메타데이터
            function_name: 호출한 함수명
            additional_metadata: 추가 메타데이터
        """
        cost_info = self.calculate_cost(model_name, usage_metadata)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "function": function_name,
            "usage": {
                "input_tokens": cost_info["input_tokens"],
                "output_tokens": cost_info["output_tokens"],
                "total_tokens": cost_info["total_tokens"],
            },
            "cost": {
                "input_cost": cost_info["input_cost"],
                "output_cost": cost_info["output_cost"],
                "total_cost": cost_info["total_cost"],
                "currency": cost_info["currency"],
                "input_price_per_1m": cost_info["input_price_per_1m"],
                "output_price_per_1m": cost_info["output_price_per_1m"],
            },
            "metadata": additional_metadata or {}
        }
        
        # 로그 파일에 저장
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        return log_entry
    
    def print_usage_summary(self, model_name: str, usage_metadata: Any):
        """사용량 요약 출력"""
        cost_info = self.calculate_cost(model_name, usage_metadata)
        
        print(f"📊 Gemini 사용량 요약 ({model_name})")
        print(f"  🔤 Input tokens: {cost_info['input_tokens']:,}")
        print(f"  📝 Output tokens: {cost_info['output_tokens']:,}")
        print(f"  📊 Total tokens: {cost_info['total_tokens']:,}")
        print(f"  💰 Input cost: ${cost_info['input_cost']:.6f}")
        print(f"  💰 Output cost: ${cost_info['output_cost']:.6f}")
        print(f"  💰 Total cost: ${cost_info['total_cost']:.6f}")
        
        # 무료 티어 정보 표시
        if model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]:
            print(f"  ℹ️  Note: {model_name}은 무료 티어 제한이 있습니다")


# 데코레이터 함수
def monitor_gemini_usage(model_name: str, function_name: str = None):
    """
    Gemini 사용량 모니터링 데코레이터
    
    Usage:
        @monitor_gemini_usage("gemini-2.0-flash-exp", "question_generator")
        def my_function():
            # Gemini API 호출
            response = model.generate_content(...)
            return response
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = GeminiMonitor()
            result = func(*args, **kwargs)
            
            # response 객체에서 usage_metadata 추출
            if hasattr(result, 'usage_metadata'):
                monitor.print_usage_summary(model_name, result.usage_metadata)
                monitor.log_usage(
                    model_name, 
                    result.usage_metadata, 
                    function_name or func.__name__
                )
            
            return result
        return wrapper
    return decorator


# LangSmith와 통합된 래퍼 클래스
class TrackedGeminiModel:
    """LangSmith 추적과 비용 모니터링이 통합된 Gemini 모델 래퍼"""
    
    def __init__(self, model_name: str, monitor: GeminiMonitor = None):
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.monitor = monitor or GeminiMonitor()
    
    @traceable(
        run_type="llm",
        name="Gemini Generate Content"
    )
    def generate_content(self, prompt: str, **kwargs):
        """LangSmith 추적과 비용 모니터링이 포함된 콘텐츠 생성"""
        
        # 요청 전 토큰 수 계산
        estimated_tokens = self.monitor.count_tokens_before_request(
            self.model_name, prompt
        )
        print(f"📝 예상 입력 토큰: {estimated_tokens:,}")
        
        # 콘텐츠 생성
        response = self.model.generate_content(prompt, **kwargs)
        
        # 사용량 모니터링
        if hasattr(response, 'usage_metadata'):
            self.monitor.print_usage_summary(self.model_name, response.usage_metadata)
            self.monitor.log_usage(
                self.model_name, 
                response.usage_metadata,
                function_name="generate_content"
            )
        
        return response


# 간편 사용을 위한 팩토리 함수
def create_monitored_model(model_name: str) -> TrackedGeminiModel:
    """모니터링이 활성화된 Gemini 모델 생성"""
    return TrackedGeminiModel(model_name)


# 사용량 분석 함수
def analyze_usage_logs(log_file: str = "data/logs/gemini_usage.jsonl") -> Dict[str, Any]:
    """사용량 로그 분석"""
    if not os.path.exists(log_file):
        return {"error": "로그 파일이 존재하지 않습니다"}
    
    total_cost = 0.0
    total_tokens = 0
    model_usage = {}
    function_usage = {}
    
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # 총 비용 및 토큰 수
                total_cost += entry["cost"]["total_cost"]
                total_tokens += entry["usage"]["total_tokens"]
                
                # 모델별 사용량
                model = entry["model"]
                if model not in model_usage:
                    model_usage[model] = {"count": 0, "cost": 0.0, "tokens": 0}
                model_usage[model]["count"] += 1
                model_usage[model]["cost"] += entry["cost"]["total_cost"]
                model_usage[model]["tokens"] += entry["usage"]["total_tokens"]
                
                # 함수별 사용량
                func = entry.get("function", "unknown")
                if func not in function_usage:
                    function_usage[func] = {"count": 0, "cost": 0.0, "tokens": 0}
                function_usage[func]["count"] += 1
                function_usage[func]["cost"] += entry["cost"]["total_cost"]
                function_usage[func]["tokens"] += entry["usage"]["total_tokens"]
                
            except json.JSONDecodeError:
                continue
    
    return {
        "summary": {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "currency": "USD"
        },
        "by_model": model_usage,
        "by_function": function_usage
    }