import pytest
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_qwq import ChatQwen
from src.runner import TaroLarkRunner


def test_lark_runner_build():
    runner = TaroLarkRunner(config="dev")
    agent = runner.build_agent(ChatQwen(model="qwen-plus-latest"))
    runner.run()


# def test_lark_runner_init():
#     """测试TaroLarkRunner的初始化"""
#     runner = TaroLarkRunner(config="dev")

#     # 验证基本属性
#     assert runner.config is not None
#     assert runner.lark_api is not None
#     assert runner.db_api is not None
#     assert runner.larkSynchronizer is not None
#     assert runner.rag_manager is not None
#     assert runner.lark_client is not None


# @pytest.mark.asyncio
# async def test_lark_runner_callback():
#     """测试回调函数"""
#     from src.agents.agent import RuntimeConfig

#     runner = TaroLarkRunner(config="dev")

#     # 先设置runtime_config
#     test_key = ("test_open_id", "test_chat_id")
#     runner.runtime_configs[test_key] = RuntimeConfig()

#     # 测试卡片动作回调
#     result = await runner.callback_card_action(
#         open_id="test_open_id", chat_id="test_chat_id", actions={"name": "stop"}
#     )

#     assert result is not None
#     assert "toast" in result
#     assert runner.runtime_configs[test_key].take_interupt is True


# if __name__ == "__main__":
#     test_lark_runner_init()
#     test_lark_runner_build()
#     print("All tests passed!")

if __name__ == "__main__":
    test_lark_runner_build()
