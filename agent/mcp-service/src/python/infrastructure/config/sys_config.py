import os
from typing import Dict, Any
import yaml
class SysConfig:
    def __init__(self,config_path:str = None):
        if config_path is None:
            # 获取当前文件所在目录，然后向上找到resources目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 从 infrastructure/config/ 向上到 src/resources/
            config_path = os.path.join(current_dir, '..', '..', '..', 'resources', 'application.yaml')
            # 标准化路径
            config_path = os.path.normpath(config_path)
        
        self.config_path = config_path
        # 计算项目基础路径
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        try:
            # 读取主配置文件
            with open(self.config_path, 'r', encoding='utf-8') as file:
                main_config = yaml.safe_load(file) or {}

                # 获取server.type字段
                server_type = main_config.get('server', {}).get('type')
                if server_type:
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
                    dev_config_path = os.path.join(project_root, 'resources', f'application-{server_type}.yaml')
                    if os.path.exists(dev_config_path):
                        with open(dev_config_path, 'r', encoding='utf-8') as dev_file:
                            dev_config = yaml.safe_load(dev_file) or {}
                        # 合并配置，dev配置覆盖主配置
                        def deep_merge(a, b):
                            for k, v in b.items():
                                if (
                                    k in a
                                    and isinstance(a[k], dict)
                                    and isinstance(v, dict)
                                ):
                                    deep_merge(a[k], v)
                                else:
                                    a[k] = v
                            return a
                        merged_config = deep_merge(main_config, dev_config)
                        return merged_config
                return main_config
        except Exception as e:
            raise Exception(f"Failed to load config file: {self.config_path}") from e

    def get_log_config(self) -> Dict[str, Any]:
        return self.config.get('log', {})
    
    def get_agent_config(self) -> Dict[str, Any]:
        return self.config.get('agent', {})

    def get_system_config(self)->Dict[str, Any]:
        return self.config.get('system', {})

    def get_server_config(self)->Dict[str, Any]:
        return self.config.get('server', {})
    
    def get_redis_config(self)->Dict[str, Any]:
        return self.config.get('system', {}).get('persistence', {}).get('redis', {})

    def get_vlm_config(self)->Dict[str, Any]:
        return self.config.get('agent', {}).get('llm', {})

    def get_vllm_embedding_base_url(self) -> str:
        """vllm-application Embedding 服务根地址，用于调用 /v1/embeddings"""
        return (self.get_system_config() or {}).get('vllm', {}).get('embedding_base_url', '')

    def get_vllm_embedding_api_key(self) -> str:
        """vllm-application Embedding 服务 API Key（用于 Authorization / X-API-Key）"""
        return (self.get_system_config() or {}).get('vllm', {}).get('embedding_api_key', '')

    def get_supported_file_types(self) -> set:
        """获取支持的文件类型配置"""
        file_type_config = (self.get_system_config() or {}).get('vllm', {}).get('file_type', '')
        if not file_type_config:
            # 默认支持的文件类型
            return {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'html', 'htm'}
        
        # 解析配置字符串，支持逗号分隔的格式
        try:
            # 移除空格和引号，然后按逗号分割
            file_types = file_type_config.replace('"', '').replace("'", '').replace(' ', '').split(',')
            supported_types = set()
            
            for file_type in file_types:
                file_type = file_type.lower().strip()
                if file_type == 'txt':
                    supported_types.add('txt')
                elif file_type == 'pdf':
                    supported_types.add('pdf')
                elif file_type == 'office':
                    # office类型包含所有Office文档格式
                    supported_types.update(['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'])
                elif file_type == 'html':
                    supported_types.update(['html', 'htm'])
                else:
                    # 直接添加具体的文件扩展名
                    supported_types.add(file_type)
            
            return supported_types
        except Exception as e:
            # 解析失败时返回默认值
            return {'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'html', 'htm'}


