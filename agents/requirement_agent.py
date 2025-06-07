"""
需求理解Agent
负责分析用户的系统需求，识别图表类型和关键信息
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from prompts.prompt_templates import PromptTemplates
from utils.validators import validate_json_response, validate_requirement_analysis


class RequirementAgent(BaseAgent):
    """需求理解Agent - 分析用户需求并提取关键信息"""
    
    def process(self, input_data: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理用户需求描述
        
        Args:
            input_data: 用户的需求描述
            context: 上下文信息
        
        Returns:
            需求分析结果
        """
        try:
            # 验证输入
            if not self.validate_input(input_data):
                raise ValueError("无效的输入数据")
            
            # 更新上下文
            if context:
                self.context.update(context)
            
            self.update_context("user_input", input_data)
            self.logger.info("开始需求理解分析")
            
            # 构建prompt
            prompt = PromptTemplates.get_prompt(
                "requirement_understanding",
                用户的需求描述=input_data
            )
            
            # 调用API
            response = self._retry_api_call(prompt, temperature=0.3)
            
            # 解析响应
            analysis_result = self._parse_response(response)
            
            # 验证结果
            if not self._validate_analysis_result(analysis_result):
                self.logger.warning("分析结果格式不完整，尝试重新分析")
                # 可以在这里添加重试逻辑
            
            # 更新上下文
            self.update_context("requirement_analysis", analysis_result)
            self.update_context("diagram_type", analysis_result.get("图表类型"))
            self.update_context("system_type", analysis_result.get("系统类型"))
            
            self.logger.info(f"需求分析完成，图表类型: {analysis_result.get('图表类型')}")
            
            return self.format_output(analysis_result)
            
        except Exception as e:
            return self.handle_error(e)
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        解析API响应
        
        Args:
            response: API响应文本
        
        Returns:
            解析后的分析结果
        """
        # 尝试解析JSON格式的响应
        parsed_json = validate_json_response(response)
        
        if parsed_json:
            return parsed_json
        
        # 如果JSON解析失败，尝试从文本中提取信息
        self.logger.warning("JSON解析失败，尝试文本解析")
        return self._extract_from_text(response)
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取需求分析信息
        
        Args:
            text: 响应文本
        
        Returns:
            提取的信息字典
        """
        result = {
            "图表类型": "未确定",
            "系统类型": "未确定", 
            "核心需求": "",
            "关键要素": [],
            "信息完整度": "部分完整",
            "补充问题": []
        }
        
        # 简单的文本解析逻辑
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 识别图表类型
            if any(keyword in line for keyword in ["E-R图", "类图", "用例图", "流程图", "时序图", "活动图", "协作图", "功能结构图", "系统架构图"]):
                for diagram_type in ["E-R图", "UML类图", "UML用例图", "流程图", "时序图", "活动图", "协作图", "功能结构图", "系统架构图"]:
                    if diagram_type in line:
                        result["图表类型"] = diagram_type
                        break
            
            # 识别系统类型
            if any(keyword in line for keyword in ["Web应用", "数据库系统", "移动应用", "企业系统", "微服务"]):
                result["系统类型"] = line
            
            # 提取核心需求
            if "需求" in line or "目标" in line:
                result["核心需求"] = line
        
        return result
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> bool:
        """
        验证分析结果的完整性
        
        Args:
            result: 分析结果
        
        Returns:
            是否有效
        """
        return validate_requirement_analysis(result)
    
    def get_supported_diagrams(self) -> Dict[str, str]:
        """
        获取支持的图表类型
        
        Returns:
            支持的图表类型字典
        """
        return PromptTemplates.list_supported_diagrams()
    
    def suggest_diagram_type(self, user_input: str) -> str:
        """
        基于用户输入建议图表类型
        
        Args:
            user_input: 用户输入
        
        Returns:
            建议的图表类型
        """
        user_input_lower = user_input.lower()
        
        # 关键词映射
        keyword_mapping = {
            "数据库": "E-R图",
            "实体": "E-R图", 
            "关系": "E-R图",
            "类": "UML类图",
            "对象": "UML类图",
            "继承": "UML类图",
            "用例": "UML用例图",
            "用户": "UML用例图",
            "角色": "UML用例图",
            "流程": "流程图",
            "步骤": "流程图",
            "业务": "流程图",
            "时序": "时序图",
            "交互": "时序图",
            "消息": "时序图",
            "活动": "活动图",
            "并行": "活动图",
            "协作": "协作图",
            "功能": "功能结构图",
            "模块": "功能结构图",
            "架构": "系统架构图",
            "组件": "系统架构图",
            "部署": "系统架构图"
        }
        
        for keyword, diagram_type in keyword_mapping.items():
            if keyword in user_input_lower:
                return diagram_type
        
        return "流程图"  # 默认建议
    
    def generate_follow_up_questions(self, analysis_result: Dict[str, Any]) -> list:
        """
        根据分析结果生成后续问题
        
        Args:
            analysis_result: 需求分析结果
        
        Returns:
            后续问题列表
        """
        questions = []
        
        # 检查信息完整度
        completeness = analysis_result.get("信息完整度", "")
        
        if completeness == "不完整":
            questions.extend([
                "请详细描述您的系统包含哪些主要组件？",
                "系统的主要用户角色有哪些？",
                "您希望图表重点展示系统的哪个方面？"
            ])
        elif completeness == "部分完整":
            diagram_type = analysis_result.get("图表类型", "")
            
            if diagram_type == "E-R图":
                questions.extend([
                    "请列出系统中的主要实体（如用户、订单、产品等）",
                    "这些实体之间有什么关系？",
                    "每个实体有哪些重要属性？"
                ])
            elif diagram_type == "UML类图":
                questions.extend([
                    "请描述系统中的主要类和它们的职责",
                    "类之间有继承或组合关系吗？",
                    "每个类有哪些重要的方法和属性？"
                ])
            elif diagram_type == "流程图":
                questions.extend([
                    "请描述完整的业务流程步骤",
                    "流程中有哪些决策点？",
                    "异常情况如何处理？"
                ])
        
        return questions 