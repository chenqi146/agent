'''
@File    :   redis_client.py
@Time    :   2025/09/09 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   redis客户端
'''

import threading
import json
from typing import Any, Callable, Dict, Optional
from datetime import datetime
from infrastructure.common.error.errcode import ErrorCode
import redis
from infrastructure.common.logging.logging import logger, method_logger

@logger()
class RedisClient:
    def __init__(self, host: str, port: int, password: str, database: int):
        self.redis_client = redis.Redis(host=host, port=port, password=password, db=database)
    
    def close(self):
        """关闭Redis连接"""
        if hasattr(self, 'redis_client') and self.redis_client is not None:
            try:
                self.redis_client.close()
                self.log.info(f"RedisClient close success")
            except Exception as e:
                self.log.error(f"RedisClient close error: {e}")
            finally:
                self.redis_client = None
    
    def __del__(self):
        if hasattr(self, 'redis_client') and self.redis_client is not None:
            try:
                self.redis_client.close()
                self.log.info(f"RedisClient del success")
            except Exception as e:
                self.log.error(f"RedisClient del error: {e}")
            finally:
                self.redis_client = None
    
    '''
    获取key的值
    '''
    def get(self, key: str):
        return self.redis_client.get(key)
    
    '''
    设置key的值
    '''
    def set(self, key: str, value: Any):
        return self.redis_client.set(key, value)
    
    '''
    设置key的值，并设置过期时间,单位为秒
    '''
    def set_with_expire(self, key: str, value: Any, expire_time: int):
        return self.redis_client.set(key, value, ex=expire_time)
    
    '''
    删除key的值
    '''
    def delete(self, key: str):
        return self.redis_client.delete(key)
    
    '''
    判断key是否存在
    '''
    def exists(self, key: str):
        return self.redis_client.exists(key)
    
    '''
    获取所有key
    '''
    def get_all_keys(self):
        return self.redis_client.keys()
    
    '''
    发布消息
    '''
    def publish(self, channel: str, message: Any):
        return self.redis_client.publish(channel, message)
    
    '''
    创建PubSub对象
    '''
    def __pubsub(self):
        return self.redis_client.pubsub()
    
    '''
    订阅频道（返回PubSub对象）
    '''
    def subscribe(self, *channels):
        """
        订阅一个或多个频道
        
        Args:
            *channels: 频道名称列表
            
        Returns:
            PubSub对象
        """
        pubsub = self.redis_client.__pubsub()
        pubsub.subscribe(*channels)
        return pubsub
    
    '''
    使用回调函数订阅频道
    '''
    def subscribe_with_callback(self, channel: str, callback: Callable[[dict], None]):
        """
        使用回调函数订阅频道
        
        Args:
            channel: 频道名称
            callback: 回调函数，接收消息字典作为参数
            
        Returns:
            PubSub对象
        """
        pubsub = self.redis_client.pubsub()
        # 先订阅频道
        pubsub.subscribe(channel)
        # 将回调函数存储到pubsub对象中，供后续使用
        pubsub._callback = callback
        return pubsub


class RedisTemplete:
    redis_client: RedisClient = None
    lock = threading.Lock()
    is_init = False

    @staticmethod
    def init(config: Dict[str, Any]):
        try:
            RedisTemplete.redis_client = RedisClient(config['host'], config['port'], config['password'], config['database'])
            RedisTemplete.is_init = True
            print(f"RedisTemplete init success: {RedisTemplete.redis_client}")
            return True
        except Exception as e:
            print(f"RedisTemplete init error: {e}")
            RedisTemplete.redis_client = None
            return False
    
    @staticmethod
    def deinit():
        if RedisTemplete.redis_client is not None:
            RedisTemplete.redis_client.close()
            print(f"RedisTemplete deinit success")
            RedisTemplete.redis_client = None
            RedisTemplete.is_init = False
    
    @staticmethod
    def test():
        RedisTemplete.lock.acquire()
        try:
            if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
                # 设置测试键值
                RedisTemplete.redis_client.set("test", "test")
                # 获取并验证
                result = RedisTemplete.redis_client.get("test")
                if result == b"test":  # Redis返回的是bytes类型
                    # 清理测试数据
                    RedisTemplete.redis_client.delete("test")
                    return True
                else:
                    # 清理测试数据
                    RedisTemplete.redis_client.delete("test")
                    return False
            else:
                print(f"RedisTemplete is not init or redis_client is None")
                return False
        except Exception as e:
            print(f"RedisTemplete test error: {e}")
            return False
        finally:
            RedisTemplete.lock.release()

    @staticmethod
    def set(key: str, value: Any, expire_time: int = 0):
        RedisTemplete.lock.acquire()
        try:
            if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
                if expire_time > 0:
                    RedisTemplete.redis_client.set_with_expire(key, value, expire_time)
                else:
                    RedisTemplete.redis_client.set(key, value)
            else:
                print(f"RedisTemplete is not init or redis_client is None")
        finally:
            RedisTemplete.lock.release()
    
    @staticmethod
    def get(key: str):
        RedisTemplete.lock.acquire()
        try:
            if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
                return RedisTemplete.redis_client.get(key)
            else:
                print(f"RedisTemplete is not init or redis_client is None")
                return None
        finally:
            RedisTemplete.lock.release()
    
    @staticmethod
    def delete(key: str):
        RedisTemplete.lock.acquire()
        try:
            if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
                RedisTemplete.redis_client.delete(key)
            else:
                print(f"RedisTemplete is not init or redis_client is None")
        finally:
            RedisTemplete.lock.release()
    
    @staticmethod
    def exists(key: str):
        RedisTemplete.lock.acquire()
        try:
            if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
                return RedisTemplete.redis_client.exists(key)
            else:
                print(f"RedisTemplete is not init or redis_client is None")
                return False
        finally:
            RedisTemplete.lock.release()
    
    @staticmethod
    def get_all_keys():
        RedisTemplete.lock.acquire()
        try:
            if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
                return RedisTemplete.redis_client.get_all_keys()
            else:
                print(f"RedisTemplete is not init or redis_client is None")
                return []
        finally:
            RedisTemplete.lock.release()
    
    @staticmethod
    def publish(channel: str, message: Any):
        RedisTemplete.lock.acquire()
        try:
            if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
                return RedisTemplete.redis_client.publish(channel, message)
            else:
                print(f"RedisTemplete is not init or redis_client is None")
                return 0
        finally:
            RedisTemplete.lock.release()
    
    @staticmethod
    def subscribe(*channels):
        """
        订阅一个或多个频道
        
        Args:
            *channels: 频道名称列表
            
        Returns:
            PubSub对象
        """
        if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
            return ErrorCode.SUCCESS,RedisTemplete.redis_client.subscribe(*channels)
        else:
            print(f"RedisTemplete is not init or redis_client is None")
            return ErrorCode.REDIS_CLIENT_NOT_INIT,None
    
    @staticmethod
    def subscribe_with_callback(channel: str, callback: Callable[[dict], None]):
        """
        使用回调函数订阅频道
        
        Args:
            channel: 频道名称
            callback: 回调函数，接收消息字典作为参数
            
        Returns:
            PubSub对象
        """
        if RedisTemplete.is_init and RedisTemplete.redis_client is not None:
            return ErrorCode.SUCCESS,RedisTemplete.redis_client.subscribe_with_callback(channel, callback)
        else:
            print(f"RedisTemplete is not init or redis_client is None")
            return ErrorCode.REDIS_CLIENT_NOT_INIT,None


