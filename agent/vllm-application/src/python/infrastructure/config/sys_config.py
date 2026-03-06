import os
from typing import Dict, Any
import yaml
class SysConfig:
    def __init__(self,config_path:str = None):
        if config_path is None:
            # 获取当前文件所在目录的上级目录的resources/application.yaml
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            config_path = os.path.join(project_root, 'resources', 'application.yaml')
        
        self.config_path = config_path
        # 计算项目基础路径（parking_sys根目录）
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
    
    def get_system_config(self) -> Dict[str, Any]:
        return self.config.get('system', {})
    
    def get_server_config(self) -> Dict[str, Any]:
        return self.config.get('server', {})
    
    def get_vllm_config(self) -> Dict[str,Any]:
        return self.config.get('vllm', {})
    
    def get_llm_config(self) -> Dict[str,Any]:
        return self.config.get('vllm', {}).get('llm', {})
    
    def get_embedding_config(self) -> Dict[str,Any]:
        return self.config.get('vllm', {}).get('embedding', {})
    
    def get_reranker_config(self) -> Dict[str,Any]:
        return self.config.get('vllm', {}).get('reranker', {})
    
    def get_vlm_config(self) -> Dict[str,Any]:
        return self.config.get('vllm', {}).get('vlm', {})
