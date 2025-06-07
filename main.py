"""
系统图表绘制代理主入口点
支持命令行模式和Web服务模式
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

from config import DeepSeekConfig, AppConfig
from api.deepseek_client import DeepSeekClient
from agents.main_controller import MainController, ControllerConfig
from utils.logger import get_logger

logger = get_logger(__name__)

async def run_cli_mode(user_request: str, output_file: str = None):
    """命令行模式"""
    try:
        # 初始化配置
        deepseek_config = DeepSeekConfig()
        app_config = AppConfig()
        controller_config = ControllerConfig()
        
        # 初始化客户端和控制器
        deepseek_client = DeepSeekClient(deepseek_config)
        controller = MainController(deepseek_client, controller_config)
        
        logger.info("开始处理用户请求...")
        logger.info(f"用户输入: {user_request}")
        
        # 处理请求
        session = await controller.process_user_request(user_request)
        
        if session.status == "completed":
            logger.info("✅ 处理完成!")
            
            # 输出结果
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(session.final_output, f, ensure_ascii=False, indent=2)
                
                logger.info(f"结果已保存到: {output_file}")
            else:
                # 控制台输出
                print("\n" + "="*50)
                print("📊 生成的图表:")
                print("="*50)
                
                if session.final_output and session.final_output.get('diagrams'):
                    for diagram_type, diagram_info in session.final_output['diagrams'].items():
                        print(f"\n🔹 {diagram_type}:")
                        print(f"描述: {diagram_info['description']}")
                        print(f"复杂度: {diagram_info['complexity_level']}")
                        print(f"元素数量: {diagram_info['estimated_elements']}")
                        print(f"状态: {'✅ 有效' if diagram_info['is_valid'] else '❌ 无效'}")
                        print(f"\nMermaid代码:")
                        print("```mermaid")
                        print(diagram_info['diagram_code'])
                        print("```")
                        
                        # 质量报告
                        if session.final_output.get('quality_reports', {}).get(diagram_type):
                            quality = session.final_output['quality_reports'][diagram_type]
                            print(f"\n📋 质量报告:")
                            print(f"总体质量: {quality['overall_quality']}")
                            print(f"质量分数: {quality['quality_score']:.1f}/100")
                            if quality['improvement_suggestions']:
                                print(f"改进建议: {', '.join(quality['improvement_suggestions'][:3])}")
                        
                        print("-" * 40)
                
                # 显示摘要
                if session.final_output and session.final_output.get('summary'):
                    summary = session.final_output['summary']
                    print(f"\n📈 处理摘要:")
                    print(f"总图表数: {summary['total_diagrams']}")
                    print(f"成功生成: {summary['successful_diagrams']}")
                    print(f"平均质量: {summary['average_quality_score']:.1f}/100")
                    print(f"处理时间: {session.processing_time:.2f}秒")
        else:
            logger.error(f"❌ 处理失败: {session.error_message}")
            return 1
            
    except Exception as e:
        logger.error(f"命令行模式执行失败: {str(e)}")
        return 1
    
    return 0

def run_web_mode(host: str = "localhost", port: int = 5000, debug: bool = False):
    """Web服务模式"""
    try:
        from web.app import create_app
        
        app = create_app()
        logger.info(f"🌐 启动Web服务: http://{host}:{port}")
        app.run(host=host, port=port, debug=debug)
        
    except ImportError:
        logger.error("Web模式需要安装Flask相关依赖")
        return 1
    except Exception as e:
        logger.error(f"Web服务启动失败: {str(e)}")
        return 1
    
    return 0

async def run_interactive_mode():
    """交互模式"""
    try:
        # 初始化
        deepseek_config = DeepSeekConfig()
        controller_config = ControllerConfig()
        deepseek_client = DeepSeekClient(deepseek_config)
        controller = MainController(deepseek_client, controller_config)
        
        print("🤖 系统图表绘制代理 - 交互模式")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'help' 查看帮助信息")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n💬 请描述您的系统或需求: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见!")
                    break
                elif user_input.lower() in ['help', 'h']:
                    print("""
