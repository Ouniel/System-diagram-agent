"""
图表生成代理模块
负责根据需求分析和系统理解结果生成相应的图表代码
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .base_agent import BaseAgent
from prompts.prompt_templates import PromptTemplates
from utils.logger import get_logger
from utils.validators import validate_mermaid_syntax

logger = get_logger(__name__)

@dataclass
class DiagramResult:
    """图表生成结果"""
    diagram_type: str
    diagram_code: str
    description: str
    complexity_level: str
    estimated_elements: int
    generation_notes: List[str]
    is_valid: bool = True
    validation_errors: List[str] = None

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []

class DiagramAgent(BaseAgent):
    """图表生成代理"""
    
    def __init__(self, deepseek_client, config):
        super().__init__(deepseek_client, config)
        self.prompt_templates = PromptTemplates()
        
        # 图表类型映射
        self.diagram_types = {
            "er_diagram": "E-R图",
            "uml_class": "UML类图", 
            "use_case": "用例图",
            "flowchart": "流程图",
            "sequence": "时序图",
            "activity": "活动图",
            "collaboration": "协作图",
            "function_structure": "功能结构图",
            "system_architecture": "系统架构图"
        }
        
        # 图表复杂度阈值
        self.complexity_thresholds = {
            "simple": 10,
            "medium": 25,
            "complex": 50
        }

    async def generate_diagram(
        self, 
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any],
        diagram_type: str
    ) -> DiagramResult:
        """
        生成指定类型的图表
        
        Args:
            requirement_result: 需求分析结果
            system_result: 系统理解结果
            diagram_type: 图表类型
            
        Returns:
            DiagramResult: 图表生成结果
        """
        try:
            logger.info(f"开始生成{self.diagram_types.get(diagram_type, diagram_type)}...")
            
            # 构建生成提示
            generation_prompt = self._build_generation_prompt(
                requirement_result, system_result, diagram_type
            )
            
            # 调用API生成图表
            response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": generation_prompt}],
                temperature=0.3,  # 较低温度确保一致性
                max_tokens=4000
            )
            
            # 解析生成结果
            diagram_result = self._parse_generation_result(response, diagram_type)
            
            # 验证图表语法
            if diagram_result.diagram_code:
                is_valid, errors = validate_mermaid_syntax(diagram_result.diagram_code)
                diagram_result.is_valid = is_valid
                diagram_result.validation_errors = errors
                
                if not is_valid:
                    logger.warning(f"图表语法验证失败: {errors}")
                    # 尝试修复语法错误
                    diagram_result = await self._fix_diagram_syntax(diagram_result)
            
            logger.info(f"{self.diagram_types.get(diagram_type)}生成完成")
            return diagram_result
            
        except Exception as e:
            logger.error(f"图表生成失败: {str(e)}")
            return DiagramResult(
                diagram_type=diagram_type,
                diagram_code="",
                description=f"生成失败: {str(e)}",
                complexity_level="unknown",
                estimated_elements=0,
                generation_notes=[f"错误: {str(e)}"],
                is_valid=False,
                validation_errors=[str(e)]
            )

    def _build_generation_prompt(
        self, 
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any], 
        diagram_type: str
    ) -> str:
        """构建图表生成提示"""
        
        # 获取基础提示模板
        base_prompt = self.prompt_templates.diagram_generation_prompt
        
        # 提取相关信息
        user_requirements = requirement_result.get('user_requirements', '')
        diagram_info = system_result.get('diagram_specific_info', {}).get(diagram_type, {})
        
        # 构建上下文信息
        context_info = {
            "用户需求": user_requirements,
            "图表类型": self.diagram_types.get(diagram_type, diagram_type),
            "系统信息": diagram_info
        }
        
        # 根据图表类型添加特定指导
        specific_guidance = self._get_diagram_specific_guidance(diagram_type)
        
        # 组合完整提示
        full_prompt = f"""
{base_prompt}

## 上下文信息
{json.dumps(context_info, ensure_ascii=False, indent=2)}

## 特定指导
{specific_guidance}

