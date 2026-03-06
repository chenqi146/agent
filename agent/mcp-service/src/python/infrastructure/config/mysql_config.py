import sys
import os
from typing import Dict, Any
from pathlib import Path

# 添加模型模块路径
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.persistences.mysql_persistence import MysqlPersistence


def mysql_config(mysql_config_dict: Dict[str, Any]):
    """mysql配置注解 - 初始化mysql persistence"""
    def decorator(cls):
        try:
            mysql_instance = MysqlPersistence(
                host=mysql_config_dict.get('host', '127.0.0.1'),
                port=mysql_config_dict.get('port', 3306),
                username=mysql_config_dict.get('username', 'root'),
                password=mysql_config_dict.get('password', '123456'),
                database=mysql_config_dict.get('database', 'parking_mng_db'),
                charset=mysql_config_dict.get('charset', 'utf8mb4')
            )
            cls.mysql_persistence = mysql_instance
        except Exception as e:
            # 如果创建失败，设置为None
            cls.mysql_persistence = None
            print(f"MySQL配置装饰器错误: {e}")
        
        return cls
    
    return decorator
