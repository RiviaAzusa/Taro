#!/usr/bin/env python3
"""
Taro Lark Runner 使用示例
"""

import os
from src.runner import TaroLarkRunner

# 设置环境变量（实际使用时应该从环境变量或配置文件读取）
# os.environ["LARK_APP_ID"] = "your_app_id"
# os.environ["LARK_APP_SECRET"] = "your_app_secret"


def create_mock_model():
    """创建一个模拟的LLM模型，实际使用时替换为真实的模型"""
    # 这里应该是实际的LLM模型，例如：
    # from langchain_anthropic import ChatAnthropic
    # return ChatAnthropic(model="claude-3-haiku-20240307")

    # 模拟模型类
    class MockModel:
        def invoke(self, messages):
            return "这是一个模拟响应"

        def stream(self, messages):
            yield "模拟"
            yield "流式"
            yield "响应"

    return MockModel()


def main():
    """主函数"""
    # 初始化 TaroLarkRunner
    runner = TaroLarkRunner(config="dev")

    # 创建LLM模型
    model = create_mock_model()

    # 构建 agent
    agent = runner.build_agent(model)
    print(f"Agent 已构建: {type(agent)}")

    # 启动飞书WebSocket服务器
    print("启动飞书WebSocket服务器...")
    try:
        runner.run()
    except KeyboardInterrupt:
        print("服务器已停止")
    except Exception as e:
        print(f"启动失败: {e}")
        print("请确保已设置正确的 LARK_APP_ID 和 LARK_APP_SECRET 环境变量")


if __name__ == "__main__":
    main()
