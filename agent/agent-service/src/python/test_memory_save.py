import os
import sys
import asyncio
from datetime import datetime
import uuid
from typing import Optional, Tuple, Dict, Any

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))))
sys.path.insert(0, project_root)

from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.elasticsearch_persistence import ElasticsearchPersistence
from infrastructure.repositories.memory_repository import MemoryRepository
from domain.service.memory_service import MemoryService
from infrastructure.common.error.errcode import ErrorCode

# Mock MysqlPersistence
class MockMysqlPersistence:
    def __init__(self):
        pass

async def test_memory_save():
    print("Initializing components...")
    
    # 1. Load Config
    config_path = os.path.join(os.path.dirname(current_dir), 'resources', 'application.yaml')
    config = SysConfig(config_path)
    
    # 2. Init ElasticsearchPersistence
    es_cfg = config.get_system_config().get('persistence', {}).get('elasticsearch', {})
    print(f"ES Config: {es_cfg}")
    
    es_client = ElasticsearchPersistence(
        host=es_cfg.get('host', '127.0.0.1'),
        port=es_cfg.get('port', 9200),
        scheme=es_cfg.get('scheme', 'http'),
        username=es_cfg.get('username'),
        password=es_cfg.get('password'),
        index=es_cfg.get('index', 'pg-agent-memory')
    )
    
    # 3. Init MemoryService with Mock MySQL
    mysql_client = MockMysqlPersistence()
    memory_service = MemoryService(config, mysql_client, es_client)
    
    # 4. Test add_memory
    print("Testing add_memory...")
    user_id = 12345
    query = "Test query from script"
    response = "Test response from script"
    
    err, doc_id = memory_service.add_memory(user_id, query, response)
    
    if err == ErrorCode.SUCCESS:
        print(f"Successfully saved memory. DocID: {doc_id}")
    else:
        print(f"Failed to save memory. Error: {err}")

if __name__ == "__main__":
    asyncio.run(test_memory_save())
