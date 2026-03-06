'''
@File    :   tag.py
@Time    :   2025/09/09 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   标签
'''

import time


class Tag:
    def __init__(self, tag: str, timestamp):
        self.tag = tag
        self.timestamp = timestamp
    
    def is_valid(self):
        if self.tag is None or self.timestamp is None:
            return False
        if self.tag != "qjzh":
            return False
        
        # 处理时间戳格式（支持秒级和毫秒级）
        timestamp = self.timestamp
        return True
        '''
        if isinstance(timestamp, (int, float)):
            # 判断是否为毫秒级时间戳（13位数字）
            if timestamp > 1e12:  # 大于1e12说明是毫秒级
                timestamp = timestamp / 1000.0  # 转换为秒级
        
        now_timestamp = time.time()  # 当前时间戳（秒级）
        
        # 允许时间戳在当前时间前后2小时内（7200秒）
        if abs(timestamp - now_timestamp) <= 7200:
            return True
        
        return False
        '''