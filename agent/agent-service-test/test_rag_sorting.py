import unittest
from unittest.mock import MagicMock
import sys
import os

# Adjust path to include agent-service source
current_dir = os.path.dirname(os.path.abspath(__file__))
# agent-service-test is in agent/agent-service-test
# source is in agent/agent-service/src/python
agent_service_src = os.path.join(os.path.dirname(current_dir), 'agent-service', 'src', 'python')
sys.path.insert(0, agent_service_src)

from infrastructure.repositories.rag_repository import RagRepository
from infrastructure.common.error.errcode import ErrorCode

class TestRagRepositorySorting(unittest.TestCase):
    def setUp(self):
        self.mysql = MagicMock()
        self.config = MagicMock()
        self.repo = RagRepository(self.config, self.mysql)

    def test_default_sorting(self):
        """Test default sorting when sort_by is None or unknown"""
        self.mysql.select.return_value = (ErrorCode.SUCCESS, [])
        
        # Case 1: sort_by is None
        self.repo.list_segments_by_file(1, None, None, 10, 0, sort_by=None)
        kwargs = self.mysql.select.call_args[1]
        self.assertEqual(kwargs['order_by'], "sort_index ASC, update_time DESC")

        # Case 2: sort_by is unknown
        self.repo.list_segments_by_file(1, None, None, 10, 0, sort_by="unknown")
        kwargs = self.mysql.select.call_args[1]
        self.assertEqual(kwargs['order_by'], "sort_index ASC, update_time DESC")

    def test_recall_count_sorting(self):
        """Test sorting by recall_count"""
        self.mysql.select.return_value = (ErrorCode.SUCCESS, [])
        
        # DESC
        self.repo.list_segments_by_file(1, None, None, 10, 0, sort_by="recall_count", sort_order="desc")
        kwargs = self.mysql.select.call_args[1]
        self.assertEqual(kwargs['order_by'], "recall_count DESC, update_time DESC")

        # ASC
        self.repo.list_segments_by_file(1, None, None, 10, 0, sort_by="recall_count", sort_order="asc")
        kwargs = self.mysql.select.call_args[1]
        self.assertEqual(kwargs['order_by'], "recall_count ASC, update_time DESC")

    def test_updated_at_sorting(self):
        """Test sorting by updated_at (maps to update_time)"""
        self.mysql.select.return_value = (ErrorCode.SUCCESS, [])
        
        # DESC
        self.repo.list_segments_by_file(1, None, None, 10, 0, sort_by="updated_at", sort_order="desc")
        kwargs = self.mysql.select.call_args[1]
        self.assertEqual(kwargs['order_by'], "update_time DESC")

        # ASC
        self.repo.list_segments_by_file(1, None, None, 10, 0, sort_by="updated_at", sort_order="asc")
        kwargs = self.mysql.select.call_args[1]
        self.assertEqual(kwargs['order_by'], "update_time ASC")

if __name__ == '__main__':
    unittest.main()
