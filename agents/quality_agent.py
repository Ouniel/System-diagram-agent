"""
质量检查代理模块
负责验证和评估生成的图表质量，确保图表符合标准和用户需求
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseAgent
from .diagram_agent import DiagramResult
from prompts.prompt_templates import PromptTemplates
from utils.logger import get_logger
from utils.validators import validate_mermaid_syntax, validate_json

logger = get_logger(__name__)

class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

@dataclass
class QualityCheckResult:
    """质量检查结果"""
    overall_quality: QualityLevel
    quality_score: float  # 0-100分
    syntax_valid: bool
    completeness_score: float
    accuracy_score: float
    readability_score: float
    compliance_score: float
    
    # 详细检查结果
    syntax_issues: List[str]
    missing_elements: List[str]
    accuracy_issues: List[str]
    readability_issues: List[str]
    compliance_issues: List[str]
    
    # 改进建议
    improvement_suggestions: List[str]
    
    # 检查详情
    check_details: Dict[str, Any]

class QualityAgent(BaseAgent):
    """质量检查代理"""
    
    def __init__(self, deepseek_client, config):
        super().__init__(deepseek_client, config)
        self.prompt_templates = PromptTemplates()
        
        # 质量检查权重
        self.quality_weights = {
            "syntax": 0.25,      # 语法正确性
            "completeness": 0.25, # 完整性
            "accuracy": 0.25,     # 准确性
            "readability": 0.15,  # 可读性
            "compliance": 0.10    # 规范符合性
        }
        
        # 质量阈值
        self.quality_thresholds = {
            QualityLevel.EXCELLENT: 90,
            QualityLevel.GOOD: 75,
            QualityLevel.FAIR: 60,
            QualityLevel.POOR: 0
        }

    async def check_diagram_quality(
        self,
        diagram_result: DiagramResult,
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any]
    ) -> QualityCheckResult:
        """
        检查图表质量
        
        Args:
            diagram_result: 图表生成结果
            requirement_result: 需求分析结果
            system_result: 系统理解结果
            
        Returns:
            QualityCheckResult: 质量检查结果
        """
        try:
            logger.info(f"开始质量检查: {diagram_result.diagram_type}")
            
            # 1. 语法检查
            syntax_score, syntax_issues = self._check_syntax(diagram_result)
            
            # 2. 完整性检查
            completeness_score, missing_elements = await self._check_completeness(
                diagram_result, requirement_result, system_result
            )
            
            # 3. 准确性检查
            accuracy_score, accuracy_issues = await self._check_accuracy(
                diagram_result, requirement_result, system_result
            )
            
            # 4. 可读性检查
            readability_score, readability_issues = self._check_readability(diagram_result)
            
            # 5. 规范符合性检查
            compliance_score, compliance_issues = self._check_compliance(diagram_result)
            
            # 计算总体质量分数
            overall_score = self._calculate_overall_score({
                "syntax": syntax_score,
                "completeness": completeness_score,
                "accuracy": accuracy_score,
                "readability": readability_score,
                "compliance": compliance_score
            })
            
            # 确定质量等级
            quality_level = self._determine_quality_level(overall_score)
            
            # 生成改进建议
            improvement_suggestions = await self._generate_improvement_suggestions(
                diagram_result, {
                    "syntax_issues": syntax_issues,
                    "missing_elements": missing_elements,
                    "accuracy_issues": accuracy_issues,
                    "readability_issues": readability_issues,
                    "compliance_issues": compliance_issues
                }
            )
            
            result = QualityCheckResult(
                overall_quality=quality_level,
                quality_score=overall_score,
                syntax_valid=syntax_score >= 90,
                completeness_score=completeness_score,
                accuracy_score=accuracy_score,
                readability_score=readability_score,
                compliance_score=compliance_score,
                syntax_issues=syntax_issues,
                missing_elements=missing_elements,
                accuracy_issues=accuracy_issues,
                readability_issues=readability_issues,
                compliance_issues=compliance_issues,
                improvement_suggestions=improvement_suggestions,
                check_details={
                    "scores": {
                        "syntax": syntax_score,
                        "completeness": completeness_score,
                        "accuracy": accuracy_score,
                        "readability": readability_score,
                        "compliance": compliance_score
                    },
                    "weights": self.quality_weights
                }
            )
            
            logger.info(f"质量检查完成，总分: {overall_score:.1f}, 等级: {quality_level.value}")
            return result
            
        except Exception as e:
            logger.error(f"质量检查失败: {str(e)}")
            return QualityCheckResult(
                overall_quality=QualityLevel.POOR,
                quality_score=0.0,
                syntax_valid=False,
                completeness_score=0.0,
                accuracy_score=0.0,
                readability_score=0.0,
                compliance_score=0.0,
                syntax_issues=[f"检查失败: {str(e)}"],
                missing_elements=[],
                accuracy_issues=[],
                readability_issues=[],
                compliance_issues=[],
                improvement_suggestions=[],
                check_details={}
            )

    def _check_syntax(self, diagram_result: DiagramResult) -> Tuple[float, List[str]]:
        """检查语法正确性"""
        if not diagram_result.diagram_code:
            return 0.0, ["图表代码为空"]
        
        # 使用已有的验证结果
        if diagram_result.is_valid:
            return 100.0, []
        else:
            return 0.0, diagram_result.validation_errors or ["语法验证失败"]

    async def _check_completeness(
        self,
        diagram_result: DiagramResult,
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """检查完整性"""
        try:
            check_prompt = f"""
