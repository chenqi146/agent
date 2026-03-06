import logging
import functools
from typing import Optional, Dict
from enum import Enum
import yaml
import os

# ANSI颜色代码
class Colors:
    """ANSI颜色代码"""
    RED = '\033[31m'      # 红色
    ORANGE = '\033[33m'   # 橘黄色/黄色
    YELLOW = '\033[33m'   # 黄色
    GREEN = '\033[32m'    # 绿色
    BLUE = '\033[34m'     # 蓝色
    PURPLE = '\033[35m'   # 紫色
    CYAN = '\033[36m'     # 青色
    WHITE = '\033[37m'    # 白色
    BOLD = '\033[1m'      # 粗体
    UNDERLINE = '\033[4m' # 下划线
    END = '\033[0m'       # 结束颜色
    
    # 自定义RGB颜色
    CUSTOM_PINK = '\033[38;2;238;122;233m'  # 粉紫色 (RGB=238,122,233)
    CUSTOM_DEBUG = '\033[38;2;255;125;64m'  # 橙红色 (RGB=255,125,64)
    CUSTOM_INFO = '\033[38;2;0;255;0m'      # 亮绿色 (RGB=0,255,0)
    CUSTOM_MODULE = '\033[38;2;255;153;18m' # 橙黄色 (RGB=255,153,18)


class LogLevel(Enum):
    """日志级别枚举"""
    TRACE = 0
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    # 定义不同日志级别的颜色
    COLORS = {
        'TRACE': Colors.CYAN,
        'DEBUG': Colors.CUSTOM_DEBUG,    # debug显示橙红色 (RGB=255,125,64)
        'INFO': Colors.CUSTOM_INFO,      # info显示亮绿色 (RGB=0,255,0)
        'WARNING': Colors.ORANGE,        # warning显示橘黄色
        'WARN': Colors.ORANGE,           # warn显示橘黄色
        'ERROR': Colors.RED,             # error显示红色
        'CRITICAL': Colors.RED + Colors.BOLD,
        'FATAL': Colors.RED + Colors.BOLD,
    }
    
    def format(self, record):
        # 获取原始格式化的消息
        message = super().format(record)
        
        # 获取日志级别名称和模块名称
        level_name = record.levelname
        module_name = record.name
        
        # 为时间戳添加自定义粉紫色 (RGB=238,122,233)
        if hasattr(record, 'asctime') and record.asctime:
            colored_time = f"{Colors.CUSTOM_PINK}{record.asctime}{Colors.END}"
            message = message.replace(record.asctime, colored_time)
        
        # 为模块名称添加橙黄色 (RGB=255,153,18)
        if module_name:
            colored_module = f"{Colors.CUSTOM_MODULE}{module_name}{Colors.END}"
            message = message.replace(module_name, colored_module)
        
        # 为日志级别添加颜色
        if level_name in self.COLORS:
            color = self.COLORS[level_name]
            # 只对日志级别名称着色，保持消息内容不变
            colored_level = f"{color}{level_name}{Colors.END}"
            message = message.replace(level_name, colored_level)
        
        return message


class LoggerConfig:
    """日志配置类"""
    
    def __init__(self):
        self.level = LogLevel.INFO
        self.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self.handlers = []
        self.propagate = False
    
    def add_handler(self, handler):
        self.handlers.append(handler)
    
    def set_level(self, level: LogLevel):
        self.level = level
    
    def set_format(self, format_str: str):
        self.format = format_str


