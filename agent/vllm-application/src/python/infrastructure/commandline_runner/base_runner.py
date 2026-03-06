from abc import ABC, abstractmethod
from typing import Optional
from enum import Enum

class RunnerStatus(Enum):
    """运行器状态枚举"""
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

class CommandLineRunner(ABC):
    """类似Spring Boot的CommandLineRunner接口类"""
    
    def __init__(self, name: str = "CommandLineRunner", priority: int = 0):
        self.name = name
        self.priority = priority  # 优先级，数字越小优先级越高
        self.status = RunnerStatus.INITIALIZED
        self.error_message: Optional[str] = None
    
    @abstractmethod
    async def run(self, *args, **kwargs) -> bool:
        """
        运行方法，子类必须实现
        
        Returns:
            bool: 运行是否成功
        """
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """
        停止方法，子类必须实现
        
        Returns:
            bool: 停止是否成功
        """
        pass
    
    async def start(self, *args, **kwargs) -> bool:
        """
        启动运行器 - 通用实现，子类不需要重写
        
        Returns:
            bool: 启动是否成功
        """
        try:
            self.status = RunnerStatus.STARTING
            
            # 执行运行逻辑
            success = await self.run(*args, **kwargs)
            
            if success:
                self.status = RunnerStatus.RUNNING
            else:
                self.status = RunnerStatus.ERROR
                # 只有在没有设置错误消息时才设置默认消息
                if not self.error_message:
                    self.error_message = "运行失败"
            
            return success
            
        except Exception as e:
            self.status = RunnerStatus.ERROR
            self.error_message = str(e)
            return False
    
    def get_status(self) -> RunnerStatus:
        """获取运行器状态"""
        return self.status
    
    def get_error_message(self) -> Optional[str]:
        """获取错误信息"""
        return self.error_message
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self.status == RunnerStatus.RUNNING
    
    def is_stopped(self) -> bool:
        """检查是否已停止"""
        return self.status == RunnerStatus.STOPPED
    
    def has_error(self) -> bool:
        """检查是否有错误"""
        return self.status == RunnerStatus.ERROR