请检查以下图表的完整性，判断是否包含了用户需求中的所有关键元素。

用户需求：
{requirement_result.get('user_requirements', '')}

图表类型：{diagram_result.diagram_type}
图表代码：
```mermaid
{diagram_result.diagram_code}
```

请分析：
1. 图表是否包含了需求中提到的所有关键实体/组件/流程
2. 是否遗漏了重要的关系或连接
3. 图表的层次结构是否完整

请以JSON格式返回结果：
{{
    "completeness_score": 0-100的分数,
    "missing_elements": ["缺失的元素列表"],
    "analysis": "详细分析"
}}
"""
            
            response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": check_prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            
            result_data = self._extract_json_from_response(response)
            if result_data:
                return (
                    float(result_data.get('completeness_score', 50)),
                    result_data.get('missing_elements', [])
                )
            else:
                return 50.0, ["无法解析完整性检查结果"]
                
        except Exception as e:
            logger.error(f"完整性检查失败: {str(e)}")
            return 30.0, [f"检查过程出错: {str(e)}"]

    async def _check_accuracy(
        self,
        diagram_result: DiagramResult,
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any]
    ) -> Tuple[float, List[str]]:
        """检查准确性"""
        try:
            check_prompt = f"""
请检查以下图表的准确性，判断图表内容是否正确反映了用户需求。

用户需求：
{requirement_result.get('user_requirements', '')}

系统信息：
{json.dumps(system_result.get('diagram_specific_info', {}).get(diagram_result.diagram_type, {}), ensure_ascii=False, indent=2)}

图表类型：{diagram_result.diagram_type}
图表代码：
```mermaid
{diagram_result.diagram_code}
```

请分析：
1. 图表中的关系是否正确
2. 实体/组件的属性是否准确
3. 流程逻辑是否合理
4. 是否存在错误的连接或关系

