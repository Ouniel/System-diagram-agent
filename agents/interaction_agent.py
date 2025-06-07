"""
交互优化代理模块
负责优化用户体验，提供智能交互和个性化建议
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .base_agent import BaseAgent
from .diagram_agent import DiagramResult
from .quality_agent import QualityCheckResult, QualityLevel
from prompts.prompt_templates import PromptTemplates
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class InteractionContext:
    """交互上下文"""
    user_id: str
    session_id: str
    interaction_history: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    current_request: str
    timestamp: datetime

@dataclass
class OptimizationSuggestion:
    """优化建议"""
    suggestion_type: str  # workflow, diagram, interaction
    priority: str  # high, medium, low
    title: str
    description: str
    action_items: List[str]
    expected_benefit: str

@dataclass
class InteractionResult:
    """交互优化结果"""
    optimized_workflow: List[str]
    personalized_suggestions: List[OptimizationSuggestion]
    user_guidance: str
    next_steps: List[str]
    estimated_completion_time: str
    confidence_score: float

class InteractionAgent(BaseAgent):
    """交互优化代理"""
    
    def __init__(self, deepseek_client, config):
        super().__init__(deepseek_client, config)
        self.prompt_templates = PromptTemplates()
        
        # 用户偏好模板
        self.default_preferences = {
            "diagram_complexity": "medium",  # simple, medium, complex
            "detail_level": "standard",      # minimal, standard, detailed
            "interaction_style": "guided",   # guided, autonomous, expert
            "preferred_diagrams": [],        # 用户偏好的图表类型
            "quality_threshold": 75,         # 质量阈值
            "auto_fix": True,               # 是否自动修复
            "batch_mode": False             # 是否批量处理
        }
        
        # 交互模式配置
        self.interaction_modes = {
            "guided": {
                "description": "引导式交互，提供详细步骤指导",
                "features": ["step_by_step", "explanations", "confirmations"]
            },
            "autonomous": {
                "description": "自主式交互，自动完成大部分任务",
                "features": ["auto_decisions", "batch_processing", "minimal_prompts"]
            },
            "expert": {
                "description": "专家模式，提供高级选项和详细控制",
                "features": ["advanced_options", "detailed_feedback", "customization"]
            }
        }

    async def optimize_interaction(
        self,
        context: InteractionContext,
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any],
        diagram_results: Optional[Dict[str, DiagramResult]] = None,
        quality_results: Optional[Dict[str, QualityCheckResult]] = None
    ) -> InteractionResult:
        """
        优化用户交互体验
        
        Args:
            context: 交互上下文
            requirement_result: 需求分析结果
            system_result: 系统理解结果
            diagram_results: 图表生成结果
            quality_results: 质量检查结果
            
        Returns:
            InteractionResult: 交互优化结果
        """
        try:
            logger.info(f"开始交互优化，用户: {context.user_id}")
            
            # 分析用户偏好
            user_preferences = self._analyze_user_preferences(context)
            
            # 生成个性化建议
            personalized_suggestions = await self._generate_personalized_suggestions(
                context, requirement_result, system_result, diagram_results, quality_results
            )
            
            # 优化工作流程
            optimized_workflow = self._optimize_workflow(
                context, requirement_result, user_preferences
            )
            
            # 生成用户指导
            user_guidance = await self._generate_user_guidance(
                context, requirement_result, diagram_results, quality_results
            )
            
            # 确定下一步行动
            next_steps = self._determine_next_steps(
                context, requirement_result, diagram_results, quality_results, user_preferences
            )
            
            # 估算完成时间
            estimated_time = self._estimate_completion_time(
                requirement_result, user_preferences
            )
            
            # 计算置信度
            confidence_score = self._calculate_confidence_score(
                requirement_result, diagram_results, quality_results
            )
            
            result = InteractionResult(
                optimized_workflow=optimized_workflow,
                personalized_suggestions=personalized_suggestions,
                user_guidance=user_guidance,
                next_steps=next_steps,
                estimated_completion_time=estimated_time,
                confidence_score=confidence_score
            )
            
            logger.info(f"交互优化完成，置信度: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"交互优化失败: {str(e)}")
            return InteractionResult(
                optimized_workflow=["发生错误，请重试"],
                personalized_suggestions=[],
                user_guidance=f"处理过程中出现错误: {str(e)}",
                next_steps=["检查输入并重试"],
                estimated_completion_time="未知",
                confidence_score=0.0
            )

    def _analyze_user_preferences(self, context: InteractionContext) -> Dict[str, Any]:
        """分析用户偏好"""
        preferences = self.default_preferences.copy()
        
        # 从用户上下文中提取偏好
        if context.user_preferences:
            preferences.update(context.user_preferences)
        
        # 从历史交互中推断偏好
        if context.interaction_history:
            inferred_prefs = self._infer_preferences_from_history(context.interaction_history)
            preferences.update(inferred_prefs)
        
        # 从当前请求中分析偏好
        current_prefs = self._analyze_current_request_preferences(context.current_request)
        preferences.update(current_prefs)
        
        return preferences

    def _infer_preferences_from_history(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从历史交互中推断用户偏好"""
        preferences = {}
        
        if not history:
            return preferences
        
        # 分析图表类型偏好
        diagram_types = []
        for interaction in history:
            if 'diagram_types' in interaction:
                diagram_types.extend(interaction['diagram_types'])
        
        if diagram_types:
            # 统计最常用的图表类型
            type_counts = {}
            for dtype in diagram_types:
                type_counts[dtype] = type_counts.get(dtype, 0) + 1
            
            # 取前3个最常用的类型
            preferred_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            preferences['preferred_diagrams'] = [t[0] for t in preferred_types]
        
        # 分析复杂度偏好
        complexities = []
        for interaction in history:
            if 'complexity' in interaction:
                complexities.append(interaction['complexity'])
        
        if complexities:
            # 取最常见的复杂度
            complexity_counts = {}
            for comp in complexities:
                complexity_counts[comp] = complexity_counts.get(comp, 0) + 1
            
            most_common = max(complexity_counts.items(), key=lambda x: x[1])
            preferences['diagram_complexity'] = most_common[0]
        
        return preferences

    def _analyze_current_request_preferences(self, request: str) -> Dict[str, Any]:
        """分析当前请求中的偏好信息"""
        preferences = {}
        
        # 分析复杂度偏好
        if any(word in request.lower() for word in ['简单', '简化', 'simple']):
            preferences['diagram_complexity'] = 'simple'
        elif any(word in request.lower() for word in ['复杂', '详细', 'complex', 'detailed']):
            preferences['diagram_complexity'] = 'complex'
        
        # 分析交互风格偏好
        if any(word in request.lower() for word in ['引导', '指导', 'guide', 'help']):
            preferences['interaction_style'] = 'guided'
        elif any(word in request.lower() for word in ['自动', '批量', 'auto', 'batch']):
            preferences['interaction_style'] = 'autonomous'
        elif any(word in request.lower() for word in ['专业', '高级', 'expert', 'advanced']):
            preferences['interaction_style'] = 'expert'
        
        # 分析质量要求
        if any(word in request.lower() for word in ['高质量', '精确', 'high quality', 'precise']):
            preferences['quality_threshold'] = 90
        elif any(word in request.lower() for word in ['快速', '简单', 'quick', 'fast']):
            preferences['quality_threshold'] = 60
        
        return preferences

    async def _generate_personalized_suggestions(
        self,
        context: InteractionContext,
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any],
        diagram_results: Optional[Dict[str, DiagramResult]],
        quality_results: Optional[Dict[str, QualityCheckResult]]
    ) -> List[OptimizationSuggestion]:
        """生成个性化建议"""
        suggestions = []
        
        try:
            # 基于用户偏好的建议
            user_prefs = self._analyze_user_preferences(context)
            
            # 工作流程优化建议
            if user_prefs.get('interaction_style') == 'guided':
                suggestions.append(OptimizationSuggestion(
                    suggestion_type="workflow",
                    priority="medium",
                    title="启用引导模式",
                    description="基于您的偏好，建议使用引导式交互模式",
                    action_items=["启用步骤提示", "提供详细说明", "确认每个步骤"],
                    expected_benefit="更清晰的操作流程和更好的理解"
                ))
            
            # 图表类型建议
            if diagram_results:
                low_quality_diagrams = [
                    dtype for dtype, result in quality_results.items()
                    if result.overall_quality in [QualityLevel.POOR, QualityLevel.FAIR]
                ] if quality_results else []
                
                if low_quality_diagrams:
                    suggestions.append(OptimizationSuggestion(
                        suggestion_type="diagram",
                        priority="high",
                        title="改进低质量图表",
                        description=f"检测到{len(low_quality_diagrams)}个图表质量较低",
                        action_items=[
                            f"重新生成{', '.join(low_quality_diagrams)}",
                            "调整参数设置",
                            "增加详细信息"
                        ],
                        expected_benefit="提高图表质量和准确性"
                    ))
            
            # 基于AI的智能建议
            ai_suggestions = await self._generate_ai_suggestions(
                context, requirement_result, system_result, diagram_results, quality_results
            )
            suggestions.extend(ai_suggestions)
            
        except Exception as e:
            logger.error(f"生成个性化建议失败: {str(e)}")
            suggestions.append(OptimizationSuggestion(
                suggestion_type="interaction",
                priority="low",
                title="建议生成失败",
                description=f"无法生成个性化建议: {str(e)}",
                action_items=["使用默认设置继续"],
                expected_benefit="确保流程继续进行"
            ))
        
        return suggestions

    async def _generate_ai_suggestions(
        self,
        context: InteractionContext,
        requirement_result: Dict[str, Any],
        system_result: Dict[str, Any],
        diagram_results: Optional[Dict[str, DiagramResult]],
        quality_results: Optional[Dict[str, QualityCheckResult]]
    ) -> List[OptimizationSuggestion]:
        """使用AI生成智能建议"""
        try:
            suggestion_prompt = f"""
基于以下信息，为用户提供3-5个个性化的优化建议：

用户请求：{context.current_request}
需求分析：{json.dumps(requirement_result, ensure_ascii=False, indent=2)}

当前状态：
- 已生成图表：{list(diagram_results.keys()) if diagram_results else '无'}
- 质量检查：{len(quality_results) if quality_results else 0}个图表已检查

请提供建议来优化：
1. 工作流程效率
2. 图表质量
3. 用户体验

请以JSON格式返回：
{{
    "suggestions": [
        {{
            "type": "workflow/diagram/interaction",
            "priority": "high/medium/low",
            "title": "建议标题",
            "description": "详细描述",
            "actions": ["行动项1", "行动项2"],
            "benefit": "预期收益"
        }}
    ]
}}
"""
            
            response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": suggestion_prompt}],
                temperature=0.4,
                max_tokens=1500
            )
            
            result_data = self._extract_json_from_response(response)
            if result_data and 'suggestions' in result_data:
                ai_suggestions = []
                for sugg in result_data['suggestions']:
                    ai_suggestions.append(OptimizationSuggestion(
                        suggestion_type=sugg.get('type', 'interaction'),
                        priority=sugg.get('priority', 'medium'),
                        title=sugg.get('title', ''),
                        description=sugg.get('description', ''),
                        action_items=sugg.get('actions', []),
                        expected_benefit=sugg.get('benefit', '')
                    ))
                return ai_suggestions
            
        except Exception as e:
            logger.error(f"AI建议生成失败: {str(e)}")
        
        return []

    def _optimize_workflow(
        self,
        context: InteractionContext,
        requirement_result: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> List[str]:
        """优化工作流程"""
        workflow = []
        
        interaction_style = user_preferences.get('interaction_style', 'guided')
        diagram_types = requirement_result.get('recommended_diagrams', [])
        
        if interaction_style == 'guided':
            workflow = [
                "1. 确认需求理解正确性",
                "2. 选择要生成的图表类型",
                "3. 逐个生成图表并确认",
                "4. 进行质量检查",
                "5. 根据反馈进行优化",
                "6. 导出最终结果"
            ]
        elif interaction_style == 'autonomous':
            workflow = [
                "1. 自动分析需求",
                "2. 批量生成所有推荐图表",
                "3. 自动质量检查和修复",
                "4. 生成完整报告"
            ]
        elif interaction_style == 'expert':
            workflow = [
                "1. 详细需求分析和参数配置",
                "2. 自定义图表生成策略",
                "3. 高级质量检查和优化",
                "4. 专业报告和建议",
                "5. 导出多种格式"
            ]
        
        # 根据图表数量调整工作流程
        if len(diagram_types) > 5:
            workflow.insert(-1, "建议分批处理图表以提高效率")
        
        return workflow

    async def _generate_user_guidance(
        self,
        context: InteractionContext,
        requirement_result: Dict[str, Any],
        diagram_results: Optional[Dict[str, DiagramResult]],
        quality_results: Optional[Dict[str, QualityCheckResult]]
    ) -> str:
        """生成用户指导"""
        try:
            guidance_prompt = f"""
为用户提供当前状态的指导说明：

用户请求：{context.current_request}
当前进度：
- 需求分析：{'已完成' if requirement_result else '未完成'}
- 图表生成：{f'已生成{len(diagram_results)}个图表' if diagram_results else '未开始'}
- 质量检查：{f'已检查{len(quality_results)}个图表' if quality_results else '未开始'}

请提供：
1. 当前状态说明
2. 下一步操作建议
3. 注意事项
4. 预期结果

请用友好、专业的语调，控制在200字以内。
"""
            
            response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": guidance_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"生成用户指导失败: {str(e)}")
            return "系统正在处理您的请求，请稍候..."

    def _determine_next_steps(
        self,
        context: InteractionContext,
        requirement_result: Dict[str, Any],
        diagram_results: Optional[Dict[str, DiagramResult]],
        quality_results: Optional[Dict[str, QualityCheckResult]],
        user_preferences: Dict[str, Any]
    ) -> List[str]:
        """确定下一步行动"""
        next_steps = []
        
        # 根据当前状态确定下一步
        if not diagram_results:
            # 还没有生成图表
            recommended_diagrams = requirement_result.get('recommended_diagrams', [])
            if recommended_diagrams:
                if user_preferences.get('batch_mode', False):
                    next_steps.append(f"批量生成{len(recommended_diagrams)}个推荐图表")
                else:
                    next_steps.append(f"开始生成第一个图表：{recommended_diagrams[0]}")
                    if len(recommended_diagrams) > 1:
                        next_steps.append(f"准备生成其余{len(recommended_diagrams)-1}个图表")
            else:
                next_steps.append("重新分析需求，确定图表类型")
        
        elif not quality_results:
            # 已生成图表但未质量检查
            next_steps.append(f"对{len(diagram_results)}个图表进行质量检查")
            next_steps.append("根据检查结果进行优化")
        
        else:
            # 已完成质量检查
            poor_quality = [
                dtype for dtype, result in quality_results.items()
                if result.overall_quality == QualityLevel.POOR
            ]
            
            if poor_quality:
                next_steps.append(f"重新生成质量较差的图表：{', '.join(poor_quality)}")
            
            good_quality = [
                dtype for dtype, result in quality_results.items()
                if result.overall_quality in [QualityLevel.GOOD, QualityLevel.EXCELLENT]
            ]
            
            if good_quality:
                next_steps.append(f"导出高质量图表：{', '.join(good_quality)}")
            
            next_steps.append("生成最终报告和总结")
        
        # 添加用户偏好相关的步骤
        if user_preferences.get('auto_fix', True) and quality_results:
            fixable_issues = sum(1 for result in quality_results.values() 
                               if result.improvement_suggestions)
            if fixable_issues > 0:
                next_steps.append(f"自动修复{fixable_issues}个可优化的图表")
        
        return next_steps

    def _estimate_completion_time(
        self,
        requirement_result: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> str:
        """估算完成时间"""
        base_time = 30  # 基础时间（秒）
        
        # 根据图表数量调整
        diagram_count = len(requirement_result.get('recommended_diagrams', []))
        time_per_diagram = 15  # 每个图表15秒
        
        total_time = base_time + (diagram_count * time_per_diagram)
        
        # 根据复杂度调整
        complexity = user_preferences.get('diagram_complexity', 'medium')
        if complexity == 'complex':
            total_time *= 1.5
        elif complexity == 'simple':
            total_time *= 0.8
        
        # 根据质量要求调整
        quality_threshold = user_preferences.get('quality_threshold', 75)
        if quality_threshold >= 90:
            total_time *= 1.3
        elif quality_threshold <= 60:
            total_time *= 0.9
        
        # 转换为友好的时间格式
        if total_time < 60:
            return f"{int(total_time)}秒"
        elif total_time < 3600:
            minutes = int(total_time / 60)
            seconds = int(total_time % 60)
            return f"{minutes}分{seconds}秒"
        else:
            hours = int(total_time / 3600)
            minutes = int((total_time % 3600) / 60)
            return f"{hours}小时{minutes}分钟"

    def _calculate_confidence_score(
        self,
        requirement_result: Dict[str, Any],
        diagram_results: Optional[Dict[str, DiagramResult]],
        quality_results: Optional[Dict[str, QualityCheckResult]]
    ) -> float:
        """计算置信度分数"""
        confidence = 0.0
        
        # 需求理解置信度 (30%)
        req_confidence = requirement_result.get('confidence_score', 0.5)
        confidence += req_confidence * 0.3
        
        # 图表生成置信度 (40%)
        if diagram_results:
            valid_diagrams = sum(1 for result in diagram_results.values() if result.is_valid)
            generation_confidence = valid_diagrams / len(diagram_results)
            confidence += generation_confidence * 0.4
        
        # 质量检查置信度 (30%)
        if quality_results:
            avg_quality_score = sum(result.quality_score for result in quality_results.values()) / len(quality_results)
            quality_confidence = avg_quality_score / 100
            confidence += quality_confidence * 0.3
        
        return round(min(confidence, 1.0), 2)

    def create_interaction_context(
        self,
        user_id: str,
        session_id: str,
        current_request: str,
        interaction_history: Optional[List[Dict[str, Any]]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> InteractionContext:
        """创建交互上下文"""
        return InteractionContext(
            user_id=user_id,
            session_id=session_id,
            interaction_history=interaction_history or [],
            user_preferences=user_preferences or {},
            current_request=current_request,
            timestamp=datetime.now()
        )

    def update_user_preferences(
        self,
        context: InteractionContext,
        new_preferences: Dict[str, Any]
    ) -> InteractionContext:
        """更新用户偏好"""
        context.user_preferences.update(new_preferences)
        return context

    def get_interaction_summary(
        self,
        context: InteractionContext,
        result: InteractionResult
    ) -> Dict[str, Any]:
        """获取交互摘要"""
        return {
            "user_id": context.user_id,
            "session_id": context.session_id,
            "request": context.current_request,
            "timestamp": context.timestamp.isoformat(),
            "workflow_steps": len(result.optimized_workflow),
            "suggestions_count": len(result.personalized_suggestions),
            "next_steps_count": len(result.next_steps),
            "estimated_time": result.estimated_completion_time,
            "confidence_score": result.confidence_score,
            "user_preferences": context.user_preferences
        } 