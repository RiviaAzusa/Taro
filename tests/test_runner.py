from langchain_qwq import ChatQwen
from langchain_deepseek import ChatDeepSeek
from src.runner import LarkRunner
from src.agents.agent import Agent


def test_lark_runner_build():
    runner = LarkRunner(config="dev")
    builder = Agent()
    llm = ChatQwen(model="qwen-plus-latest")
    # llm = ChatDeepSeek(model="deepseek-reasoner")
    builder.build_agent(llm)
    runner.set_agent(builder)
    runner.run()


if __name__ == "__main__":
    test_lark_runner_build()
