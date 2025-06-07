#!/usr/bin/env python3
"""
系统图表绘制代理测试示例
演示如何使用API生成各种类型的图表
"""

import asyncio
import json
from config import DeepSeekConfig
from api.deepseek_client import DeepSeekClient
from agents.main_controller import MainController, ControllerConfig

async def test_diagram_generation():
    """测试图表生成功能"""
    
    # 初始化配置和客户端
    deepseek_config = DeepSeekConfig()
    controller_config = ControllerConfig()
    
    print("🔧 初始化DeepSeek客户端...")
    deepseek_client = DeepSeekClient(deepseek_config)
    
    print("🤖 初始化控制器...")
    controller = MainController(deepseek_client, controller_config)
    
    # 测试用例
    test_cases = [
        {
            "name": "用户登录流程图",
            "request": "为用户登录系统生成流程图，包括用户输入账号密码、验证、登录成功和失败的处理"
        },
        {
            "name": "电商系统架构图", 
            "request": "设计一个电商网站的系统架构图，包括前端、后端API、数据库、缓存、消息队列等组件"
        },
        {
            "name": "数据库ER图",
            "request": "为用户管理系统设计数据库ER图，包括用户表、角色表、权限表及其关系"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 测试用例 {i}: {test_case['name']}")
        print(f"请求: {test_case['request']}")
        print("-" * 60)
        
        try:
            # 处理请求
            session = await controller.process_user_request(
                user_request=test_case['request'],
                user_id=f"test_user_{i}",
                user_preferences={
                    'diagram_complexity': 'medium',
                    'detail_level': 'standard',
                    'quality_threshold': 75,
                    'auto_fix': True
                }
            )
            
            if session.status == "completed":
                print("✅ 生成成功!")
                
                # 显示结果摘要
                if session.final_output:
                    summary = session.final_output.get('summary', {})
                    diagrams = session.final_output.get('diagrams', {})
                    
                    print(f"📈 生成图表数: {summary.get('total_diagrams', 0)}")
                    print(f"⏱️  处理时间: {session.processing_time:.2f}秒")
                    print(f"⭐ 平均质量: {summary.get('average_quality_score', 0):.1f}/100")
                    
                    print("\n生成的图表类型:")
                    for diagram_type in diagrams.keys():
                        quality_info = session.final_output.get('quality_reports', {}).get(diagram_type, {})
                        quality_score = quality_info.get('quality_score', 0)
                        print(f"  • {diagram_type}: {quality_score:.1f}分")
                
                results.append({
                    "test_case": test_case['name'],
                    "status": "success",
                    "session_id": session.session_id,
                    "processing_time": session.processing_time,
                    "output": session.final_output
                })
                
            else:
                print(f"❌ 生成失败: {session.error_message}")
                results.append({
                    "test_case": test_case['name'],
                    "status": "failed",
                    "error": session.error_message
                })
                
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
            results.append({
                "test_case": test_case['name'],
                "status": "error",
                "error": str(e)
            })
    
    # 保存测试结果
    print("\n" + "="*60)
    print("📋 测试结果摘要")
    print("="*60)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    total_count = len(results)
    
    print(f"总测试数: {total_count}")
    print(f"成功数: {success_count}")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    
    # 保存详细结果到JSON文件
    with open('test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细结果已保存到: test_results.json")
    
    return results

async def test_health_check():
    """测试系统健康检查"""
    print("\n🏥 执行系统健康检查...")
    
    try:
        deepseek_config = DeepSeekConfig()
        controller_config = ControllerConfig()
        deepseek_client = DeepSeekClient(deepseek_config)
        controller = MainController(deepseek_client, controller_config)
        
        health_status = await controller.health_check()
        
        print("系统健康状态:")
        print(f"  控制器: {health_status['controller_status']}")
        print(f"  API连接: {health_status['api_status']}")
        print(f"  活跃会话: {health_status['active_sessions']}")
        print(f"  最大并发: {health_status['max_concurrent_sessions']}")
        
        print("\n各代理状态:")
        for agent, status in health_status['agents_status'].items():
            print(f"  {agent}: {status}")
        
        if health_status['api_status'] == 'healthy':
            print("\n✅ 系统运行正常")
            return True
        else:
            print("\n❌ 系统存在问题")
            return False
            
    except Exception as e:
        print(f"❌ 健康检查失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始系统图表绘制代理测试")
    print("="*60)
    
    # 健康检查
    health_ok = await test_health_check()
    
    if not health_ok:
        print("⚠️  系统健康检查未通过，跳过功能测试")
        return
    
    # 功能测试
    await test_diagram_generation()
    
    print("\n🎉 测试完成!")

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容）
    if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试执行失败: {str(e)}") 