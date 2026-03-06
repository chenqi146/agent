from typing import List, Optional, Dict, Any, Tuple
from infrastructure.persistences.mysql_persistence import MysqlPersistence
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
import json

@logger()
class AgentRepository:
    def __init__(self, persistence: MysqlPersistence):
        self.persistence = persistence

    def get_conversations(self, user_id: int, limit: int = 50, offset: int = 0) -> Tuple[ErrorCode, List[Dict]]:
        # Using execute_sql for complex query (ordering, limit)
        sql = """
            SELECT * FROM chat_conversation 
            WHERE user_id = %s AND is_deleted = 0 
            ORDER BY last_message_time DESC 
            LIMIT %s OFFSET %s
        """
        return self.persistence.execute_sql(sql, (user_id, limit, offset))

    def get_conversation_by_id(self, conversation_id: str) -> Tuple[ErrorCode, Optional[Dict]]:
        sql = "SELECT * FROM chat_conversation WHERE conversation_id = %s AND is_deleted = 0"
        err, result = self.persistence.execute_sql(sql, (conversation_id,))
        if err != ErrorCode.SUCCESS:
            return err, None
        return ErrorCode.SUCCESS, result[0] if result else None

    def create_conversation(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.persistence.insert("chat_conversation", data)

    def update_conversation(self, conversation_id: str, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.persistence.update("chat_conversation", data, "conversation_id = %s", (conversation_id,))

    def delete_conversation(self, conversation_id: str) -> Tuple[ErrorCode, int]:
        return self.persistence.update("chat_conversation", {"is_deleted": 1}, "conversation_id = %s", (conversation_id,))

    def clear_history(self, user_id: int) -> Tuple[ErrorCode, int]:
        return self.persistence.update("chat_conversation", {"is_deleted": 1}, "user_id = %s", (user_id,))

    def get_messages(self, conversation_id: str, limit: int = 100) -> Tuple[ErrorCode, List[Dict]]:
        sql = """
            SELECT * FROM chat_message 
            WHERE conversation_id = %s 
            ORDER BY seq_no ASC, created_at ASC
            LIMIT %s
        """
        err, result = self.persistence.execute_sql(sql, (conversation_id, limit))
        if err == ErrorCode.SUCCESS and result:
            for row in result:
                if row.get('metadata') and isinstance(row['metadata'], str):
                    try:
                        row['metadata'] = json.loads(row['metadata'])
                    except:
                        pass
        return err, result

    def save_message(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.persistence.insert("chat_message", data)
        
    def save_attachment(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        return self.persistence.insert("chat_message_attachment", data)

    def get_attachments(self, message_id: str) -> Tuple[ErrorCode, List[Dict]]:
        sql = "SELECT * FROM chat_message_attachment WHERE message_id = %s"
        return self.persistence.execute_sql(sql, (message_id,))

    def get_attachments_by_message_ids(self, message_ids: List[str]) -> Tuple[ErrorCode, List[Dict]]:
        if not message_ids:
            return ErrorCode.SUCCESS, []
        placeholders = ','.join(['%s'] * len(message_ids))
        sql = f"SELECT * FROM chat_message_attachment WHERE message_id IN ({placeholders})"
        return self.persistence.execute_sql(sql, tuple(message_ids))

    def get_last_seq_no(self, conversation_id: str) -> int:
        sql = "SELECT MAX(seq_no) as max_seq FROM chat_message WHERE conversation_id = %s"
        err, result = self.persistence.execute_sql(sql, (conversation_id,))
        if err == ErrorCode.SUCCESS and result and result[0]['max_seq'] is not None:
            return result[0]['max_seq']
        return 0

    def save_history_index(self, data: Dict[str, Any]) -> Tuple[ErrorCode, int]:
        # Check if index exists for this conversation
        sql = "SELECT id FROM chat_history_index WHERE conversation_id = %s"
        err, result = self.persistence.execute_sql(sql, (data['conversation_id'],))
        if err != ErrorCode.SUCCESS:
            return err, 0
            
        if result:
            # Update
            update_data = data.copy()
            if 'created_at' in update_data:
                del update_data['created_at']
            if 'user_id' in update_data:
                del update_data['user_id']

            return self.persistence.update(
                "chat_history_index", 
                update_data, 
                "conversation_id = %s", 
                (data['conversation_id'],)
            )
        else:
            # Insert
            return self.persistence.insert("chat_history_index", data)
