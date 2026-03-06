from enum import Enum


class ModelStatus(Enum):
    """模型状态枚举"""
    UNINITIALIZED = "uninitialized"  # 未初始化
    LOADING = "loading"              # 加载中
    READY = "ready"                  # 就绪
    ERROR = "error"                  # 错误
    UNLOADED = "unloaded"            # 已卸载