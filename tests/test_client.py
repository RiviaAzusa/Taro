import os
from easylark.client import LarkClient
from easylark.conn import EasyLarkWsServer


async def pipeline():
    pipelines = [
        {"type": "text", "text": "Hello, "},
        {"type": "text", "text": "world!"},
        {"type": "tool_call", "text": "Call: Searching..."},
        {"type": "tool_result", "text": "Result: Hello, world!"},
        {"type": "tool_call", "text": "Call: Processing data..."},
        {"type": "text", "text": "Processing complete."},
        {"type": "tool_result", "text": "Result: Data processed successfully."},
        {"type": "tool_call", "text": "Call: Analyzing results..."},
        {"type": "tool_result", "text": "Result: Analysis complete."},
        {"type": "text", "text": "Final summary: "},
        {"type": "text", "text": "All operations completed successfully."},
        {"type": "tool_call", "text": "Call: Generating report..."},
        {"type": "tool_result", "text": "Result: Report generated."},
        {"type": "text", "text": "Thank you for using our service!"},
        {"type": "tool_call", "text": "Call: Cleanup..."},
        {"type": "tool_result", "text": "Result: Cleanup completed."},
    ]
    for i in pipelines:
        yield i


if __name__ == "__main__":
    client = LarkClient(
        app_id=os.getenv("LARK_APP_ID"),
        app_secret=os.getenv("LARK_APP_SECRET"),
    )

    async def recv_message_callback(
        open_id: str,
        chat_id: str,
        msg_id: str,
        content: str,
        recv_id_type: str,
    ):
        await client.send_card_pipeline(
            pipeline(),
            open_id,
            chat_id,
            recv_id_type=recv_id_type,
        )

    ws_server = EasyLarkWsServer(
        app_id=os.getenv("LARK_APP_ID"),
        app_secret=os.getenv("LARK_APP_SECRET"),
        callback_reply_message=recv_message_callback,
    )
    ws_server.start()