class SLF4JLogger:
    """SLF4J风格的Python日志器"""
    
    def __init__(self, name: str, config: Optional[LoggerConfig] = None):
        self.name = name
        self.config = config or LoggerConfig()
        self._logger = self._create_logger()
    
    def _create_logger(self) -> logging.Logger:
        logger = logging.getLogger(self.name)
        logger.setLevel(self.config.level.value)
        
        logger.handlers.clear()
        
        if self.config.handlers:
            for handler in self.config.handlers:
                logger.addHandler(handler)
        else:
            handler = logging.StreamHandler()
            # 使用带颜色的格式化器
            formatter = ColoredFormatter(self.config.format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        logger.propagate = self.config.propagate
        return logger
    
    def trace(self, message: str, *args, **kwargs):
        if self._logger.isEnabledFor(LogLevel.TRACE.value):
            self._logger.log(LogLevel.TRACE.value, message, *args, **kwargs)
    
    def debug(self, message: str, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)
    
    def warn(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)
    
    def fatal(self, message: str, *args, **kwargs):
        self._logger.critical(message, *args, **kwargs)
    
    def is_trace_enabled(self) -> bool:
        return self._logger.isEnabledFor(LogLevel.TRACE.value)
    
    def is_debug_enabled(self) -> bool:
        return self._logger.isEnabledFor(LogLevel.DEBUG.value)
    
    def is_info_enabled(self) -> bool:
        return self._logger.isEnabledFor(LogLevel.INFO.value)
    
    def is_warn_enabled(self) -> bool:
        return self._logger.isEnabledFor(LogLevel.WARN.value)
    
    def is_error_enabled(self) -> bool:
        return self._logger.isEnabledFor(LogLevel.ERROR.value)
    
    def is_fatal_enabled(self) -> bool:
        return self._logger.isEnabledFor(LogLevel.FATAL.value)


class LoggerFactory:
    """日志器工厂类"""
    
    _loggers: Dict[str, SLF4JLogger] = {}
    _default_config = LoggerConfig()
    
    @classmethod
    def get_logger(cls, name: str) -> SLF4JLogger:
        if name not in cls._loggers:
            cls._loggers[name] = SLF4JLogger(name, cls._default_config)
        return cls._loggers[name]
    
    @classmethod
    def get_logger_by_class(cls, clazz: type) -> SLF4JLogger:
        return cls.get_logger(clazz.__name__)
    
    @classmethod
    def set_default_config(cls, config: LoggerConfig):
        cls._default_config = config
        for name in list(cls._loggers.keys()):
            cls._loggers[name] = SLF4JLogger(name, config)


def logger(name: Optional[str] = None):
    """
    装饰器：为类添加日志器
    
    用法:
    @logger()
    class MyClass:
        def my_method(self):
            self.log.info("这是一条日志")
    """
    def decorator(cls):
        logger_name = name or cls.__name__
        
        # 保存原始的__init__方法
        original_init = cls.__init__
        
        def new_init(self, *args, **kwargs):
            # 先设置logger属性
            self.log = LoggerFactory.get_logger(logger_name)
            # 然后调用原始__init__方法
            original_init(self, *args, **kwargs)
        
        # 替换__init__方法
        cls.__init__ = new_init
        
        def get_logger(self):
            return getattr(self, 'log', LoggerFactory.get_logger(logger_name))
        
        setattr(cls, 'get_logger', get_logger)
        return cls
    
    return decorator


def method_logger(level: LogLevel = LogLevel.INFO):
    """
    方法级日志装饰器
    
    用法:
    @method_logger(LogLevel.INFO)
    def my_method(self):
        return "some result"
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if args and hasattr(args[0], 'log'):
                log = args[0].log
                class_name = args[0].__class__.__name__
                method_name = func.__name__
                
                if level == LogLevel.TRACE:
                    log.trace(f"进入方法: {class_name}.{method_name}")
                elif level == LogLevel.DEBUG:
                    log.debug(f"进入方法: {class_name}.{method_name}")
                elif level == LogLevel.INFO:
                    log.info(f"进入方法: {class_name}.{method_name}")
                elif level == LogLevel.WARN:
                    log.warn(f"进入方法: {class_name}.{method_name}")
                elif level == LogLevel.ERROR:
                    log.error(f"进入方法: {class_name}.{method_name}")
                elif level == LogLevel.FATAL:
                    log.fatal(f"进入方法: {class_name}.{method_name}")
                
                try:
                    result = func(*args, **kwargs)
                    
                    if level == LogLevel.TRACE:
                        log.trace(f"退出方法: {class_name}.{method_name}")
                    elif level == LogLevel.DEBUG:
                        log.debug(f"退出方法: {class_name}.{method_name}")
                    elif level == LogLevel.INFO:
                        log.info(f"退出方法: {class_name}.{method_name}")
                    elif level == LogLevel.WARN:
                        log.warn(f"退出方法: {class_name}.{method_name}")
                    elif level == LogLevel.ERROR:
                        log.error(f"退出方法: {class_name}.{method_name}")
                    elif level == LogLevel.FATAL:
                        log.fatal(f"退出方法: {class_name}.{method_name}")
                    
                    return result
                except Exception as e:
                    log.error(f"方法 {class_name}.{method_name} 发生异常: {str(e)}")
                    raise
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# 便捷函数
def get_logger(name: str) -> SLF4JLogger:
    return LoggerFactory.get_logger(name)


def get_logger_by_class(clazz: type) -> SLF4JLogger:
    return LoggerFactory.get_logger_by_class(clazz)


def set_default_config(config: LoggerConfig):
    LoggerFactory.set_default_config(config)


def create_console_config(level: LogLevel = LogLevel.INFO, 
                         format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s") -> LoggerConfig:
    config = LoggerConfig()
    config.set_level(level)
    config.set_format(format_str)
    return config 


def init_logging(config: dict):
    """
    从字典配置初始化LoggerFactory。
    支持字段：
    - level: 日志等级 (TRACE/DEBUG/INFO/WARN/ERROR/FATAL)
    - format: 日志格式
    - log_dir: 日志保存路径
    - filename: 日志文件名称
    - max_days: 日志保存时间（天）
    - handlers: 处理器配置 (console/file)
    """
    # 解析日志等级
    level_str = config.get('level', 'INFO').upper()
    level = LogLevel[level_str] if level_str in LogLevel.__members__ else LogLevel.INFO
    
    # 解析日志格式
    fmt = config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 解析日志保存路径和文件名
    log_dir = config.get('log_dir', 'data/logs')
    filename = config.get('filename', 'app.log')
    
    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 构建完整的日志文件路径
    log_file_path = os.path.join(log_dir, filename)
    
    # 解析日志保存时间
    max_days = config.get('max_days', 30)
    
    # 获取处理器配置
    handlers_cfg = config.get('handlers', [{'type': 'console'}])
    
    config_obj = LoggerConfig()
    config_obj.set_level(level)
    config_obj.set_format(fmt)
    config_obj.handlers.clear()
    
    for handler_cfg in handlers_cfg:
        if handler_cfg.get('type') == 'console':
            handler = logging.StreamHandler()
            # 控制台使用带颜色的格式化器
            handler.setFormatter(ColoredFormatter(fmt))
            config_obj.add_handler(handler)
        elif handler_cfg.get('type') == 'file':
            # 文件使用普通格式化器（不需要颜色）
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setFormatter(logging.Formatter(fmt))
            config_obj.add_handler(file_handler)
    
    set_default_config(config_obj)
    
    # 返回配置信息供调试使用
    return {
        'level': level_str,
        'format': fmt,
        'log_dir': log_dir,
        'filename': filename,
        'log_file_path': log_file_path,
        'max_days': max_days
    } 