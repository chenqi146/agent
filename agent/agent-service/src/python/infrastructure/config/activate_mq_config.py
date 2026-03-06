'''
@File    :   activate_mq_config.py
@Time    :   2025/09/08 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   activeMQ配置
'''

import sys
import os
from typing import Dict, Any
from pathlib import Path

# 添加模型模块路径
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.persistences.activate_mq_api import ActivateMQApi

def activate_mq_config(activate_mq_config_dict: Dict[str, Any]):
    '''activeMQ配置注解 - 初始化activeMQ persistence'''
    def decorator(cls):
        try:
            activeMQ_instance = ActivateMQApi(activate_mq_config_dict)
            cls.activateMQ_api = activeMQ_instance
        except Exception as e:
            cls.activateMQ_api = None
            print(f"ActiveMQ配置装饰器错误: {e}")
        
        return cls
    
    return decorator
    