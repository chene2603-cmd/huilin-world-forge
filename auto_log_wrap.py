from functools import wraps
from system_logger import create_logger

def func_log():
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            name = func.__name__
            log = create_logger("system_error")
            log.info(f"执行函数：{name}")
            try:
                res = func(*args, **kwargs)
                log.info(f"函数 {name} 执行成功")
                return res
            except Exception as e:
                log.error(f"函数 {name} 异常：{str(e)}")
                raise
        return inner
    return outer