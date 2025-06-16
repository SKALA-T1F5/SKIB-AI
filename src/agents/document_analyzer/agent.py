"""
DocumentAnalyzerAgent - 문서 분석 Agent

문서를 분석하여 구조, 내용, 난이도 등을 파악하는 Agent입니다.
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging

from src.agents.base.agent import BaseAgent
from state import DocumentAnalyzerState
from .tools.text_analyzer import TextAnalyzer
from .tools.structure_parser import StructureParser
from .tools.difficulty_assessor import DifficultyAssessor
from .tools.keyword_extractor import KeywordExtractor

from exceptions.agent_exceptions import (
    create_agent_execution_error,
    create_agent_validation_error,
    create_agent_tool_error
)


class DocumentAnalyzerAgent(BaseAgent):
    """
    문서 분석 Agent
    
    주요 기능:
    - 문서 텍스트 추출 및 정제
    - 문서 구조 분석 (제목, 섹션, 단락 등)
    - 내용 난이도 평가
    - 핵심 키워드 추출
    - 문서 요약 생성
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """DocumentAnalyzerAgent 초기화"""
        
        super().__init__(
            name="document_analyzer",
            state_class=DocumentAnalyzerState,
            config=config or {}
        )
        
        # 기본 설정
        self.config.setdefault("max_text_length", 50000)
        self.config.setdefault("min_text_length", 100)
        self.config.setdefault("analysis_depth", "standard")
        self.config.setdefault("keyword_count", 10)
        self.config.setdefault("summary_max_length", 500)
    
    async def _setup_tools(self) -> None:
        """도구들을 초기화합니다"""
        try:
            self.tools["text_analyzer"] = TextAnalyzer(self.config.get("text_analyzer_config", {}))
            self.tools["structure_parser"] = StructureParser(self.config.get("structure_parser_config", {}))
            self.tools["difficulty_assessor"] = DifficultyAssessor(self.config.get("difficulty_assessor_config", {}))
            self.tools["keyword_extractor"] = KeywordExtractor(self.config.get("keyword_extractor_config", {}))
            
            # 도구들 초기화
            for tool_name, tool in self.tools.items():
                if hasattr(tool, 'initialize'):
                    await tool.initialize()
                    
        except Exception as e:
            raise create_agent_tool_error(
                agent_name=self.name,
                tool_name="setup",
                tool_operation="initialization",
                tool_error=e
            )
    
    async def plan(self, input_data: Dict[str, Any], state: DocumentAnalyzerState) -> Dict[str, Any]:
        """
        문서 분석 계획을 수립합니다
        
        Args:
            input_data: 입력 데이터 (document_path, document_id 등)
            state: 현재 상태
            
        Returns:
            분석 계획
        """
        try:
            # 입력 검증
            document_path = input_data.get("document_path")
            document_id = input_data.get("document_id")
            
            if not document_path:
                raise ValueError("document_path is required")
            if not document_id:
                raise ValueError("document_id is required")
            
            # 분석 옵션 설정
            analysis_options = input_data.get("analysis_options", {})
            analysis_depth = analysis_options.get("depth", self.config["analysis_depth"])
            
            # 분석 계획 생성
            plan = {
                "document_path": document_path,
                "document_id": document_id,
                "analysis_steps": [
                    "extract_text",
                    "parse_structure", 
                    "assess_difficulty",
                    "extract_keywords",
                    "generate_summary"
                ],
                "analysis_options": {
                    "depth": analysis_depth,
                    "keyword_count": analysis_options.get("keyword_count", self.config["keyword_count"]),
                    "summary_length": analysis_options.get("summary_length", self.config["summary_max_length"]),
                    "include_metadata": analysis_options.get("include_metadata", True)
                },
                "estimated_duration": self._estimate_duration(analysis_depth)
            }
            
            # 상태 업데이트
            state["document_path"] = document_path
            state["document_id"] = document_id
            state["analysis_options"] = plan["analysis_options"]
            
            self.logger.info(f"Analysis plan created for document {document_id}")
            return plan
            
        except Exception as e:
            raise create_agent_execution_error(
                agent_name=self.name,
                operation="planning",
                reason=str(e),
                input_data=input_data
            )
    
    async def act(self, plan: Dict[str, Any], state: DocumentAnalyzerState) -> Dict[str, Any]:
        """
        분석 계획에 따라 문서를 분석합니다
        
        Args:
            plan: 분석 계획
            state: 현재 상태
            
        Returns:
            분석 결과
        """
        try:
            document_path = plan["document_path"]
            analysis_steps = plan["analysis_steps"]
            analysis_options = plan["analysis_options"]
            
            results = {}
            total_steps = len(analysis_steps)
            
            for i, step in enumerate(analysis_steps):
                self.logger.info(f"Executing analysis step: {step}")
                
                result = None
                try:
                    # 각 분석 단계 실행
                    extracted_text = state.get("extracted_text")
                    if step == "extract_text":
                        result = await self._extract_text(document_path, analysis_options)
                        state["extracted_text"] = result["text"]
                        state["document_metadata"] = result["metadata"]
                    elif step == "parse_structure":
                        if not isinstance(extracted_text, str):
                            raise create_agent_execution_error(
                                agent_name=self.name,
                                operation="parse_structure",
                                reason="Extracted text is missing or not a string",
                                input_data=dict(state)
                            )
                        result = await self._parse_structure(extracted_text, analysis_options)
                        state["document_structure"] = result
                    elif step == "assess_difficulty":
                        if not isinstance(extracted_text, str):
                            raise create_agent_execution_error(
                                agent_name=self.name,
                                operation="assess_difficulty",
                                reason="Extracted text is missing or not a string",
                                input_data=dict(state)
                            )
                        result = await self._assess_difficulty(extracted_text, analysis_options)
                        state["difficulty_assessment"] = result
                    elif step == "extract_keywords":
                        if not isinstance(extracted_text, str):
                            raise create_agent_execution_error(
                                agent_name=self.name,
                                operation="extract_keywords",
                                reason="Extracted text is missing or not a valid string",
                                input_data=dict(state)
                            )
                        result = await self._extract_keywords(extracted_text, analysis_options)
                        state["keywords"] = result
                    elif step == "generate_summary":
                        if not isinstance(extracted_text, str):
                            raise create_agent_execution_error(
                                agent_name=self.name,
                                operation="generate_summary",
                                reason="Extracted text is missing or not a string",
                                input_data=dict(state)
                            )
                        result = await self._generate_summary(extracted_text, analysis_options)
                        state["summary"] = result

                    results[step] = result

                    # 진행률 업데이트
                    progress = (i + 1) / total_steps * 0.9  # 90%까지만 (검증 단계 남겨둠)
                    self.update_progress(progress, f"Completed {step}")

                except Exception as step_error:
                    raise create_agent_tool_error(
                        agent_name=self.name,
                        tool_name=step,
                        tool_operation="analysis",
                        tool_error=step_error
                    )
            
        except Exception as e:
            raise create_agent_execution_error(
                agent_name=self.name,
                operation="analysis_execution",
                reason=str(e),
                input_data=plan
            )
    
    async def reflect(self, result: Dict[str, Any], state: DocumentAnalyzerState) -> tuple[bool, str]:
        """
        분석 결과를 검증합니다
        
        Args:
            result: 분석 결과
            state: 현재 상태
            
        Returns:
            (is_valid, feedback) 튜플
        """
        try:
            validation_issues = []
            
            # 필수 결과 검증
            required_results = ["extract_text", "parse_structure", "assess_difficulty", "extract_keywords"]
            analysis_results = result.get("analysis_results", {})
            
            for required_step in required_results:
                if required_step not in analysis_results:
                    validation_issues.append(f"Missing analysis result: {required_step}")
            
            # 텍스트 길이 검증
            extracted_text = state.get("extracted_text") or ""
            if len(extracted_text) < self.config["min_text_length"]:
                validation_issues.append(f"Extracted text too short: {len(extracted_text)} < {self.config['min_text_length']}")
            
            # 키워드 개수 검증
            keywords = state.get("keywords") or []
            if len(keywords) == 0:
                validation_issues.append("No keywords extracted")
            
            # 구조 분석 검증
            document_structure = state.get("document_structure") or {}
            if not document_structure.get("sections") and not document_structure.get("paragraphs"):
                validation_issues.append("No document structure detected")
            
            # 난이도 평가 검증
            difficulty_assessment = state.get("difficulty_assessment", {})
            if not isinstance(difficulty_assessment, dict) or "level" not in difficulty_assessment:
                validation_issues.append("Difficulty level not assessed")
            
            # 검증 결과
            is_valid = len(validation_issues) == 0
            
            if is_valid:
                feedback = "Document analysis validation successful"
                self.logger.info(f"Validation passed for document {result.get('document_id')}")
            else:
                feedback = f"Validation failed: {'; '.join(validation_issues)}"
                self.logger.warning(f"Validation failed for document {result.get('document_id')}: {feedback}")
            
            return is_valid, feedback
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    # 내부 분석 메서드들
    async def _extract_text(self, document_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """텍스트 추출"""
        text_analyzer = self.get_tool("text_analyzer")
        if not text_analyzer:
            raise ValueError("TextAnalyzer tool not available")
        
        return await text_analyzer.extract_text(document_path, options)
    
    async def _parse_structure(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """문서 구조 분석"""
        structure_parser = self.get_tool("structure_parser")
        if not structure_parser:
            raise ValueError("StructureParser tool not available")
        
        return await structure_parser.parse_structure(text, options)
    
    async def _assess_difficulty(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """난이도 평가"""
        difficulty_assessor = self.get_tool("difficulty_assessor")
        if not difficulty_assessor:
            raise ValueError("DifficultyAssessor tool not available")
        
        return await difficulty_assessor.assess_difficulty(text, options)
    
    async def _extract_keywords(self, text: str, options: Dict[str, Any]) -> List[str]:
        """키워드 추출"""
        keyword_extractor = self.get_tool("keyword_extractor")
        if not keyword_extractor:
            raise ValueError("KeywordExtractor tool not available")
        
        return await keyword_extractor.extract_keywords(text, options)
    
    async def _generate_summary(self, text: str, options: Dict[str, Any]) -> str:
        """요약 생성"""
        text_analyzer = self.get_tool("text_analyzer")
        if not text_analyzer:
            raise ValueError("TextAnalyzer tool not available")
        
        return await text_analyzer.generate_summary(text, options)
    
    def _estimate_duration(self, analysis_depth: str) -> float:
        """분석 예상 소요 시간 계산"""
        duration_map = {
            "quick": 30.0,
            "standard": 60.0,
            "deep": 120.0
        }
        return duration_map.get(analysis_depth, 60.0)
    
    def _calculate_structure_complexity(self, structure: Dict[str, Any]) -> float:
        """문서 구조 복잡도 계산"""
        sections = structure.get("sections", [])
        paragraphs = structure.get("paragraphs", [])
        
        # 간단한 복잡도 계산 공식
        complexity = len(sections) * 0.5 + len(paragraphs) * 0.1
        return min(complexity, 10.0)  # 최대 10.0으로 제한
