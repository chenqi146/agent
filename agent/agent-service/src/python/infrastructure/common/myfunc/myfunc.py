'''
@File    :   myfunc.py
@Time    :   2025/09/14 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   通用函数
'''

import os
import random
import string
import time

class MyFunc:
    @staticmethod
    def get_random_string(length: int):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def get_random_number(length: int):
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def get_current_timestamp():
        return int(time.time())