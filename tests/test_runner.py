from langchain_qwq import ChatQwen
from langchain_deepseek import ChatDeepSeek
from src.runner import LarkRunner
from src.agents.agent import Agent


def test_lark_runner_build():
    runner = LarkRunner(config="dev")
    builder = Agent()
    qwen = ChatQwen(model="qwen-plus-latest")
    # deepseek_r1 = ChatDeepSeek(model="deepseek-reasoner")
    builder.build_agent(qwen)
    runner.set_agent(builder)
    runner.run()


if __name__ == "__main__":
    test_lark_runner_build()