class RedisCache:
    """
    Redis 缓存包装类
    
    替代 TTLCache，支持：
    - 自动 JSON 序列化/反序列化
    - TTL 过期时间
    - datetime、set 等特殊类型处理
    - 键前缀隔离
    """
    
    def __init__(self, redis_client: RedisClient, prefix: str = "", ttl: int = 3600):
        """
        初始化 Redis 缓存
        
        Args:
            redis_client: Redis 客户端实例
            prefix: 键前缀（用于隔离不同缓存）
            ttl: 默认过期时间（秒）
        """
        self.redis_client = redis_client
        self.prefix = prefix
        self.ttl = ttl
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的 Redis 键"""
        if self.prefix:
            return f"{self.prefix}:{key}"
        return key
    
    def _serialize(self, value: Any) -> str:
        """
        序列化值为 JSON 字符串
        
        支持 datetime、set 等特殊类型
        """
        def default_serializer(obj):
            if isinstance(obj, datetime):
                return {"__type__": "datetime", "value": obj.isoformat()}
            elif isinstance(obj, set):
                return {"__type__": "set", "value": list(obj)}
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(value, default=default_serializer, ensure_ascii=False)
    
    def _deserialize(self, data: bytes) -> Any:
        """
        反序列化 JSON 字符串
        
        自动还原 datetime、set 等特殊类型
        """
        if data is None:
            return None
        
        def object_hook(obj):
            if isinstance(obj, dict) and "__type__" in obj:
                if obj["__type__"] == "datetime":
                    return datetime.fromisoformat(obj["value"])
                elif obj["__type__"] == "set":
                    return set(obj["value"])
            return obj
        
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        return json.loads(data, object_hook=object_hook)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值（键不存在时返回）
        
        Returns:
            缓存值或默认值
        """
        try:
            redis_key = self._make_key(key)
            data = self.redis_client.get(redis_key)
            if data is None:
                return default
            return self._deserialize(data)
        except Exception as e:
            print(f"RedisCache get error: {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 则使用默认 TTL
        
        Returns:
            是否成功
        """
        try:
            redis_key = self._make_key(key)
            serialized = self._serialize(value)
            expire_time = ttl if ttl is not None else self.ttl
            self.redis_client.set_with_expire(redis_key, serialized, expire_time)
            return True
        except Exception as e:
            print(f"RedisCache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            redis_key = self._make_key(key)
            self.redis_client.delete(redis_key)
            return True
        except Exception as e:
            print(f"RedisCache delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            redis_key = self._make_key(key)
            return bool(self.redis_client.exists(redis_key))
        except Exception as e:
            print(f"RedisCache exists error: {e}")
            return False
    
    def __getitem__(self, key: str) -> Any:
        """支持 cache[key] 语法"""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持 cache[key] = value 语法"""
        self.set(key, value)
    
    def __delitem__(self, key: str) -> None:
        """支持 del cache[key] 语法"""
        self.delete(key)
    
    def __contains__(self, key: str) -> bool:
        """支持 key in cache 语法"""
        return self.exists(key)
    