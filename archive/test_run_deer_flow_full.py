import os
import re
import sys

sys.path.insert(0, "deer_flow/")

import json
import logging
import asyncio
from pydantic import BaseModel

from easylark.conn.larkapi import EasyLarkAPI
from easylark.client.lark_client import LarkClient
from easylark.conn.larkws import EasyLarkWsServer

from deer_flow.src.graph import build_graph
from deer_flow.src.prompts.planner_model import Plan

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()
client = LarkClient(
    app_id=os.getenv("LARK_APP_ID"), app_secret=os.getenv("LARK_APP_SECRET")
)


async def run_agent_workflow_async(
    user_input: str,
    debug: bool = False,
    max_plan_iterations: int = 1,
    max_step_num: int = 3,
    enable_background_investigation: bool = True,
):
    """Run the agent workflow asynchronously with the given user input.

    Args:
        user_input: The user's query or request
        debug: If True, enables debug level logging
        max_plan_iterations: Maximum number of plan iterations
        max_step_num: Maximum number of steps in a plan
        enable_background_investigation: If True, performs web search before planning to enhance context

    Returns:
        The final state after the workflow completes
    """
    if not user_input:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"Starting async workflow with user input: {user_input}")
    initial_state = {
        # Runtime Variables
        "messages": [{"role": "user", "content": user_input}],
        "auto_accepted_plan": True,
        "enable_background_investigation": enable_background_investigation,
    }
    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
        },
        "recursion_limit": 100,
    }
    current_message_len = 0
    print_status = {"plans": False, "final_report": False}
    final_report = None  # 存储最终报告

    async for s in graph.astream(
        input=initial_state, config=config, stream_mode="values"
    ):
        try:
            if isinstance(s, dict):
                if (
                    "current_plan" in s
                    and isinstance(s["current_plan"], BaseModel)
                    and not print_status["plans"]
                ):
                    yield {"type": "tool_call", "text": "当前计划:"}
                    for step in s["current_plan"].steps:
                        yield {
                            "type": "tool_result",
                            "text": f"**{step.title}**: {step.description}\n\n",
                        }
                    print_status["plans"] = True
                if "final_report" in s and not print_status["final_report"]:
                    final_report = s["final_report"]  # 保存最终报告
                    yield {"type": "tool_call", "text": "最终报告:"}
                    yield {"type": "text", "text": final_report}
                    print_status["final_report"] = True

                if "messages" in s:
                    if len(s["messages"]) <= current_message_len:
                        continue
                    current_message_len = len(s["messages"])
                    message = s["messages"][-1]
                    if message.name != "planner":
                        tool_call_name = (
                            "Taro Say:" if message.name is None else message.name
                        )
                        yield {"type": "tool_call", "text": tool_call_name}
                        # Parse message content to extract images and clean text
                        content = message.content
                        images = []

                        # Extract image links in ![alt](url) format
                        image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
                        matches = re.findall(image_pattern, content)

                        for alt_text, url in matches:
                            images.append((alt_text, url))

                        # Remove image markdown from content
                        cleaned_content = re.sub(image_pattern, "", content)

                        yield {"type": "text", "text": cleaned_content}

                        # Yield images separately if any found
                        # if images:
                        #     yield {"type": "tool_call", "text": "相关图片:"}
                        #     for image_name, image_url in images:
                        #         yield {"type": "tool_result", "text": f"图片: {image_name}\n链接: {image_url}\n"}
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")
            print(f"Error processing output: {str(e)}")

    logger.info("Async workflow completed successfully")

    # 最后返回最终报告


async def recv_message_callback(open_id, chat_id, msg_id, content, recv_id_type):
    logger.info(
        f"recv_message_callback: {open_id}, {chat_id}, {msg_id}, {content}, {recv_id_type}"
    )
    pipeline = run_agent_workflow_async(
        user_input=content,
        debug=True,
        max_plan_iterations=3,
        max_step_num=20,
        enable_background_investigation=False,
    )
    await client.send_card_pipeline(
        pipeline=pipeline,
        open_id=open_id,
        chat_id=chat_id,
        recv_id_type=recv_id_type,
    )
    # After run workflow, create a final output to a doc and save to local.


def run_lark_client():
    ws = EasyLarkWsServer(
        app_id=os.getenv("LARK_APP_ID"),
        app_secret=os.getenv("LARK_APP_SECRET"),
        callback_reply_message=recv_message_callback,
    )
    ws.start()


# async def main():
#     api = EasyLarkAPI(
#         app_id=os.getenv("LARK_APP_ID"), app_secret=os.getenv("LARK_APP_SECRET")
#     )
#     larkSynchronizer = LarkSynchronizer(api, None)

#     items = await larkSynchronizer.fetch_all_wiki_nodes(space_id="7511700730315653148", page_size=20)
#     from pprint import pprint
#     pprint(items)


async def run_deerflow():
    async for chunk in run_agent_workflow_async(
        user_input="武汉天气如何？ (仅从温度，湿度角度回答即可，不需要创建太长的计划。这是一个测试)",
        debug=True,
        max_plan_iterations=3,
        max_step_num=20,
        enable_background_investigation=False,
    ):
        print(f"{chunk['type'], chunk['text']}")


if __name__ == "__main__":
    # Run DeerFlow in Lark.
    # asyncio.run(run_deerflow())
    run_lark_client()
    # asyncio.run(main())
