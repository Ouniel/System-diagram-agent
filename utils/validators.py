"""
验证工具模块
提供数据验证和格式检查功能
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from jsonschema import validate, ValidationError


# 支持的图表类型
SUPPORTED_DIAGRAM_TYPES = {
    "er_diagram": "E-R图",
    "class_diagram": "UML类图", 
    "use_case_diagram": "UML用例图",
    "flowchart": "流程图",
    "sequence_diagram": "时序图",
    "activity_diagram": "活动图",
    "collaboration_diagram": "协作图",
    "function_structure_diagram": "功能结构图",
    "system_architecture_diagram": "系统架构图"
}


def validate_json(json_str: str) -> bool:
    """
    验证JSON格式是否正确（别名）
    
    Args:
        json_str: JSON字符串
    
    Returns:
        是否为有效的JSON格式
    """
    return validate_json_format(json_str)


def validate_json_format(json_str: str) -> bool:
    """
    验证JSON格式是否正确
    
    Args:
        json_str: JSON字符串
    
    Returns:
        是否为有效的JSON格式
    """
    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def validate_diagram_type(diagram_type: str) -> bool:
    """
    验证图表类型是否支持
    
    Args:
        diagram_type: 图表类型
    
    Returns:
        是否为支持的图表类型
    """
    return diagram_type in SUPPORTED_DIAGRAM_TYPES


def validate_json_response(response: str) -> Optional[Dict[str, Any]]:
    """
    验证并解析JSON响应
    
    Args:
        response: JSON字符串响应
    
    Returns:
        解析后的字典，如果解析失败返回None
    """
    try:
        # 尝试提取JSON部分（处理可能包含其他文本的响应）
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试找到第一个{到最后一个}的内容
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response[start:end+1]
            else:
                json_str = response
        
        return json.loads(json_str)
    except (json.JSONDecodeError, AttributeError) as e:
        return None


def validate_requirement_analysis(data: Dict[str, Any]) -> bool:
    """
    验证需求分析结果的格式
    
    Args:
        data: 需求分析结果字典
    
    Returns:
        是否符合预期格式
    """
    required_fields = ["图表类型", "系统类型", "核心需求", "关键要素", "信息完整度"]
    return all(field in data for field in required_fields)


def validate_system_analysis(data: Dict[str, Any]) -> bool:
    """
    验证系统分析结果的格式
    
    Args:
        data: 系统分析结果字典
    
    Returns:
        是否符合预期格式
    """
    # 系统分析结果格式比较灵活，主要检查是否有内容
    return bool(data) and isinstance(data, dict)


def validate_quality_check(data: Dict[str, Any]) -> bool:
    """
    验证质量检查结果的格式
    
    Args:
        data: 质量检查结果字典
    
    Returns:
        是否符合预期格式
    """
    required_fields = ["质量评分", "检查结果"]
    return all(field in data for field in required_fields)


def sanitize_user_input(user_input: str) -> str:
    """
    清理用户输入，移除潜在的危险字符
    
    Args:
        user_input: 用户输入字符串
    
    Returns:
        清理后的字符串
    """
    if not isinstance(user_input, str):
        return str(user_input)
    
    # 移除控制字符
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', user_input)
    
    # 限制长度
    max_length = 10000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    return sanitized.strip()


def validate_api_response(response: Dict[str, Any]) -> bool:
    """
    验证API响应的基本格式
    
    Args:
        response: API响应字典
    
    Returns:
        是否为有效的API响应
    """
    if not isinstance(response, dict):
        return False
    
    # 检查是否有choices字段（OpenAI格式）
    if "choices" in response:
        choices = response["choices"]
        if isinstance(choices, list) and len(choices) > 0:
            first_choice = choices[0]
            return "message" in first_choice and "content" in first_choice["message"]
    
    return False


def extract_mermaid_code(text: str) -> Optional[str]:
    """
    从文本中提取Mermaid代码
    
    Args:
        text: 包含Mermaid代码的文本
    
    Returns:
        提取的Mermaid代码，如果没有找到返回None
    """
    # 查找```mermaid代码块
    mermaid_pattern = r'```mermaid\s*(.*?)\s*```'
    match = re.search(mermaid_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    
    return None


def validate_mermaid_syntax(mermaid_code: str) -> bool:
    """
    基本的Mermaid语法验证
    
    Args:
        mermaid_code: Mermaid代码
    
    Returns:
        是否符合基本语法
    """
    if not mermaid_code:
        return False
    
    # 检查是否包含基本的Mermaid关键词
    mermaid_keywords = [
        'graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 
        'erDiagram', 'gitgraph', 'pie', 'journey'
    ]
    
    return any(keyword in mermaid_code for keyword in mermaid_keywords) 