请以JSON格式返回结果：
{{
    "accuracy_score": 0-100的分数,
    "accuracy_issues": ["准确性问题列表"],
    "analysis": "详细分析"
}}
"""
            
            response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": check_prompt}],
                temperature=0.2,
                max_tokens=1000
            )
            
            result_data = self._extract_json_from_response(response)
            if result_data:
                return (
                    float(result_data.get('accuracy_score', 50)),
                    result_data.get('accuracy_issues', [])
                )
            else:
                return 50.0, ["无法解析准确性检查结果"]
                
        except Exception as e:
            logger.error(f"准确性检查失败: {str(e)}")
            return 30.0, [f"检查过程出错: {str(e)}"]

    def _check_readability(self, diagram_result: DiagramResult) -> Tuple[float, List[str]]:
        """检查可读性"""
        issues = []
        score = 100.0
        
        if not diagram_result.diagram_code:
            return 0.0, ["图表代码为空"]
        
        lines = diagram_result.diagram_code.split('\n')
        
        # 检查命名规范
        for line in lines:
            line = line.strip()
            if line and not line.startswith('%'):
                # 检查是否有过长的标识符
                words = re.findall(r'\b\w+\b', line)
                for word in words:
                    if len(word) > 30:
                        issues.append(f"标识符过长: {word[:20]}...")
                        score -= 5
                
                # 检查是否有中文字符但没有引号
                if re.search(r'[\u4e00-\u9fff]', line) and '"' not in line:
                    issues.append("中文标签应该使用引号包围")
                    score -= 3
        
        # 检查图表复杂度
        if diagram_result.estimated_elements > 50:
            issues.append("图表元素过多，可能影响可读性")
            score -= 10
        elif diagram_result.estimated_elements > 30:
            issues.append("图表元素较多，建议简化")
            score -= 5
        
        # 检查是否有注释
        has_comments = any(line.strip().startswith('%%') for line in lines)
        if not has_comments and diagram_result.estimated_elements > 10:
            issues.append("复杂图表建议添加注释说明")
            score -= 5
        
        return max(score, 0.0), issues

    def _check_compliance(self, diagram_result: DiagramResult) -> Tuple[float, List[str]]:
        """检查规范符合性"""
        issues = []
        score = 100.0
        
        if not diagram_result.diagram_code:
            return 0.0, ["图表代码为空"]
        
        lines = diagram_result.diagram_code.split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # 检查图表类型声明
        diagram_type_patterns = {
            "er_diagram": r"erDiagram",
            "uml_class": r"classDiagram",
            "sequence": r"sequenceDiagram",
            "flowchart": r"flowchart|graph",
            "use_case": r"graph",
            "activity": r"flowchart|graph",
            "collaboration": r"graph",
            "function_structure": r"graph",
            "system_architecture": r"graph"
        }
        
        expected_pattern = diagram_type_patterns.get(diagram_result.diagram_type)
        if expected_pattern and not re.search(expected_pattern, first_line):
            issues.append(f"图表类型声明不正确，应以{expected_pattern}开头")
            score -= 20
        
        # 检查语法规范
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('%'):
                # 检查箭头语法
                if '-->' in line or '---' in line:
                    if not re.search(r'\w+\s*(-->|---)\s*\w+', line):
                        issues.append(f"第{i+1}行箭头语法不规范")
                        score -= 3
                
                # 检查引号使用
                if re.search(r'[\u4e00-\u9fff]', line):
                    if not ('"' in line or "'" in line):
                        issues.append(f"第{i+1}行中文内容应使用引号")
                        score -= 2
        
        return max(score, 0.0), issues

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """计算总体质量分数"""
        weighted_score = 0.0
        for category, score in scores.items():
            weight = self.quality_weights.get(category, 0)
            weighted_score += score * weight
        
        return round(weighted_score, 1)

    def _determine_quality_level(self, score: float) -> QualityLevel:
        """确定质量等级"""
        for level, threshold in self.quality_thresholds.items():
            if score >= threshold:
                return level
        return QualityLevel.POOR

    async def _generate_improvement_suggestions(
        self,
        diagram_result: DiagramResult,
        issues: Dict[str, List[str]]
    ) -> List[str]:
        """生成改进建议"""
        try:
            all_issues = []
            for category, issue_list in issues.items():
                all_issues.extend([f"{category}: {issue}" for issue in issue_list])
            
            if not all_issues:
                return ["图表质量良好，无需改进"]
            
            suggestion_prompt = f"""
基于以下质量检查发现的问题，请提供具体的改进建议：

图表类型：{diagram_result.diagram_type}
发现的问题：
{chr(10).join(all_issues)}

请提供3-5条具体的改进建议，每条建议应该：
1. 针对具体问题
2. 提供可操作的解决方案
3. 简洁明了

