'''
@File    :   myfile.py
@Time    :   2025/09/10 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   文件操作
'''

import os
from typing import Any, Dict, List, Optional, Tuple, Union

class MyFile:
    @staticmethod
    def create_dir(dir_path: str):
        """
        创建目录（如果不存在）
        
        Args:
            dir_path: 目录路径，可以是相对路径或绝对路径
                     - 如果是相对路径，会基于当前工作目录创建
                     - 如果是绝对路径，直接使用
        
        Returns:
            str: 创建的目录路径（绝对路径）
        """
        if not dir_path:
            raise ValueError("dir_path cannot be empty")
        
        # 如果是相对路径，转换为绝对路径（基于当前工作目录）
        if not os.path.isabs(dir_path):
            dir_path = os.path.abspath(dir_path)
        
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        return dir_path
    
    @staticmethod
    def get_file_path(file_name: str):
        return os.path.join(os.path.dirname(__file__), file_name)
    
    @staticmethod
    def get_file_content(file_path: str):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    @staticmethod
    def write_file(file_path: str, content: str):
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    @staticmethod
    def append_file(file_path: str, content: str):
        with open(file_path, 'a', encoding='utf-8') as file:
            file.write(content)
    
    @staticmethod
    def is_file_exists(file_path: str):
        return os.path.exists(file_path)
    
    @staticmethod
    def is_dir_exists(dir_path: str):
        return os.path.isdir(dir_path)
    
    @staticmethod
    def is_file_readable(file_path: str):
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK)
    
    