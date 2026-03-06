'''
@File    :   q_drant_client.py
@Time    :   2025/09/14 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   QDrant客户端
'''

import threading
from typing import Any, Dict
from infrastructure.config.sys_config import SysConfig
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

@logger()
class QDrantClient:
    def __init__(self, config: SysConfig):
        self.client = QdrantClient(url=config.get('url'), api_key=config.get('api_key'))
    
    def get_client(self):
        return self.client
    
    def insert_data(self, collection_name: str, data: Dict[str, Any]):
        self.client.insert(collection_name, data)
    
    def query_data(self, collection_name: str, query: Dict[str, Any]):
        self.client.query(collection_name, query)
    
    def delete_data(self, collection_name: str, data: Dict[str, Any]):
        self.client.delete(collection_name, data)

class QDrantTemplete:
    client: QDrantClient = None
    lock = threading.Lock()
    is_init = False

    @staticmethod
    def init(config: Dict[str, Any]):
        QDrantTemplete.client = QDrantClient(config)
        QDrantTemplete.is_init = True
        return True
    
    @staticmethod
    def deinit():
        QDrantTemplete.client = None
        QDrantTemplete.is_init = False
    
    @staticmethod
    def async_insert_data(collection_name: str, data: Dict[str, Any]):
        QDrantTemplete.client.async_insert_data(collection_name, data)
    
    @staticmethod
    def async_query_data(collection_name: str, query: Dict[str, Any]):
        QDrantTemplete.client.async_query_data(collection_name, query)
    
    @staticmethod
    def async_delete_data(collection_name: str, data: Dict[str, Any]):
        QDrantTemplete.client.async_delete_data(collection_name, data)