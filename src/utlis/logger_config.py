import sys
from pathlib import Path
from datetime import datetime
from loguru import logger


# 使用全局变量来标记是否已经初始化，避免重复初始化
_logger_initialized = False


def _initialize_logger():
    """初始化日志配置，只在第一次调用时执行"""
    global _logger_initialized

    if _logger_initialized:
        return

    # --- 1. 移除默认的控制台输出 ---
    # Loguru 默认会添加一个输出到 sys.stderr 的 handler，为了完全自定义，我们先移除它。
    logger.remove()

    # --- 2. 添加一个新的控制台输出 (满足需求3：代替print) ---
    # level="INFO": 表示只有 INFO 及更高级别的日志（INFO, SUCCESS, WARNING, ERROR, CRITICAL）才会在这里输出。
    # colorize=True: 开启颜色高亮。
    logger.add(
        sys.stdout,
        level="INFO",
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # --- 3. 添加一个文件输出 (满足需求1：创建带时间的日志文件) ---
    # 确保 work_dirs 目录存在
    log_dir = Path("work_dirs")
    log_dir.mkdir(exist_ok=True)

    # 使用当前时间创建日志文件名
    log_file_name = f"{datetime.now().strftime('%Y-%m-%d')}.log"
    log_file_path = log_dir / log_file_name

    # level="DEBUG": 表示所有级别的日志（DEBUG, INFO, ...）都会被写入文件。
    # rotation, retention, compression 是管理日志文件的强大功能，后面会讲。
    # encoding="utf-8": 确保能正确处理中文字符。
    logger.add(
        log_file_path,
        level="DEBUG",
        format="{time} | {level} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
    )

    # 标记已完成初始化
    _logger_initialized = True

    # 现在，这个配置好的 logger 就可以被其他文件导入使用了
    logger.info("Logger configuration loaded.")


# 在模块被导入时自动初始化
_initialize_logger()
