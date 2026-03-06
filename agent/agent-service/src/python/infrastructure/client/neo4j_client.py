from typing import Any, Dict, List, Optional, Tuple, Union
from neo4j import GraphDatabase, Driver
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig

@logger()
class Neo4jClient:
    def __init__(self, config: SysConfig):
        self.config = config
        self._driver: Optional[Driver] = None
        self._init_driver()

    def _init_driver(self):
        """Initialize Neo4j driver from configuration"""
        try:
            persistence_config = self.config.get_system_config().get("persistence", {})
            neo4j_config = persistence_config.get("neo4j", {})
            host = neo4j_config.get("host", "127.0.0.1")
            port = neo4j_config.get("port", 7687)
            username = neo4j_config.get("username", "neo4j")
            password = neo4j_config.get("password", "")
            
            uri = f"bolt://{host}:{port}"
            self._driver = GraphDatabase.driver(uri, auth=(username, password))
            
            # Verify connection
            self._driver.verify_connectivity()
            self.log.info(f"Connected to Neo4j at {uri}")
        except Exception as e:
            self.log.error(f"Failed to initialize Neo4j driver: {e}")
            self._driver = None

    def close(self):
        """Close the Neo4j driver connection"""
        if self._driver:
            self._driver.close()
            self.log.info("Neo4j driver closed")

    def execute_query(self, query: str, parameters: Dict[str, Any] = None, database: str = None) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        Execute a Cypher query
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name
            
        Returns:
            Tuple[ErrorCode, Result List]
        """
        if not self._driver:
            # Try to reconnect if driver is missing
            self._init_driver()
            if not self._driver:
                return ErrorCode.DATABASE_CONNECTION_ERROR, []

        try:
            records, summary, keys = self._driver.execute_query(
                query, 
                parameters_=parameters or {},
                database_=database
            )
            
            # Convert records to list of dicts for easier consumption
            result = [record.data() for record in records]
            return ErrorCode.SUCCESS, result
            
        except Exception as e:
            self.log.error(f"Neo4j query execution failed: {e}")
            return ErrorCode.DATABASE_EXECUTION_ERROR, []

    def verify_connectivity(self) -> bool:
        """Check if connected to Neo4j"""
        if not self._driver:
            self.log.error("Neo4j driver not initialized")
            return False
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            self.log.error("Failed to verify Neo4j connectivity")
            return False