## 输出要求
请严格按照以下JSON格式输出结果：
{{
    "diagram_code": "完整的Mermaid图表代码",
    "description": "图表描述和说明",
    "complexity_level": "simple/medium/complex",
    "estimated_elements": "预估元素数量",
    "generation_notes": ["生成过程中的注意事项"]
}}
"""
        return full_prompt

    def _get_diagram_specific_guidance(self, diagram_type: str) -> str:
        """获取特定图表类型的生成指导"""
        
        guidance_map = {
            "er_diagram": """
E-R图生成指导：
- 使用erDiagram语法
- 明确标识实体、属性和关系
- 正确使用关系符号（||--o{, }|--||等）
- 为每个实体添加主要属性
- 标注关系的基数
""",
            "uml_class": """
UML类图生成指导：
- 使用classDiagram语法
- 包含类名、属性、方法
- 正确标识访问修饰符（+, -, #, ~）
- 使用继承、实现、关联等关系
- 添加接口和抽象类标识
""",
            "use_case": """
用例图生成指导：
- 使用graph语法绘制用例图
- 明确标识参与者（Actor）
- 列出主要用例
- 显示参与者与用例的关系
- 可包含系统边界
""",
            "flowchart": """
流程图生成指导：
- 使用flowchart TD/LR语法
- 使用标准流程图符号
- 明确开始和结束节点
- 正确使用判断节点
- 保持流程逻辑清晰
""",
            "sequence": """
时序图生成指导：
- 使用sequenceDiagram语法
- 明确参与者和对象
- 按时间顺序排列消息
- 使用激活框显示生命周期
- 包含返回消息
""",
            "activity": """
活动图生成指导：
- 使用flowchart语法绘制活动图
- 明确开始和结束活动
- 使用菱形表示决策点
- 显示并行活动分支
- 标注活动间的转换条件
""",
            "collaboration": """
协作图生成指导：
- 使用graph语法绘制协作图
- 显示对象间的协作关系
- 标注消息序号和方向
- 包含对象的角色信息
- 体现系统的动态行为
""",
            "function_structure": """
功能结构图生成指导：
- 使用graph TD语法
- 按层次结构组织功能模块
- 明确模块间的调用关系
- 使用不同形状区分模块类型
- 保持结构清晰易读
""",
            "system_architecture": """
系统架构图生成指导：
- 使用graph语法绘制架构图
- 明确系统各层次结构
- 显示组件间的依赖关系
- 标注数据流向
- 包含外部系统接口
"""
        }
        
        return guidance_map.get(diagram_type, "请根据图表类型生成相应的Mermaid代码")

    def _parse_generation_result(self, response: str, diagram_type: str) -> DiagramResult:
        """解析图表生成结果"""
        try:
            # 尝试解析JSON响应
            result_data = self._extract_json_from_response(response)
            
            if result_data:
                return DiagramResult(
                    diagram_type=diagram_type,
                    diagram_code=result_data.get('diagram_code', ''),
                    description=result_data.get('description', ''),
                    complexity_level=result_data.get('complexity_level', 'medium'),
                    estimated_elements=int(result_data.get('estimated_elements', 0)),
                    generation_notes=result_data.get('generation_notes', [])
                )
            else:
                # 如果JSON解析失败，尝试提取Mermaid代码
                diagram_code = self._extract_mermaid_code(response)
                return DiagramResult(
                    diagram_type=diagram_type,
                    diagram_code=diagram_code,
                    description="从响应中提取的图表代码",
                    complexity_level=self._estimate_complexity(diagram_code),
                    estimated_elements=self._count_elements(diagram_code),
                    generation_notes=["从文本响应中提取"]
                )
                
        except Exception as e:
            logger.error(f"解析生成结果失败: {str(e)}")
            return DiagramResult(
                diagram_type=diagram_type,
                diagram_code="",
                description=f"解析失败: {str(e)}",
                complexity_level="unknown",
                estimated_elements=0,
                generation_notes=[f"解析错误: {str(e)}"]
            )

    def _extract_mermaid_code(self, text: str) -> str:
        """从文本中提取Mermaid代码"""
        # 查找代码块
        code_patterns = [
            r'```mermaid\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'`(.*?)`'
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                return matches[0].strip()
        
        # 如果没有找到代码块，返回整个文本
        return text.strip()

    def _estimate_complexity(self, diagram_code: str) -> str:
        """估算图表复杂度"""
        if not diagram_code:
            return "unknown"
            
        element_count = self._count_elements(diagram_code)
        
        if element_count <= self.complexity_thresholds["simple"]:
            return "simple"
        elif element_count <= self.complexity_thresholds["medium"]:
            return "medium"
        else:
            return "complex"

    def _count_elements(self, diagram_code: str) -> int:
        """统计图表元素数量"""
        if not diagram_code:
            return 0
            
        # 统计各种图表元素
        lines = diagram_code.split('\n')
        element_count = 0
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('%') and not line.startswith('%%'):
                # 统计节点、关系、实体等
                if '-->' in line or '---' in line or '||--' in line:
                    element_count += 1
                elif ':' in line and not line.startswith('graph'):
                    element_count += 1
                elif line.startswith('class ') or line.startswith('participant '):
                    element_count += 1
        
        return max(element_count, len([l for l in lines if l.strip()]) // 2)

    async def _fix_diagram_syntax(self, diagram_result: DiagramResult) -> DiagramResult:
        """尝试修复图表语法错误"""
        try:
            logger.info("尝试修复图表语法错误...")
            
            fix_prompt = f"""
