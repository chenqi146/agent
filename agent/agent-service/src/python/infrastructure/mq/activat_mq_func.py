'''
@File    :   activat_mq_func.py
@Time    :   2025/09/08 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   activeMQ函数
'''
from typing import Callable, Dict, Any, Optional
from infrastructure.persistences.activate_mq_api import ActivateMQApi
from infrastructure.common.logging.logging import logger
from infrastructure.config.activate_mq_config import activate_mq_config

@logger()
class ActivatMQFunc:
    def __init__(self,config:Dict[str,Any]):
        try:
            @activate_mq_config(config)
            class ActivateMQConfig:
                pass
            self.activate_mq_api = ActivateMQConfig.activateMQ_api
            self.activate_mq_api.connect()
            self.log.info(f"ActivatMQFunc init success: {self.activate_mq_api}")
        except Exception as e:
            self.log.error(f"ActivatMQFunc init error: {e}")
            self.activate_mq_api = None
    
    def __del__(self):
        if self.activate_mq_api is not None:         
            self.activate_mq_api.disconnect()
            self.log.info(f"ActivatMQFunc del success: {self.activate_mq_api}")
    
    def publish(self,destination:str,message:str,headers:Optional[Dict[str,Any]] = None, 
                receipt:bool = False, receipt_callback:Optional[Callable[[str, bool], None]] = None,
                receipt_timeout:float = 10.0):
        return self.activate_mq_api.publish(destination,message,headers,receipt,receipt_callback,receipt_timeout)
    
    def subscribe(self,destination:str,callback:Callable[[str,Dict[str,Any]],None],ack:str = 'auto',subscription_id:Optional[str] = None):
        return self.activate_mq_api.subscribe(destination,callback,ack,subscription_id)
    
    def unsubscribe(self,subscription_id:str):
        return self.activate_mq_api.unsubscribe(subscription_id)