请以JSON格式返回：
{{
    "suggestions": ["建议1", "建议2", "建议3"]
}}
"""
            
            response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": suggestion_prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            result_data = self._extract_json_from_response(response)
            if result_data and 'suggestions' in result_data:
                return result_data['suggestions']
            else:
                # 生成默认建议
                return self._generate_default_suggestions(issues)
                
        except Exception as e:
            logger.error(f"生成改进建议失败: {str(e)}")
            return self._generate_default_suggestions(issues)

    def _generate_default_suggestions(self, issues: Dict[str, List[str]]) -> List[str]:
        """生成默认改进建议"""
        suggestions = []
        
        if issues.get('syntax_issues'):
            suggestions.append("修复语法错误，确保Mermaid代码符合规范")
        
        if issues.get('missing_elements'):
            suggestions.append("补充缺失的关键元素，确保图表完整性")
        
        if issues.get('accuracy_issues'):
            suggestions.append("检查并修正图表中的错误关系和属性")
        
        if issues.get('readability_issues'):
            suggestions.append("优化图表布局和命名，提高可读性")
        
        if issues.get('compliance_issues'):
            suggestions.append("调整图表格式，符合Mermaid语法规范")
        
        if not suggestions:
            suggestions.append("图表质量良好，建议保持当前标准")
        
        return suggestions

    async def batch_quality_check(
        self,
        diagram_results: Dict[str, DiagramResult],
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any]
    ) -> Dict[str, QualityCheckResult]:
        """批量质量检查"""
        results = {}
        
        for diagram_type, diagram_result in diagram_results.items():
            try:
                quality_result = await self.check_diagram_quality(
                    diagram_result, requirement_result, system_result
                )
                results[diagram_type] = quality_result
                
                logger.info(f"{diagram_type}质量检查完成: {quality_result.overall_quality.value}")
                
            except Exception as e:
                logger.error(f"{diagram_type}质量检查失败: {str(e)}")
                results[diagram_type] = QualityCheckResult(
                    overall_quality=QualityLevel.POOR,
                    quality_score=0.0,
                    syntax_valid=False,
                    completeness_score=0.0,
                    accuracy_score=0.0,
                    readability_score=0.0,
                    compliance_score=0.0,
                    syntax_issues=[f"检查失败: {str(e)}"],
                    missing_elements=[],
                    accuracy_issues=[],
                    readability_issues=[],
                    compliance_issues=[],
                    improvement_suggestions=[],
                    check_details={}
                )
        
        return results

    def get_quality_summary(self, quality_results: Dict[str, QualityCheckResult]) -> Dict[str, Any]:
        """获取质量检查摘要"""
        if not quality_results:
            return {}
        
        total_diagrams = len(quality_results)
        quality_distribution = {}
        total_score = 0.0
        
        for result in quality_results.values():
            level = result.overall_quality.value
            quality_distribution[level] = quality_distribution.get(level, 0) + 1
            total_score += result.quality_score
        
        average_score = total_score / total_diagrams if total_diagrams > 0 else 0
        
        # 统计各维度平均分
        dimension_scores = {
            "syntax": sum(r.completeness_score for r in quality_results.values()) / total_diagrams,
            "completeness": sum(r.completeness_score for r in quality_results.values()) / total_diagrams,
            "accuracy": sum(r.accuracy_score for r in quality_results.values()) / total_diagrams,
            "readability": sum(r.readability_score for r in quality_results.values()) / total_diagrams,
            "compliance": sum(r.compliance_score for r in quality_results.values()) / total_diagrams
        }
        
        return {
            "total_diagrams": total_diagrams,
            "average_score": round(average_score, 1),
            "quality_distribution": quality_distribution,
            "dimension_scores": {k: round(v, 1) for k, v in dimension_scores.items()},
            "excellent_count": quality_distribution.get("excellent", 0),
            "good_count": quality_distribution.get("good", 0),
            "fair_count": quality_distribution.get("fair", 0),
            "poor_count": quality_distribution.get("poor", 0)
        } 