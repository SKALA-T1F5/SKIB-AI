from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List, Dict


def block_to_documents(blocks: List[Dict]) -> List[Document]:
    """
    Docling 블록 리스트를 LangChain Document 객체 리스트로 변환합니다.
    
    Args:
        blocks (List[Dict]): Docling 블록 리스트
        
    Returns:
        List[Document]: LangChain Document 객체 리스트
    """
    docs = []
    current_section = None
    
    for i, block in enumerate(blocks):
        block_type = block["type"]
        metadata = block.get("metadata", {})
        
        # 섹션 블록 처리
        if block_type == "section":
            current_section = block["title"]
            continue
            
        # 텍스트 블록 처리
        if block_type == "paragraph":
            content = block["content"]
            if current_section:
                metadata["section_title"] = current_section
            
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        **metadata,
                        "chunk_type": block_type,
                        "chunk_id": f"p{i}"
                    }
                )
            )
            
        # 표 블록 처리
        elif block_type == "table":
            table_content = _format_table_content(block["content"])
            if current_section:
                metadata["section_title"] = current_section
                
            docs.append(
                Document(
                    page_content=table_content,
                    metadata={
                        **metadata,
                        "chunk_type": block_type,
                        "chunk_id": f"t{i}"
                    }
                )
            )
            
        # 리스트 블록 처리
        elif block_type == "list":
            list_content = "\n".join([f"- {item}" for item in block["content"]])
            if current_section:
                metadata["section_title"] = current_section
                
            docs.append(
                Document(
                    page_content=list_content,
                    metadata={
                        **metadata,
                        "chunk_type": block_type,
                        "chunk_id": f"l{i}"
                    }
                )
            )
    
    return docs


def split_docs(docs: List[Document], chunk_size=500, chunk_overlap=50) -> List[Document]:
    """
    LangChain Document 객체들을 지정된 크기로 분할합니다.
    
    Args:
        docs (List[Document]): 분할할 Document 객체 리스트
        chunk_size (int): 청크 크기 (문자 수)
        chunk_overlap (int): 청크 간 겹침 크기 (문자 수)
        
    Returns:
        List[Document]: 분할된 Document 객체 리스트
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(docs)


def _format_table_content(table_content) -> str:
    """
    표 데이터를 문자열로 변환합니다.
    
    Args:
        table_content: 표 데이터 (딕셔너리 또는 문자열)
        
    Returns:
        str: 변환된 표 문자열
    """
    # 디버깅을 위한 출력
    print(f"Table content type: {type(table_content)}")
    print(f"Table content: {table_content}")
    
    # 문자열인 경우 그대로 반환
    if isinstance(table_content, str):
        return table_content
    
    # 딕셔너리가 아닌 경우 문자열로 변환
    if not isinstance(table_content, dict):
        return str(table_content)
    
    # 데이터가 없는 경우 빈 문자열 반환
    if not table_content or "data" not in table_content:
        return ""
    
    data = table_content["data"]
    headers = table_content.get("headers", [])
    
    if not data:
        return ""
    
    # 데이터가 문자열인 경우 그대로 반환
    if isinstance(data, str):
        return data
    
    # 데이터가 리스트가 아닌 경우 문자열로 변환
    if not isinstance(data, list):
        return str(data)
    
    table_str = ""
    
    # 헤더가 있는 경우 헤더 행 추가
    if headers:
        table_str = "| " + " | ".join(str(h) for h in headers) + " |\n"
        table_str += "|" + "|".join(["---" for _ in headers]) + "|\n"
    
    # 데이터 행 추가
    for row in data:
        if isinstance(row, (list, tuple)):
            table_str += "| " + " | ".join(str(cell) for cell in row) + " |\n"
        else:
            table_str += "| " + str(row) + " |\n"
    
    return table_str
