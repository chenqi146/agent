'''
@File    :   devops_runner.py
@Time    :   2025/09/09 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   运维运行器
'''

import threading
import time
import psutil
from infrastructure.commandline_runner.base_runner import CommandLineRunner, RunnerStatus
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig

@logger()
class DevopsRunner(CommandLineRunner):
    def __init__(self,config:dict):
        super().__init__("DevopsRunner", 1)
        self.devops_thread = None
        self.config = config
    
    def __get_cpu_usage(self):
        return psutil.cpu_percent(interval=1)
    
    def __get_memory_usage(self):
        return psutil.virtual_memory().percent
    
    def __get_disk_usage(self):
        return psutil.disk_usage('/').percent

    def devops_thread_func(self):
        self.log.info("DevopsRunner devops_thread start")
        while not self.is_stopped():
            resource_usage = {
                "cpu_usage": self.__get_cpu_usage(),
                "memory_usage": self.__get_memory_usage(),
                "disk_usage": self.__get_disk_usage(),
            }
            self.log.info(f"DevopsRunner resource_usage: {resource_usage}")
            time.sleep(self.config.get('check_system_resource_period'))
        self.log.info("DevopsRunner devops_thread stop")

    async def run(self):
        self.log.info("DevopsRunner run start")
        self.devops_thread = threading.Thread(target=self.devops_thread_func)
        self.devops_thread.start()
        return True
    
    async def stop(self):
        self.log.info("DevopsRunner stop start")
        self.status = RunnerStatus.STOPPED
        
        if self.devops_thread and self.devops_thread.is_alive():
            self.log.info("等待 DevopsRunner 线程结束...")
            self.devops_thread.join(timeout=5)
            if self.devops_thread.is_alive():
                self.log.warn("DevopsRunner 线程未能在5秒内结束")
            else:
                self.log.info("DevopsRunner 线程已结束")
        
        self.devops_thread = None
        self.log.info("DevopsRunner stop success")
        return True