📖 帮助信息:
- 描述您想要图表化的系统、流程或架构
- 例如: "用户登录系统的流程图"
- 例如: "电商网站的系统架构图" 
- 例如: "数据库设计的ER图"
- 支持的图表类型: 流程图、架构图、时序图、类图等
                    """)
                    continue
                elif not user_input:
                    continue
                
                print("\n🔄 正在处理...")
                session = await controller.process_user_request(user_input)
                
                if session.status == "completed":
                    print("✅ 处理完成!")
                    
                    # 显示结果摘要
                    if session.final_output:
                        summary = session.final_output.get('summary', {})
                        diagrams = session.final_output.get('diagrams', {})
                        
                        print(f"\n📊 生成了 {summary.get('total_diagrams', 0)} 个图表:")
                        for diagram_type in diagrams.keys():
                            quality_info = session.final_output.get('quality_reports', {}).get(diagram_type, {})
                            quality_score = quality_info.get('quality_score', 0)
                            print(f"  • {diagram_type}: 质量分数 {quality_score:.1f}/100")
                        
                        # 询问是否查看详细内容
                        show_detail = input("\n🔍 是否查看详细的图表代码? (y/n): ").lower().strip()
                        if show_detail in ['y', 'yes']:
                            for diagram_type, diagram_info in diagrams.items():
                                print(f"\n📋 {diagram_type}:")
                                print("```mermaid")
                                print(diagram_info['diagram_code'])
                                print("```")
                        
                        print(f"\n⏱️  处理时间: {session.processing_time:.2f}秒")
                else:
                    print(f"❌ 处理失败: {session.error_message}")
                    
            except KeyboardInterrupt:
                print("\n\n👋 程序已中断，再见!")
                break
            except Exception as e:
                print(f"❌ 处理过程中出现错误: {str(e)}")
                
    except Exception as e:
        logger.error(f"交互模式执行失败: {str(e)}")
        return 1
    
    return 0

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="系统图表绘制代理 - 基于DeepSeek API的智能图表生成工具"
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='运行模式')
    
    # CLI模式
    cli_parser = subparsers.add_parser('cli', help='命令行模式')
    cli_parser.add_argument('request', help='用户请求描述')
    cli_parser.add_argument('-o', '--output', help='输出文件路径')
    
    # Web模式
    web_parser = subparsers.add_parser('web', help='Web服务模式')
    web_parser.add_argument('--host', default='localhost', help='服务器地址')
    web_parser.add_argument('--port', type=int, default=5000, help='端口号')
    web_parser.add_argument('--debug', action='store_true', help='调试模式')
    
    # 交互模式
    interactive_parser = subparsers.add_parser('interactive', help='交互模式')
    
    # 健康检查
    health_parser = subparsers.add_parser('health', help='健康检查')
    
    args = parser.parse_args()
    
    if not args.mode:
        # 默认交互模式
        return asyncio.run(run_interactive_mode())
    
    if args.mode == 'cli':
        return asyncio.run(run_cli_mode(args.request, args.output))
    elif args.mode == 'web':
        return run_web_mode(args.host, args.port, args.debug)
    elif args.mode == 'interactive':
        return asyncio.run(run_interactive_mode())
    elif args.mode == 'health':
        return asyncio.run(health_check())
    else:
        parser.print_help()
        return 1

async def health_check():
    """健康检查"""
    try:
        deepseek_config = DeepSeekConfig()
        controller_config = ControllerConfig()
        deepseek_client = DeepSeekClient(deepseek_config)
        controller = MainController(deepseek_client, controller_config)
        
        health_status = await controller.health_check()
        
        print("🏥 系统健康检查:")
        print(f"控制器状态: {health_status['controller_status']}")
        print(f"API状态: {health_status['api_status']}")
        print(f"活跃会话: {health_status['active_sessions']}")
        print(f"最大并发: {health_status['max_concurrent_sessions']}")
        
        print("\n各代理状态:")
        for agent, status in health_status['agents_status'].items():
            print(f"  {agent}: {status}")
        
        if health_status['api_status'] == 'healthy':
            print("\n✅ 系统运行正常")
            return 0
        else:
            print("\n❌ 系统存在问题")
            return 1
            
    except Exception as e:
        print(f"❌ 健康检查失败: {str(e)}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n程序已中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1) 