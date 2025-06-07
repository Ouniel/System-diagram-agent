"""
主控制器模块
协调所有代理的工作流程，管理整个图表生成过程
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from .requirement_agent import RequirementAgent
from .system_agent import SystemAgent
from .diagram_agent import DiagramAgent, DiagramResult
from .quality_agent import QualityAgent, QualityCheckResult
from .interaction_agent import InteractionAgent, InteractionContext, InteractionResult
from api.deepseek_client import DeepSeekClient
from utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ProcessingSession:
    """处理会话"""
    session_id: str
    user_id: str
    user_request: str
    start_time: datetime
    current_stage: str
    status: str  # pending, processing, completed, failed
    
    # 各阶段结果
    requirement_result: Optional[Dict[str, Any]] = None
    system_result: Optional[Dict[str, Any]] = None
    diagram_results: Optional[Dict[str, DiagramResult]] = None
    quality_results: Optional[Dict[str, QualityCheckResult]] = None
    interaction_result: Optional[InteractionResult] = None
    
    # 元数据
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    final_output: Optional[Dict[str, Any]] = None

@dataclass
class ControllerConfig:
    """控制器配置"""
    max_concurrent_sessions: int = 10
    session_timeout: int = 3600  # 1小时
    auto_quality_check: bool = True
    auto_fix_diagrams: bool = True
    enable_interaction_optimization: bool = True
    default_diagram_types: List[str] = None
    
    def __post_init__(self):
        if self.default_diagram_types is None:
            self.default_diagram_types = ["flowchart", "system_architecture"]

class MainController:
    """主控制器"""
    
    def __init__(self, deepseek_client: DeepSeekClient, config: ControllerConfig = None):
        self.deepseek_client = deepseek_client
        self.config = config or ControllerConfig()
        
        # 初始化各个代理
        self.requirement_agent = RequirementAgent(deepseek_client)
        self.system_agent = SystemAgent(deepseek_client)
        self.diagram_agent = DiagramAgent(deepseek_client)
        self.quality_agent = QualityAgent(deepseek_client)
        self.interaction_agent = InteractionAgent(deepseek_client)
        
        # 会话管理
        self.active_sessions: Dict[str, ProcessingSession] = {}
        self.session_history: List[ProcessingSession] = []
        
        logger.info("主控制器初始化完成")

    async def process_user_request(
        self,
        user_request: str,
        user_id: str = None,
        session_id: str = None,
        user_preferences: Dict[str, Any] = None,
        interaction_history: List[Dict[str, Any]] = None
    ) -> ProcessingSession:
        """
        处理用户请求的主入口
        
        Args:
            user_request: 用户请求
            user_id: 用户ID
            session_id: 会话ID（可选，不提供则自动生成）
            user_preferences: 用户偏好
            interaction_history: 交互历史
            
        Returns:
            ProcessingSession: 处理会话结果
        """
        # 生成会话ID
        if not session_id:
            session_id = str(uuid.uuid4())
        if not user_id:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # 创建处理会话
        session = ProcessingSession(
            session_id=session_id,
            user_id=user_id,
            user_request=user_request,
            start_time=datetime.now(),
            current_stage="初始化",
            status="pending"
        )
        
        # 检查并发限制
        if len(self.active_sessions) >= self.config.max_concurrent_sessions:
            session.status = "failed"
            session.error_message = "系统繁忙，请稍后重试"
            return session
        
        self.active_sessions[session_id] = session
        
        try:
            logger.info(f"开始处理用户请求，会话ID: {session_id}")
            session.status = "processing"
            
            # 创建交互上下文
            interaction_context = self.interaction_agent.create_interaction_context(
                user_id=user_id,
                session_id=session_id,
                current_request=user_request,
                interaction_history=interaction_history,
                user_preferences=user_preferences
            )
            
            # 执行完整的处理流程
            await self._execute_processing_pipeline(session, interaction_context)
            
            # 标记完成
            session.status = "completed"
            session.processing_time = (datetime.now() - session.start_time).total_seconds()
            
            logger.info(f"用户请求处理完成，耗时: {session.processing_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"处理用户请求失败: {str(e)}")
            session.status = "failed"
            session.error_message = str(e)
            session.processing_time = (datetime.now() - session.start_time).total_seconds()
        
        finally:
            # 移动到历史记录
            self.session_history.append(session)
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
        
        return session

    async def _execute_processing_pipeline(
        self,
        session: ProcessingSession,
        interaction_context: InteractionContext
    ):
        """执行处理管道"""
        
        # 阶段1: 需求理解
        session.current_stage = "需求理解"
        logger.info(f"[{session.session_id}] 开始需求理解阶段")
        
        session.requirement_result = await self.requirement_agent.analyze_requirements(
            session.user_request
        )
        
        # 阶段2: 系统理解
        session.current_stage = "系统理解"
        logger.info(f"[{session.session_id}] 开始系统理解阶段")
        
        session.system_result = await self.system_agent.analyze_system(
            session.user_request, session.requirement_result
        )
        
        # 阶段3: 交互优化（第一次）
        if self.config.enable_interaction_optimization:
            session.current_stage = "交互优化"
            logger.info(f"[{session.session_id}] 开始交互优化阶段")
            
            session.interaction_result = await self.interaction_agent.optimize_interaction(
                interaction_context,
                session.requirement_result,
                session.system_result
            )
        
        # 阶段4: 图表生成
        session.current_stage = "图表生成"
        logger.info(f"[{session.session_id}] 开始图表生成阶段")
        
        # 确定要生成的图表类型
        diagram_types = self._determine_diagram_types(
            session.requirement_result,
            session.interaction_result
        )
        
        # 生成图表
        session.diagram_results = await self.diagram_agent.generate_multiple_diagrams(
            session.requirement_result,
            session.system_result,
            diagram_types
        )
        
        # 阶段5: 质量检查
        if self.config.auto_quality_check:
            session.current_stage = "质量检查"
            logger.info(f"[{session.session_id}] 开始质量检查阶段")
            
            session.quality_results = await self.quality_agent.batch_quality_check(
                session.diagram_results,
                session.requirement_result,
                session.system_result
            )
            
            # 自动修复低质量图表
            if self.config.auto_fix_diagrams:
                await self._auto_fix_diagrams(session)
        
        # 阶段6: 最终交互优化
        if self.config.enable_interaction_optimization:
            session.current_stage = "最终优化"
            logger.info(f"[{session.session_id}] 开始最终优化阶段")
            
            session.interaction_result = await self.interaction_agent.optimize_interaction(
                interaction_context,
                session.requirement_result,
                session.system_result,
                session.diagram_results,
                session.quality_results
            )
        
        # 阶段7: 生成最终输出
        session.current_stage = "生成输出"
        logger.info(f"[{session.session_id}] 生成最终输出")
        
        session.final_output = self._generate_final_output(session)

    def _determine_diagram_types(
        self,
        requirement_result: Dict[str, Any],
        interaction_result: Optional[InteractionResult]
    ) -> List[str]:
        """确定要生成的图表类型"""
        
        # 从需求分析结果获取推荐图表
        recommended_diagrams = requirement_result.get('recommended_diagrams', [])
        
        # 如果有交互优化结果，考虑用户偏好
        if interaction_result and interaction_result.personalized_suggestions:
            for suggestion in interaction_result.personalized_suggestions:
                if suggestion.suggestion_type == "diagram":
                    # 可以根据建议调整图表类型
                    pass
        
        # 如果没有推荐图表，使用默认类型
        if not recommended_diagrams:
            recommended_diagrams = self.config.default_diagram_types
        
        return recommended_diagrams

    async def _auto_fix_diagrams(self, session: ProcessingSession):
        """自动修复低质量图表"""
        if not session.quality_results:
            return
        
        poor_quality_diagrams = [
            diagram_type for diagram_type, quality_result in session.quality_results.items()
            if quality_result.quality_score < 60  # 质量分数低于60的图表
        ]
        
        if poor_quality_diagrams:
            logger.info(f"[{session.session_id}] 自动修复{len(poor_quality_diagrams)}个低质量图表")
            
            # 重新生成低质量图表
            for diagram_type in poor_quality_diagrams:
                try:
                    new_diagram = await self.diagram_agent.generate_diagram(
                        session.requirement_result,
                        session.system_result,
                        diagram_type
                    )
                    
                    # 更新结果
                    session.diagram_results[diagram_type] = new_diagram
                    
                    # 重新质量检查
                    new_quality = await self.quality_agent.check_diagram_quality(
                        new_diagram,
                        session.requirement_result,
                        session.system_result
                    )
                    session.quality_results[diagram_type] = new_quality
                    
                    logger.info(f"[{session.session_id}] {diagram_type}重新生成完成，新质量分数: {new_quality.quality_score}")
                    
                except Exception as e:
                    logger.error(f"[{session.session_id}] 修复{diagram_type}失败: {str(e)}")

    def _generate_final_output(self, session: ProcessingSession) -> Dict[str, Any]:
        """生成最终输出"""
        output = {
            "session_info": {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "user_request": session.user_request,
                "processing_time": session.processing_time,
                "status": session.status
            },
            "requirement_analysis": session.requirement_result,
            "system_analysis": session.system_result,
            "diagrams": {},
            "quality_reports": {},
            "interaction_optimization": None,
            "summary": {}
        }
        
        # 添加图表结果
        if session.diagram_results:
            for diagram_type, diagram_result in session.diagram_results.items():
                output["diagrams"][diagram_type] = {
                    "diagram_code": diagram_result.diagram_code,
                    "description": diagram_result.description,
                    "complexity_level": diagram_result.complexity_level,
                    "estimated_elements": diagram_result.estimated_elements,
                    "is_valid": diagram_result.is_valid,
                    "generation_notes": diagram_result.generation_notes
                }
        
        # 添加质量报告
        if session.quality_results:
            for diagram_type, quality_result in session.quality_results.items():
                output["quality_reports"][diagram_type] = {
                    "overall_quality": quality_result.overall_quality.value,
                    "quality_score": quality_result.quality_score,
                    "syntax_valid": quality_result.syntax_valid,
                    "improvement_suggestions": quality_result.improvement_suggestions
                }
        
        # 添加交互优化结果
        if session.interaction_result:
            output["interaction_optimization"] = {
                "optimized_workflow": session.interaction_result.optimized_workflow,
                "user_guidance": session.interaction_result.user_guidance,
                "next_steps": session.interaction_result.next_steps,
                "estimated_completion_time": session.interaction_result.estimated_completion_time,
                "confidence_score": session.interaction_result.confidence_score
            }
        
        # 生成摘要
        output["summary"] = self._generate_summary(session)
        
        return output

    def _generate_summary(self, session: ProcessingSession) -> Dict[str, Any]:
        """生成处理摘要"""
        summary = {
            "total_diagrams": len(session.diagram_results) if session.diagram_results else 0,
            "successful_diagrams": 0,
            "average_quality_score": 0.0,
            "processing_stages": session.current_stage,
            "recommendations": []
        }
        
        if session.diagram_results and session.quality_results:
            successful_diagrams = sum(
                1 for result in session.diagram_results.values() if result.is_valid
            )
            summary["successful_diagrams"] = successful_diagrams
            
            total_quality_score = sum(
                result.quality_score for result in session.quality_results.values()
            )
            summary["average_quality_score"] = total_quality_score / len(session.quality_results)
        
        # 添加建议
        if session.interaction_result and session.interaction_result.personalized_suggestions:
            summary["recommendations"] = [
                {
                    "type": sugg.suggestion_type,
                    "priority": sugg.priority,
                    "title": sugg.title,
                    "description": sugg.description
                }
                for sugg in session.interaction_result.personalized_suggestions[:3]  # 只取前3个
            ]
        
        return summary

    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        # 检查活跃会话
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            return {
                "session_id": session_id,
                "status": session.status,
                "current_stage": session.current_stage,
                "start_time": session.start_time.isoformat(),
                "processing_time": (datetime.now() - session.start_time).total_seconds()
            }
        
        # 检查历史会话
        for session in self.session_history:
            if session.session_id == session_id:
                return {
                    "session_id": session_id,
                    "status": session.status,
                    "current_stage": session.current_stage,
                    "start_time": session.start_time.isoformat(),
                    "processing_time": session.processing_time,
                    "error_message": session.error_message
                }
        
        return None

    async def cancel_session(self, session_id: str) -> bool:
        """取消会话"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.status = "cancelled"
            session.error_message = "用户取消"
            session.processing_time = (datetime.now() - session.start_time).total_seconds()
            
            # 移动到历史记录
            self.session_history.append(session)
            del self.active_sessions[session_id]
            
            logger.info(f"会话 {session_id} 已取消")
            return True
        
        return False

    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        total_sessions = len(self.session_history)
        successful_sessions = sum(1 for s in self.session_history if s.status == "completed")
        failed_sessions = sum(1 for s in self.session_history if s.status == "failed")
        
        if total_sessions > 0:
            avg_processing_time = sum(
                s.processing_time for s in self.session_history 
                if s.processing_time is not None
            ) / total_sessions
        else:
            avg_processing_time = 0.0
        
        return {
            "active_sessions": len(self.active_sessions),
            "total_sessions": total_sessions,
            "successful_sessions": successful_sessions,
            "failed_sessions": failed_sessions,
            "success_rate": successful_sessions / total_sessions if total_sessions > 0 else 0,
            "average_processing_time": avg_processing_time,
            "system_status": "healthy" if len(self.active_sessions) < self.config.max_concurrent_sessions else "busy"
        }

    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if (current_time - session.start_time).total_seconds() > self.config.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            session = self.active_sessions[session_id]
            session.status = "timeout"
            session.error_message = "会话超时"
            session.processing_time = (current_time - session.start_time).total_seconds()
            
            self.session_history.append(session)
            del self.active_sessions[session_id]
            
            logger.warning(f"会话 {session_id} 因超时被清理")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 测试DeepSeek API连接
            test_response = await self.deepseek_client.chat_completion(
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=10
            )
            
            api_status = "healthy" if test_response else "unhealthy"
        except Exception as e:
            api_status = f"error: {str(e)}"
        
        return {
            "controller_status": "healthy",
            "api_status": api_status,
            "active_sessions": len(self.active_sessions),
            "max_concurrent_sessions": self.config.max_concurrent_sessions,
            "agents_status": {
                "requirement_agent": "healthy",
                "system_agent": "healthy", 
                "diagram_agent": "healthy",
                "quality_agent": "healthy",
                "interaction_agent": "healthy"
            }
        } 