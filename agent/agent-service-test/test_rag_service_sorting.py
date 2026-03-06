import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import asyncio

# Adjust path to include agent-service source
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_service_src = os.path.join(os.path.dirname(current_dir), 'agent-service', 'src', 'python')
sys.path.insert(0, agent_service_src)

from domain.service.rag_service import RagService
from infrastructure.common.error.errcode import ErrorCode
from interfaces.dto.rag_dto import KnowledgeSegmentListRequest

class TestRagServiceSorting(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = MagicMock()
        self.mysql = MagicMock()
        self.qdrant = MagicMock()
        self.minio = MagicMock()
        self.neo4j = MagicMock()
        
        self.repo_patcher = patch('domain.service.rag_service.RagRepository')
        self.MockRepo = self.repo_patcher.start()
        self.repo = self.MockRepo.return_value

        self.hsyq_patcher = patch('domain.service.rag_service.HsyqClient')
        self.MockHsyq = self.hsyq_patcher.start()

        self.embedding_patcher = patch('domain.service.rag_service.EmbeddingClient')
        self.MockEmbedding = self.embedding_patcher.start()
        
        self.service = RagService(self.config, self.mysql, self.qdrant, self.minio, self.neo4j)
        self.service.repo = self.repo

    def tearDown(self):
        self.repo_patcher.stop()
        self.hsyq_patcher.stop()
        self.embedding_patcher.stop()

    async def test_list_segments_sorting_params(self):
        """Test that list_segments passes sorting parameters correctly to the repository"""
        req = KnowledgeSegmentListRequest(
            file_id=1,
            page_no=1,
            page_size=10,
            sort_by="recall_count",
            sort_order="desc"
        )
        
        # Mock repo calls
        self.repo.get_file_by_id.return_value = (ErrorCode.SUCCESS, {"rag_id": 100})
        self.repo.get_knowledge_base_by_id.return_value = (ErrorCode.SUCCESS, {"id": 100})
        self.repo.list_segments_by_file.return_value = (ErrorCode.SUCCESS, [])
        self.repo.count_segments_by_file.return_value = (ErrorCode.SUCCESS, 0)
        
        await self.service.list_segments(req, user_id=1)
        
        # Verify repo.list_segments_by_file was called with correct arguments
        # args: file_id, status, binding_user_id, limit, offset, sort_by, sort_order
        self.repo.list_segments_by_file.assert_called_with(
            1, None, 1, 10, 0, "recall_count", "desc"
        )

if __name__ == '__main__':
    unittest.main()
