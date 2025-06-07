"""
系统理解Agent
负责深入分析用户描述的系统，提取绘图所需的核心信息
"""

from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from prompts.prompt_templates import PromptTemplates
from utils.validators import validate_system_analysis


class SystemAgent(BaseAgent):
    """系统理解Agent - 深入分析系统架构和组件"""
    
    def process(self, input_data: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理系统描述，提取绘图所需信息
        
        Args:
            input_data: 用户的系统描述
            context: 上下文信息（包含需求分析结果）
        
        Returns:
            系统分析结果
        """
        try:
            # 验证输入
            if not self.validate_input(input_data):
                raise ValueError("无效的输入数据")
            
            # 更新上下文
            if context:
                self.context.update(context)
            
            # 获取图表类型
            diagram_type = self.get_context("diagram_type", "流程图")
            
            self.logger.info(f"开始系统理解分析，目标图表类型: {diagram_type}")
            
            # 构建prompt
            prompt = PromptTemplates.get_prompt(
                "system_understanding",
                用户的系统描述=input_data,
                从需求理解模块获得的图表类型=diagram_type
            )
            
            # 调用API，使用推理模型获得更好的分析结果
            response = self._retry_api_call(
                prompt, 
                model="deepseek-reasoner",  # 使用推理模型
                temperature=0.2  # 较低温度确保分析准确性
            )
            
            # 解析和结构化响应
            analysis_result = self._structure_analysis(response, diagram_type)
            
            # 验证结果
            if not self._validate_analysis_result(analysis_result):
                self.logger.warning("系统分析结果可能不完整")
            
            # 更新上下文
            self.update_context("system_analysis", analysis_result)
            self.update_context("structured_info", analysis_result)
            
            self.logger.info("系统分析完成")
            
            return self.format_output(analysis_result)
            
        except Exception as e:
            return self.handle_error(e)
    
    def _structure_analysis(self, response: str, diagram_type: str) -> Dict[str, Any]:
        """
        根据图表类型结构化分析结果
        
        Args:
            response: API响应文本
            diagram_type: 目标图表类型
        
        Returns:
            结构化的分析结果
        """
        # 基础结构
        structured_result = {
            "diagram_type": diagram_type,
            "raw_analysis": response,
            "entities": [],
            "relationships": [],
            "components": [],
            "processes": [],
            "actors": [],
            "use_cases": [],
            "interactions": [],
            "activities": [],
            "functions": [],
            "architecture_layers": []
        }
        
        # 根据图表类型提取特定信息
        if diagram_type in ["E-R图"]:
            structured_result.update(self._extract_er_info(response))
        elif diagram_type in ["UML类图"]:
            structured_result.update(self._extract_class_info(response))
        elif diagram_type in ["UML用例图"]:
            structured_result.update(self._extract_usecase_info(response))
        elif diagram_type in ["流程图"]:
            structured_result.update(self._extract_process_info(response))
        elif diagram_type in ["时序图"]:
            structured_result.update(self._extract_sequence_info(response))
        elif diagram_type in ["活动图"]:
            structured_result.update(self._extract_activity_info(response))
        elif diagram_type in ["协作图"]:
            structured_result.update(self._extract_collaboration_info(response))
        elif diagram_type in ["功能结构图"]:
            structured_result.update(self._extract_function_info(response))
        elif diagram_type in ["系统架构图"]:
            structured_result.update(self._extract_architecture_info(response))
        
        return structured_result
    
    def _extract_er_info(self, text: str) -> Dict[str, Any]:
        """提取E-R图相关信息"""
        entities = []
        relationships = []
        
        lines = text.split('\n')
        current_entity = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找实体
            if any(keyword in line.lower() for keyword in ['实体', 'entity', '表', 'table']):
                # 提取实体名称
                entity_name = self._extract_entity_name(line)
                if entity_name:
                    current_entity = {
                        "name": entity_name,
                        "attributes": [],
                        "primary_key": None
                    }
                    entities.append(current_entity)
            
            # 查找属性
            elif current_entity and any(keyword in line.lower() for keyword in ['属性', 'attribute', '字段', 'field']):
                attribute = self._extract_attribute(line)
                if attribute:
                    current_entity["attributes"].append(attribute)
            
            # 查找关系
            elif any(keyword in line.lower() for keyword in ['关系', 'relationship', '关联']):
                relationship = self._extract_relationship(line)
                if relationship:
                    relationships.append(relationship)
        
        return {
            "entities": entities,
            "relationships": relationships
        }
    
    def _extract_class_info(self, text: str) -> Dict[str, Any]:
        """提取类图相关信息"""
        classes = []
        relationships = []
        
        lines = text.split('\n')
        current_class = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找类
            if any(keyword in line.lower() for keyword in ['类', 'class', '对象']):
                class_name = self._extract_class_name(line)
                if class_name:
                    current_class = {
                        "name": class_name,
                        "attributes": [],
                        "methods": [],
                        "visibility": "public"
                    }
                    classes.append(current_class)
            
            # 查找方法和属性
            elif current_class:
                if any(keyword in line.lower() for keyword in ['方法', 'method', '函数']):
                    method = self._extract_method(line)
                    if method:
                        current_class["methods"].append(method)
                elif any(keyword in line.lower() for keyword in ['属性', 'attribute', '成员']):
                    attribute = self._extract_class_attribute(line)
                    if attribute:
                        current_class["attributes"].append(attribute)
        
        return {
            "classes": classes,
            "relationships": relationships
        }
    
    def _extract_usecase_info(self, text: str) -> Dict[str, Any]:
        """提取用例图相关信息"""
        actors = []
        use_cases = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找参与者
            if any(keyword in line.lower() for keyword in ['参与者', 'actor', '用户', '角色']):
                actor = self._extract_actor(line)
                if actor:
                    actors.append(actor)
            
            # 查找用例
            elif any(keyword in line.lower() for keyword in ['用例', 'use case', '功能']):
                use_case = self._extract_use_case(line)
                if use_case:
                    use_cases.append(use_case)
        
        return {
            "actors": actors,
            "use_cases": use_cases
        }
    
    def _extract_process_info(self, text: str) -> Dict[str, Any]:
        """提取流程图相关信息"""
        processes = []
        decisions = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找流程步骤
            if any(keyword in line.lower() for keyword in ['步骤', 'step', '流程', '处理']):
                process = self._extract_process_step(line)
                if process:
                    processes.append(process)
            
            # 查找决策点
            elif any(keyword in line.lower() for keyword in ['判断', 'decision', '条件', '分支']):
                decision = self._extract_decision(line)
                if decision:
                    decisions.append(decision)
        
        return {
            "processes": processes,
            "decisions": decisions
        }
    
    def _extract_sequence_info(self, text: str) -> Dict[str, Any]:
        """提取时序图相关信息"""
        participants = []
        interactions = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找参与对象
            if any(keyword in line.lower() for keyword in ['对象', 'object', '参与者', '组件']):
                participant = self._extract_participant(line)
                if participant:
                    participants.append(participant)
            
            # 查找交互消息
            elif any(keyword in line.lower() for keyword in ['消息', 'message', '调用', '交互']):
                interaction = self._extract_interaction(line)
                if interaction:
                    interactions.append(interaction)
        
        return {
            "participants": participants,
            "interactions": interactions
        }
    
    def _extract_activity_info(self, text: str) -> Dict[str, Any]:
        """提取活动图相关信息"""
        activities = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找活动
            if any(keyword in line.lower() for keyword in ['活动', 'activity', '动作', '任务']):
                activity = self._extract_activity(line)
                if activity:
                    activities.append(activity)
        
        return {
            "activities": activities
        }
    
    def _extract_collaboration_info(self, text: str) -> Dict[str, Any]:
        """提取协作图相关信息"""
        objects = []
        collaborations = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找协作对象
            if any(keyword in line.lower() for keyword in ['对象', 'object', '组件']):
                obj = self._extract_collaboration_object(line)
                if obj:
                    objects.append(obj)
        
        return {
            "collaboration_objects": objects,
            "collaborations": collaborations
        }
    
    def _extract_function_info(self, text: str) -> Dict[str, Any]:
        """提取功能结构图相关信息"""
        functions = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找功能模块
            if any(keyword in line.lower() for keyword in ['功能', 'function', '模块', 'module']):
                function = self._extract_function(line)
                if function:
                    functions.append(function)
        
        return {
            "functions": functions
        }
    
    def _extract_architecture_info(self, text: str) -> Dict[str, Any]:
        """提取系统架构图相关信息"""
        components = []
        layers = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 查找组件
            if any(keyword in line.lower() for keyword in ['组件', 'component', '服务', 'service']):
                component = self._extract_component(line)
                if component:
                    components.append(component)
            
            # 查找架构层次
            elif any(keyword in line.lower() for keyword in ['层', 'layer', '层次']):
                layer = self._extract_layer(line)
                if layer:
                    layers.append(layer)
        
        return {
            "components": components,
            "architecture_layers": layers
        }
    
    # 辅助提取方法
    def _extract_entity_name(self, line: str) -> Optional[str]:
        """从文本行中提取实体名称"""
        # 简单的实体名称提取逻辑
        words = line.split()
        for i, word in enumerate(words):
            if word.lower() in ['实体', 'entity']:
                if i + 1 < len(words):
                    return words[i + 1].strip('：:')
        return None
    
    def _extract_attribute(self, line: str) -> Optional[Dict[str, str]]:
        """提取属性信息"""
        # 简化的属性提取
        return {"name": line.strip(), "type": "string"}
    
    def _extract_relationship(self, line: str) -> Optional[Dict[str, str]]:
        """提取关系信息"""
        return {"type": "association", "description": line.strip()}
    
    def _extract_class_name(self, line: str) -> Optional[str]:
        """提取类名"""
        words = line.split()
        for i, word in enumerate(words):
            if word.lower() in ['类', 'class']:
                if i + 1 < len(words):
                    return words[i + 1].strip('：:')
        return None
    
    def _extract_method(self, line: str) -> Optional[Dict[str, str]]:
        """提取方法信息"""
        return {"name": line.strip(), "return_type": "void", "visibility": "public"}
    
    def _extract_class_attribute(self, line: str) -> Optional[Dict[str, str]]:
        """提取类属性"""
        return {"name": line.strip(), "type": "string", "visibility": "private"}
    
    def _extract_actor(self, line: str) -> Optional[str]:
        """提取参与者"""
        return line.strip()
    
    def _extract_use_case(self, line: str) -> Optional[str]:
        """提取用例"""
        return line.strip()
    
    def _extract_process_step(self, line: str) -> Optional[Dict[str, str]]:
        """提取流程步骤"""
        return {"name": line.strip(), "type": "process"}
    
    def _extract_decision(self, line: str) -> Optional[Dict[str, str]]:
        """提取决策点"""
        return {"name": line.strip(), "type": "decision"}
    
    def _extract_participant(self, line: str) -> Optional[str]:
        """提取参与对象"""
        return line.strip()
    
    def _extract_interaction(self, line: str) -> Optional[Dict[str, str]]:
        """提取交互信息"""
        return {"message": line.strip(), "type": "sync"}
    
    def _extract_activity(self, line: str) -> Optional[str]:
        """提取活动"""
        return line.strip()
    
    def _extract_collaboration_object(self, line: str) -> Optional[str]:
        """提取协作对象"""
        return line.strip()
    
    def _extract_function(self, line: str) -> Optional[Dict[str, str]]:
        """提取功能"""
        return {"name": line.strip(), "level": 1}
    
    def _extract_component(self, line: str) -> Optional[str]:
        """提取组件"""
        return line.strip()
    
    def _extract_layer(self, line: str) -> Optional[str]:
        """提取架构层次"""
        return line.strip()
    
    def _validate_analysis_result(self, result: Dict[str, Any]) -> bool:
        """验证系统分析结果"""
        return validate_system_analysis(result)
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        analysis = self.get_context("system_analysis", {})
        
        summary = {
            "diagram_type": analysis.get("diagram_type", "未知"),
            "entity_count": len(analysis.get("entities", [])),
            "component_count": len(analysis.get("components", [])),
            "process_count": len(analysis.get("processes", [])),
            "actor_count": len(analysis.get("actors", [])),
            "has_relationships": len(analysis.get("relationships", [])) > 0
        }
        
        return summary 