import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Adjust path to include agent-service source
current_dir = os.path.dirname(os.path.abspath(__file__))
# agent-service-test is in agent/
# source is in agent/agent-service/src/python
agent_service_src = os.path.join(os.path.dirname(current_dir), 'agent-service', 'src', 'python')
sys.path.insert(0, agent_service_src)

from domain.service.rag_service import RagService
from infrastructure.common.error.errcode import ErrorCode
from interfaces.dto.rag_dto import HybridRagQueryRequest

class TestRagService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = MagicMock()
        self.mysql = MagicMock()
        self.qdrant = MagicMock()
        self.minio = MagicMock()
        self.neo4j = MagicMock()
        
        # We need to patch RagRepository because it's instantiated inside RagService
        self.repo_patcher = patch('domain.service.rag_service.RagRepository')
        self.MockRepo = self.repo_patcher.start()
        self.repo = self.MockRepo.return_value

        # Patch HsyqClient
        self.hsyq_patcher = patch('domain.service.rag_service.HsyqClient')
        self.MockHsyq = self.hsyq_patcher.start()
        
        # Patch EmbeddingClient
        self.embedding_patcher = patch('domain.service.rag_service.EmbeddingClient')
        self.MockEmbedding = self.embedding_patcher.start()
        
        self.service = RagService(self.config, self.mysql, self.qdrant, self.minio, self.neo4j)
        # Verify repo is set (it is set in __init__)
        self.service.repo = self.repo

        # Mock embedding client
        self.service._embedding_client = self.MockEmbedding.return_value

    def tearDown(self):
        self.repo_patcher.stop()
        self.hsyq_patcher.stop()
        self.embedding_patcher.stop()

    async def test_get_ontology_statistics_success(self):
        """Test getting ontology statistics with successful Neo4j and Repo calls"""
        # Mock Neo4j responses
        # The service uses asyncio.to_thread(self._neo4j_client.execute_query, ...)
        
        self.neo4j.execute_query.side_effect = [
            (ErrorCode.SUCCESS, [{"node_count": 100}]), # Node count
            (ErrorCode.SUCCESS, [{"rel_count": 50}]),   # Rel count
            (ErrorCode.SUCCESS, [{"label": "Person"}, {"label": "Org"}]), # Labels
        ]
        
        self.repo.get_total_recall_count.return_value = (ErrorCode.SUCCESS, 999)

        err, stats = await self.service.get_ontology_statistics()

        self.assertEqual(err, ErrorCode.SUCCESS)
        self.assertEqual(stats["total_nodes"], 100)
        self.assertEqual(stats["total_relations"], 50)
        self.assertEqual(len(stats["labels"]), 2)
        self.assertEqual(stats["total_recall_count"], 999)

    async def test_get_ontology_statistics_neo4j_down(self):
        """Test graceful degradation when Neo4j is down"""
        # Simulate Neo4j client being None (service handles this)
        self.service._neo4j_client = None
        
        err, stats = await self.service.get_ontology_statistics()
        
        self.assertEqual(err, ErrorCode.SUCCESS)
        self.assertEqual(stats["total_nodes"], 0)
        self.assertEqual(stats["total_relations"], 0)
        self.assertEqual(stats["labels"], {})

    async def test_hybrid_rag_query_basic(self):
        """Test basic flow of hybrid RAG query (Stage 1 & 2 & 5)"""
        req = HybridRagQueryRequest(
            query="test query",
            kb_id=1,
            top_k=5
        )
        
        # Stage 1: Vector Search
        # Mock embed_texts
        self.service.embed_texts = MagicMock(return_value=(ErrorCode.SUCCESS, [[0.1, 0.2]]))
        # Mock qdrant search (used in Stage 1)
        self.qdrant.search.return_value = (ErrorCode.SUCCESS, [
            {
                "id": "uuid1", 
                "score": 0.9, 
                "payload": {
                    "segment_id": 101, 
                    "file_id": 10, 
                    "text": "content 1",
                    "rag_id": 1
                }
            }
        ])
        
        # Stage 2: Metadata Filtering
        # Mock repo.get_segments_by_ids (called in Stage 2 and Stage 5)
        self.repo.get_segments_by_ids.return_value = (ErrorCode.SUCCESS, [
            {
                "id": 101, 
                "status": 2, 
                "is_noise": False,
                "content": "Full Content 1",
                "title": "Title 1",
                "file_id": 10,
                "recall_count": 5
            }
        ])

        # Mock Stage 3 and Stage 4 because they are critical for Stage 5 input
        # Stage 3: Semantic Extension
        self.service._stage3_semantic_extension = AsyncMock(return_value=["concept1"])
        
        # Stage 4: Secondary Retrieval
        # This returns the list that Stage 5 processes
        self.service._stage4_secondary_retrieval_enhancement = AsyncMock(return_value=[
            {
                "id": "uuid1", 
                "score": 0.95, 
                "segment_id": 101, 
                "file_id": 10, 
                "text": "content 1",
                "chunk_index": 0
            }
        ])
        
        err, response = await self.service.hybrid_rag_query(req)
        
        self.assertEqual(err, ErrorCode.SUCCESS)
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0]["segment_id"], 101)
        self.assertEqual(response.results[0]["content"], "Full Content 1")

    async def test_hybrid_rag_query_complex(self):
        """Test complex flow: duplicates, multi-stage results, sorting"""
        req = HybridRagQueryRequest(
            query="complex query",
            kb_id=1,
            top_k=3
        )
        
        # Stage 1: Vector Search (3 results)
        self.service.embed_texts = MagicMock(return_value=(ErrorCode.SUCCESS, [[0.1, 0.2]]))
        self.qdrant.search.return_value = (ErrorCode.SUCCESS, [
            {"id": "uuid1", "score": 0.8, "payload": {"segment_id": 101, "file_id": 10, "text": "content 1", "rag_id": 1}},
            {"id": "uuid2", "score": 0.7, "payload": {"segment_id": 102, "file_id": 10, "text": "content 2", "rag_id": 1}},
            {"id": "uuid3", "score": 0.6, "payload": {"segment_id": 103, "file_id": 11, "text": "content 3", "rag_id": 1}}
        ])
        
        # Stage 2: Metadata Filtering (Filter out 103)
        # Mock get_segments_by_ids to return only 101 and 102 as valid
        self.repo.get_segments_by_ids.side_effect = [
            # First call for Stage 2
            (ErrorCode.SUCCESS, [
                {"id": 101, "status": 2, "is_noise": False, "content": "Full Content 1", "title": "Title 1", "file_id": 10, "recall_count": 5},
                {"id": 102, "status": 2, "is_noise": False, "content": "Full Content 2", "title": "Title 2", "file_id": 10, "recall_count": 3}
            ]),
            # Second call for Stage 5 (merging enhanced results)
             # Now that we merge filtered_results + enhanced_results, we need to return info for ALL of them.
             (ErrorCode.SUCCESS, [
                 {"id": 101, "status": 2, "is_noise": False, "content": "Full Content 1", "title": "Title 1", "file_id": 10, "recall_count": 5},
                 {"id": 102, "status": 2, "is_noise": False, "content": "Full Content 2", "title": "Title 2", "file_id": 10, "recall_count": 3},
                 {"id": 104, "status": 2, "is_noise": False, "content": "Full Content 4", "title": "Title 4", "file_id": 12, "recall_count": 1}
             ])
         ]

        # Stage 3: Semantic Extension
        self.service._stage3_semantic_extension = AsyncMock(return_value=["conceptA", "conceptB"])
        
        # Stage 4: Secondary Retrieval (Returns 101 again with higher score, and new 104)
        self.service._stage4_secondary_retrieval_enhancement = AsyncMock(return_value=[
            {"id": "uuid1_enhanced", "score": 0.95, "segment_id": 101, "file_id": 10, "text": "content 1", "chunk_index": 0},
            {"id": "uuid4", "score": 0.85, "segment_id": 104, "file_id": 12, "text": "content 4", "chunk_index": 0}
        ])
        
        err, response = await self.service.hybrid_rag_query(req)
        
        self.assertEqual(err, ErrorCode.SUCCESS)
        # Expecting: 
        # 101 (score 0.95 from enhanced > 0.8 from initial) -> deduplicated, keep highest? No, logic keeps first seen or merges?
        # Let's check logic: Stage 5 merges enhanced_results. Wait, Stage 5 only takes enhanced_results as input in code?
        # Ah, in rag_service.py:
        # final_results = await self._stage5_result_mapping_and_merging(enhanced_results, request.kb_id)
        # Wait, where does initial_results (filtered_results) go?
        # Let's re-read rag_service.py code.
        
        # Reading code snippet from previous turn:
        # 2288→            # 阶段5: 结果映射与合并 - 增强结果 → 映射到MySQL知识片段 → 片段合并策略 → 最终输出
        # 2289→            final_results = await self._stage5_result_mapping_and_merging(enhanced_results, request.kb_id)
        
        # It seems Stage 5 only processes `enhanced_results`!
        # AND `enhanced_results` comes from Stage 4.
        # BUT Stage 4 uses `related_concepts` AND `original_query` to query Qdrant again.
        # Does Stage 4 include the original filtered results?
        # Let's check Stage 4 code again.
       # We expect Stage 5 to merge filtered_results (101, 102) AND enhanced_results (101, 104).
        # So final list should have 101, 102, 104.
        # However, looking at current implementation of hybrid_rag_query, it seems to ONLY pass enhanced_results to Stage 5.
        # This implies filtered_results are discarded if not re-found in Stage 4.
        # We will assert the current behavior first, then fix the code if needed.
        # Current code behavior: only enhanced_results (101, 104) are processed.
        
        # But wait, if related_concepts is empty, Stage 4 returns empty. Then we get NO results?
        # That would be a bug. The intention of Hybrid RAG is usually to Combine.
        # Let's assume we WANT to fix it.
        # So I will assert that we get 101, 102, 104.
        
        # Note: Stage 5 does deduplication.
        
        result_ids = [r["segment_id"] for r in response.results]
        self.assertIn(101, result_ids)
        self.assertIn(104, result_ids)
        # 102 comes from filtered_results. If it's missing, we need to fix the service.
        self.assertIn(102, result_ids) 
        
        # Check sorting: 101 (0.95), 104 (0.85), 102 (0.7 from Stage 1)
        self.assertEqual(response.results[0]["segment_id"], 101)
        self.assertEqual(response.results[1]["segment_id"], 104)
        self.assertEqual(response.results[2]["segment_id"], 102)

if __name__ == '__main__':
    unittest.main()
