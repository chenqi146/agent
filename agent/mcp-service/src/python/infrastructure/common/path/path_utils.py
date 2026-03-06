'''
@File    :   path_utils.py
@Time    :   2025/01/15 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   路径工具类，提供全局路径管理功能
'''

import os
from typing import Optional


class PathUtils:
    """全局路径工具类"""
    
    _project_root: Optional[str] = None
    
    @classmethod
    def set_project_root(cls, project_root: str) -> None:
        """
        设置项目基础路径
        
        Args:
            project_root: 项目基础路径（proj目录的绝对路径）
        """
        cls._project_root = project_root
    
    @classmethod
    def get_project_root(cls) -> str:
        """
        获取项目基础路径
        
        Returns:
            str: 项目基础路径
            
        Raises:
            ValueError: 如果项目基础路径未设置
        """
        if cls._project_root is None:
            raise ValueError("项目基础路径未设置，请先调用 set_project_root() 方法")
        return cls._project_root
    
    @classmethod
    def get_absolute_path(cls, relative_path: str) -> str:
        """
        将相对路径转换为绝对路径
        
        Args:
            relative_path: 相对路径
            
        Returns:
            str: 绝对路径
        """
        if os.path.isabs(relative_path):
            return relative_path
        
        project_root = cls.get_project_root()
        return os.path.join(project_root, relative_path)
    
    @classmethod
    def get_resource_path(cls, relative_path: str) -> str:
        """
        获取资源文件的绝对路径
        
        Args:
            relative_path: 相对于resources目录的路径
            
        Returns:
            str: 资源文件的绝对路径
        """
        project_root = cls.get_project_root()
        return os.path.join(project_root, 'proj', 'resources', relative_path)
    
    @classmethod
    def get_lib_path(cls, relative_path: str) -> str:
        """
        获取库文件的绝对路径
        
        Args:
            relative_path: 相对于lib目录的路径
            
        Returns:
            str: 库文件的绝对路径
        """
        project_root = cls.get_project_root()
        return os.path.join(project_root, 'proj', 'resources', 'lib', relative_path)
    
    @classmethod
    def get_model_path(cls, relative_path: str) -> str:
        """
        获取模型文件的绝对路径
        
        Args:
            relative_path: 相对于models目录的路径
            
        Returns:
            str: 模型文件的绝对路径
        """
        project_root = cls.get_project_root()
        return os.path.join(project_root, 'proj', 'resources', 'models', relative_path)
    
    @classmethod
    def get_log_path(cls, relative_path: str) -> str:
        """
        获取日志文件的绝对路径
        
        Args:
            relative_path: 相对于logs目录的路径
            
        Returns:
            str: 日志文件的绝对路径
        """
        project_root = cls.get_project_root()
        return os.path.join(project_root, 'logs', relative_path)
    
    @classmethod
    def ensure_dir_exists(cls, path: str) -> None:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            path: 目录路径
        """
        dir_path = os.path.dirname(path) if os.path.isfile(path) else path
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
