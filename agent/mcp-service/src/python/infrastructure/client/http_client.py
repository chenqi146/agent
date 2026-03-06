'''
@File    :   http_client.py
@Time    :   2025/09/10 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   http客户端
'''

from typing import Any, Dict
import requests
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

@logger()
class HttpClient:
    @staticmethod
    def post_synchronous(url:str,data:Dict[str, Any],timeout:int = 40):
        try:
            response = requests.post(url,json=data,timeout=timeout)
            response.raise_for_status()  # 检查HTTP状态码
            return ErrorCode.SUCCESS, response.json()
        except requests.exceptions.Timeout:
            return ErrorCode.TIMEOUT, None
        except requests.exceptions.ConnectionError:
            return ErrorCode.NETWORK_ERROR, None
        except requests.exceptions.HTTPError as e:
            return ErrorCode.EXTERNAL_SERVICE_ERROR, f"HTTP错误: {e}"
        except requests.exceptions.RequestException as e:
            return ErrorCode.EXTERNAL_SERVICE_ERROR, f"请求异常: {e}"
        except Exception as e:
            return ErrorCode.UNKNOWN_ERROR, f"未知错误: {e}"
        