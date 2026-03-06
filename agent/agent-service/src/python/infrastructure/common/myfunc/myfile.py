'''
@File    :   myfile.py
@Time    :   2025/09/10 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   文件操作
'''

import os
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

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

    def to_absolute_path(file_path: Union[str, Path],
                         base_dir: Optional[str] = None,
                         expand_user: bool = True) -> str:
        """
        将路径转换为绝对路径

        Args:
            file_path: 文件路径（相对或绝对）
            base_dir: 基准目录，为None时自动选择
            expand_user: 是否展开~符号

        Returns:
            绝对路径字符串
        """
        if not file_path:
            raise ValueError("文件路径不能为空")

        # 转换为字符串
        if isinstance(file_path, Path):
            path_str = str(file_path)
        else:
            path_str = str(file_path)

        path_str = path_str.strip()
        if not path_str:
            raise ValueError("文件路径不能为空字符串")

        # 展开用户目录
        if expand_user and '~' in path_str:
            path_str = os.path.expanduser(path_str)

        # 如果已经是绝对路径，直接返回
        if os.path.isabs(path_str):
            return os.path.normpath(path_str)

        # 确定基准目录
        if base_dir is None:
            # 默认使用当前工作目录
            base_dir = os.getcwd()
        else:
            # 确保基准目录是绝对路径
            if not os.path.isabs(base_dir):
                base_dir = os.path.abspath(base_dir)

        # 构建绝对路径
        absolute_path = os.path.join(base_dir, path_str)

        # 规范化路径（去除..和.）
        absolute_path = os.path.normpath(absolute_path)

        return absolute_path

    def safe_to_absolute(file_path: Union[str, Path],
                         base_dir: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        安全地将路径转换为绝对路径

        Args:
            file_path: 文件路径
            base_dir: 基准目录

        Returns:
            (是否成功, 绝对路径或错误信息)
        """
        try:
            absolute_path = MyFile.to_absolute_path(file_path, base_dir)
            return True, absolute_path
        except Exception as e:
            return False, f"转换失败: {str(e)}"

    
    @staticmethod
    def is_file_exists(file_path: str,
                       base_dirs: List[str] = None,
                       search_recursive: bool = False) -> bool:
        """
        检查文件是否存在，支持相对路径

        Args:
            file_path: 文件路径（可以是相对或绝对路径）
            base_dirs: 搜索基础目录列表，为None时自动确定
            search_recursive: 是否在子目录中递归搜索

        Returns:
            (是否存在, 实际路径或错误信息)
        """
        try:
            # 转换为Path对象便于处理
            path = Path(file_path)

            # 1. 如果是绝对路径，直接检查
            if path.is_absolute():
                if path.is_file():
                    return True
                elif path.exists():
                    return False
                else:
                    return False

            # 2. 如果是相对路径，确定搜索基础目录
            if base_dirs is None:
                # 默认搜索顺序
                base_dirs = [
                    os.getcwd(),  # 当前工作目录
                    Path(__file__).parent.absolute(),  # 脚本所在目录
                    os.path.expanduser("~"),  # 用户主目录
                ]

            # 3. 在基础目录中搜索
            searched_paths = []
            for base_dir in base_dirs:
                base_path = Path(base_dir)

                # 构建完整路径
                full_path = base_path / path

                # 如果是递归搜索
                if search_recursive and not full_path.exists():
                    # 在子目录中查找
                    for found_path in base_path.rglob(str(path)):
                        if found_path.is_file():
                            return True

                # 普通查找
                if full_path.is_file():
                    return True

                searched_paths.append(str(full_path))

                # 检查路径是否存在但不是文件
                if full_path.exists():
                    return False

            # 4. 检查PATH环境变量中的可执行文件
            if file_path and not Path(file_path).suffix:  # 无扩展名，可能是可执行文件
                for path_dir in os.getenv("PATH", "").split(os.pathsep):
                    exe_path = Path(path_dir) / file_path
                    if exe_path.is_file():
                        return True

            # 5. 文件不存在
            error_msg = (f"文件未找到: '{file_path}'\n"
                         f"搜索过的位置:\n" +
                         "\n".join(f"  - {p}" for p in searched_paths))
            return False

        except PermissionError:
            return False
        except Exception as e:
            return False
    
    @staticmethod
    def is_dir_exists(dir_path: str):
        try:
            if os.path.isabs(dir_path):
                return os.path.isdir(dir_path)
            else:
                cwd_path = os.path.join(os.getcwd(), dir_path)
                return os.path.isdir(cwd_path)
        except Exception as e:
            return False

    
    @staticmethod
    def is_file_readable(file_path: str):
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK)
    
    