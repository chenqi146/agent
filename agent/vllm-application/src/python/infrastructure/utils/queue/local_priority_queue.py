'''
@File    :   local_priority_queue.py
@Time    :   2025/09/09 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   本地优先队列
'''

import queue
from typing import List, Dict, Any
from infrastructure.common.logging.logging import logger

@logger()
class LocalPriorityQueue(queue.PriorityQueue):
    def __init__(self, max_size: int):
        self.max_size = max_size
    
    def enqueue(self, item: Any):
        if self.is_full():
            return False
        self.put(item)
        return True
    
    def dequeue(self,timeout:int) -> Any:
        if self.is_empty():
            return None
        return self.get(timeout)
    
    def is_empty(self) -> bool:
        return self.qsize() == 0
    
    def get_size(self) -> int:
        return self.qsize()
    
    def get_max_size(self) -> int:
        return self.max_size
    
    def get_queue(self) -> List[Any]:
        return self.queue

    def is_full(self) -> bool:
        return self.qsize() >= self.max_size