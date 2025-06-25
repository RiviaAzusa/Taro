from langchain_qwq import ChatQwen
from langchain_deepseek import ChatDeepSeek
from src.runner import LarkRunner
from src.agents.agent import Agent
from src.utlis.logger_config import logger


def main():
    runner = LarkRunner(config="dev")
    builder = Agent()
    llm = ChatQwen(model="qwen-plus-latest")
    # llm = ChatDeepSeek(model="deepseek-reasoner")
    builder.build_agent(llm)
    runner.set_agent(builder)
    logger.info("Start to Run Taro")
    runner.run()


if __name__ == "__main__":
    main()
