from typing import Any, Dict, List, Optional, Tuple

from elasticsearch import Elasticsearch

from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger


@logger()
class ElasticsearchPersistence:
    def __init__(
        self,
        host: str,
        port: int,
        scheme: str,
        username: Optional[str],
        password: Optional[str],
        index: str,
    ):
        self.host = host
        self.port = port
        self.scheme = scheme
        self.username = username
        self.password = password
        self.index = index
        self.client = self._create_client()

    def _create_client(self) -> Optional[Elasticsearch]:
        try:
            hosts = [{"host": self.host, "port": self.port, "scheme": self.scheme}]
            if self.username and self.password:
                client = Elasticsearch(hosts=hosts, basic_auth=(self.username, self.password))
            else:
                client = Elasticsearch(hosts=hosts)
            return client
        except Exception as e:
            self.log.error("init elasticsearch client failed: %s", e, exc_info=True)
            return None

    def search(self, body: Dict[str, Any]) -> Tuple[ErrorCode, Optional[Dict[str, Any]]]:
        if self.client is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        try:
            resp = self.client.search(index=self.index, body=body)
            return ErrorCode.SUCCESS, resp
        except Exception as e:
            self.log.error("elasticsearch search failed: %s", e, exc_info=True)
            return ErrorCode.FACT_MEMORY_QUERY_FAILURE, None

    def bulk_delete_by_ids(self, ids: List[str]) -> Tuple[ErrorCode, Optional[object]]:
        if self.client is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        if not ids:
            return ErrorCode.SUCCESS, None
        try:
            operations: List[Dict[str, Any]] = []
            for doc_id in ids:
                operations.append({"delete": {"_index": self.index, "_id": doc_id}})
            self.client.bulk(operations=operations, refresh=True)
            return ErrorCode.SUCCESS, None
        except Exception as e:
            self.log.error("elasticsearch bulk delete failed: %s", e, exc_info=True)
            return ErrorCode.DATA_DELETE_FAILED, None

    def delete_by_query(self, query: Dict[str, Any]) -> Tuple[ErrorCode, Optional[object]]:
        if self.client is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        try:
            self.client.delete_by_query(index=self.index, body=query, refresh=True)
            return ErrorCode.SUCCESS, None
        except Exception as e:
            self.log.error("elasticsearch delete_by_query failed: %s", e, exc_info=True)
            return ErrorCode.DATA_DELETE_FAILED, None

    def save_document(self, doc_id: str, document: Dict[str, Any]) -> Tuple[ErrorCode, Optional[object]]:
        if self.client is None:
            return ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE, None
        try:
            self.client.index(index=self.index, id=doc_id, body=document, refresh=True)
            return ErrorCode.SUCCESS, None
        except Exception as e:
            self.log.error("elasticsearch save_document failed: %s", e, exc_info=True)
            return ErrorCode.DATA_SAVE_FAILED, None
