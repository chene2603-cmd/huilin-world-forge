import os
import logging
import logging.handlers
from datetime import datetime

LOG_ROOT = "system_logs"
os.makedirs(LOG_ROOT, exist_ok=True)

LOG_TYPE = [
    "core_protocol",
    "terrain_blue",
    "render_engine",
    "sound_gen",
    "world_build",
    "scanner_check",
    "system_error"
]

LOG_INSTANCE = {}

def create_logger(log_name):
    if log_name in LOG_INSTANCE:
        return LOG_INSTANCE[log_name]

    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    log_path = os.path.join(LOG_ROOT, f"{log_name}.log")
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_path, when="midnight", interval=1, backupCount=30, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%Y-%m-%d %H:%M:%S | %(levelname)s | %(filename)s | %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    LOG_INSTANCE[log_name] = logger
    return logger

# 全局初始化
def log_init():
    create_logger("system_error").info("慧凌世界系统 日志模块启动完成")