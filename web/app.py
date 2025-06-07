"""
Flask Web应用
提供系统图表绘制代理的Web界面
"""

import asyncio
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS

from config import DeepSeekConfig
from api.deepseek_client import DeepSeekClient
from agents.main_controller import MainController, ControllerConfig
from utils.logger import get_logger

logger = get_logger(__name__)

# 全局控制器实例
controller = None

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    app.secret_key = 'your-secret-key-change-this-in-production'
    
    # 启用CORS
    CORS(app)
    
    # 初始化控制器
    global controller
    try:
        deepseek_config = DeepSeekConfig()
        controller_config = ControllerConfig()
        deepseek_client = DeepSeekClient(deepseek_config)
        controller = MainController(deepseek_client, controller_config)
        logger.info("Web应用控制器初始化完成")
    except Exception as e:
        logger.error(f"控制器初始化失败: {str(e)}")
        controller = None
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')
    
    @app.route('/api/generate', methods=['POST'])
    def generate_diagrams():
        """生成图表API"""
        try:
            if not controller:
                return jsonify({
                    'success': False,
                    'error': '系统未正确初始化，请检查配置'
                }), 500
            
            data = request.get_json()
            user_request = data.get('request', '').strip()
            
            if not user_request:
                return jsonify({
                    'success': False,
                    'error': '请提供有效的请求描述'
                }), 400
            
            # 获取或创建用户会话
            user_id = session.get('user_id')
            if not user_id:
                user_id = f"user_{uuid.uuid4().hex[:8]}"
                session['user_id'] = user_id
            
            # 异步处理请求
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                processing_session = loop.run_until_complete(
                    controller.process_user_request(
                        user_request=user_request,
                        user_id=user_id,
                        user_preferences=data.get('preferences', {}),
                        interaction_history=session.get('interaction_history', [])
                    )
                )
            finally:
                loop.close()
            
            # 更新会话历史
            if 'interaction_history' not in session:
                session['interaction_history'] = []
            
            session['interaction_history'].append({
                'request': user_request,
                'timestamp': datetime.now().isoformat(),
                'session_id': processing_session.session_id,
                'status': processing_session.status
            })
            
            if processing_session.status == 'completed':
                return jsonify({
                    'success': True,
                    'session_id': processing_session.session_id,
                    'data': processing_session.final_output,
                    'processing_time': processing_session.processing_time
                })
            else:
                return jsonify({
                    'success': False,
                    'error': processing_session.error_message,
                    'session_id': processing_session.session_id
                }), 500
                
        except Exception as e:
            logger.error(f"图表生成失败: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'处理过程中出现错误: {str(e)}'
            }), 500
    
    @app.route('/api/session/<session_id>/status', methods=['GET'])
    def get_session_status(session_id):
        """获取会话状态"""
        try:
            if not controller:
                return jsonify({'error': '系统未正确初始化'}), 500
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                status = loop.run_until_complete(
                    controller.get_session_status(session_id)
                )
            finally:
                loop.close()
            
            if status:
                return jsonify(status)
            else:
                return jsonify({'error': '会话不存在'}), 404
                
        except Exception as e:
            logger.error(f"获取会话状态失败: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/session/<session_id>/cancel', methods=['POST'])
    def cancel_session(session_id):
        """取消会话"""
        try:
            if not controller:
                return jsonify({'error': '系统未正确初始化'}), 500
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    controller.cancel_session(session_id)
                )
            finally:
                loop.close()
            
            if success:
                return jsonify({'success': True, 'message': '会话已取消'})
            else:
                return jsonify({'success': False, 'error': '会话取消失败'}), 400
                
        except Exception as e:
            logger.error(f"取消会话失败: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """健康检查API"""
        try:
            if not controller:
                return jsonify({
                    'status': 'unhealthy',
                    'error': '控制器未初始化'
                }), 500
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                health_status = loop.run_until_complete(controller.health_check())
            finally:
                loop.close()
            
            return jsonify(health_status)
            
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500
    
    @app.route('/api/statistics', methods=['GET'])
    def get_statistics():
        """获取系统统计信息"""
        try:
            if not controller:
                return jsonify({'error': '系统未正确初始化'}), 500
            
            stats = controller.get_system_statistics()
            return jsonify(stats)
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {str(e)}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/user/preferences', methods=['GET', 'POST'])
    def user_preferences():
        """用户偏好设置"""
        if request.method == 'GET':
            # 获取用户偏好
            prefs = session.get('user_preferences', {
                'diagram_complexity': 'medium',
                'detail_level': 'standard',
                'interaction_style': 'guided',
                'quality_threshold': 75,
                'auto_fix': True
            })
            return jsonify(prefs)
        
        elif request.method == 'POST':
            # 设置用户偏好
            try:
                data = request.get_json()
                session['user_preferences'] = data
                return jsonify({'success': True, 'message': '偏好设置已保存'})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 400
    
    @app.route('/api/examples', methods=['GET'])
    def get_examples():
        """获取示例请求"""
        examples = [
            {
                'title': '用户登录流程图',
                'description': '生成用户登录系统的流程图',
                'request': '请为用户登录系统生成一个流程图，包括用户输入账号密码、验证、登录成功和失败的处理'
            },
            {
                'title': '电商系统架构图',
                'description': '电商网站的系统架构设计',
                'request': '设计一个电商网站的系统架构图，包括前端、后端API、数据库、缓存、消息队列等组件'
            },
            {
                'title': '数据库ER图',
                'description': '用户管理系统的数据库设计',
                'request': '为用户管理系统设计数据库ER图，包括用户表、角色表、权限表及其关系'
            },
            {
                'title': '订单处理时序图',
                'description': '电商订单处理的时序图',
                'request': '生成电商系统中订单处理的时序图，包括用户下单、库存检查、支付、发货等步骤'
            },
            {
                'title': 'API系统类图',
                'description': 'RESTful API系统的类图设计',
                'request': '设计RESTful API系统的UML类图，包括控制器、服务、数据访问对象等类的关系'
            }
        ]
        return jsonify(examples)
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': '页面不存在'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': '服务器内部错误'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) 