以下Mermaid图表代码存在语法错误，请修复：

错误信息：
{'; '.join(diagram_result.validation_errors)}

原始代码：
```mermaid
{diagram_result.diagram_code}
```

请提供修复后的正确Mermaid代码，只返回代码，不要其他说明。
"""
            
            response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": fix_prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            fixed_code = self._extract_mermaid_code(response)
            
            # 验证修复后的代码
            is_valid, errors = validate_mermaid_syntax(fixed_code)
            
            if is_valid:
                logger.info("图表语法修复成功")
                diagram_result.diagram_code = fixed_code
                diagram_result.is_valid = True
                diagram_result.validation_errors = []
                diagram_result.generation_notes.append("语法已自动修复")
            else:
                logger.warning("图表语法修复失败")
                diagram_result.generation_notes.append("语法修复失败")
                
        except Exception as e:
            logger.error(f"语法修复过程出错: {str(e)}")
            diagram_result.generation_notes.append(f"修复过程出错: {str(e)}")
            
        return diagram_result

    async def generate_multiple_diagrams(
        self,
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any],
        diagram_types: List[str]
    ) -> Dict[str, DiagramResult]:
        """
        批量生成多个图表
        
        Args:
            requirement_result: 需求分析结果
            system_result: 系统理解结果
            diagram_types: 要生成的图表类型列表
            
        Returns:
            Dict[str, DiagramResult]: 图表类型到生成结果的映射
        """
        results = {}
        
        for diagram_type in diagram_types:
            try:
                result = await self.generate_diagram(
                    requirement_result, system_result, diagram_type
                )
                results[diagram_type] = result
                
                # 记录生成状态
                status = "成功" if result.is_valid else "失败"
                logger.info(f"{self.diagram_types.get(diagram_type)}生成{status}")
                
            except Exception as e:
                logger.error(f"生成{self.diagram_types.get(diagram_type)}时出错: {str(e)}")
                results[diagram_type] = DiagramResult(
                    diagram_type=diagram_type,
                    diagram_code="",
                    description=f"生成失败: {str(e)}",
                    complexity_level="unknown",
                    estimated_elements=0,
                    generation_notes=[f"错误: {str(e)}"],
                    is_valid=False,
                    validation_errors=[str(e)]
                )
        
        return results

    def get_diagram_statistics(self, results: Dict[str, DiagramResult]) -> Dict[str, Any]:
        """获取图表生成统计信息"""
        total_diagrams = len(results)
        successful_diagrams = sum(1 for r in results.values() if r.is_valid)
        failed_diagrams = total_diagrams - successful_diagrams
        
        complexity_distribution = {}
        total_elements = 0
        
        for result in results.values():
            if result.is_valid:
                complexity = result.complexity_level
                complexity_distribution[complexity] = complexity_distribution.get(complexity, 0) + 1
                total_elements += result.estimated_elements
        
        return {
            "total_diagrams": total_diagrams,
            "successful_diagrams": successful_diagrams,
            "failed_diagrams": failed_diagrams,
            "success_rate": successful_diagrams / total_diagrams if total_diagrams > 0 else 0,
            "complexity_distribution": complexity_distribution,
            "total_elements": total_elements,
            "average_elements": total_elements / successful_diagrams if successful_diagrams > 0 else 0
        } 