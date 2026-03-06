'''
@File    :   activate_mq_api.py
@Time    :   2025/09/08 10:00:00
@Author  :   penghf 
@Version :   1.0
@Desc    :   activeMQ API
'''

from typing import Callable, Optional, Dict, Any
import threading
import time
from typing import Dict, Any
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode

try:
    import stomp
except Exception:
    stomp = None  # 延迟依赖，运行时连接时再报错，便于不使用时不强依赖

@logger()
class _StompCallbackListener:
    """简单的回调适配器，转发 STOMP 消息到用户提供的回调。"""
    def __init__(self, on_message: Callable[[str, Dict[str, Any]], None]):
        self._on_message = on_message
        self._is_registered = False  # 标记是否已注册为 listener

    def on_message(self, frame):  # type: ignore[no-redef]
        """
        仅在建立了 stomp 连接后才会实际注册为 listener
        这里提供接口定义，实际注册在 connect() 时进行
        """
        try:
            if not self._is_registered:
                self.log.warn("Listener 尚未注册，忽略消息")
                return
                
            body = getattr(frame, 'body', None)
            headers = getattr(frame, 'headers', {}) or {}
            self._on_message(body, headers)
        except Exception as e:
            # 回调内部异常不应使连接中止
            self.log.error(f"Failed to on_message: {str(e)}")
            pass
    
    def mark_as_registered(self):
        """标记 listener 已注册"""
        self._is_registered = True
        self.log.debug("Listener 已标记为注册状态")
    
    def mark_as_unregistered(self):
        """标记 listener 已取消注册"""
        self._is_registered = False
        self.log.debug("Listener 已标记为未注册状态")


@logger()
class _ReceiptListener:
    """回执监听器，处理STOMP回执消息"""
    def __init__(self, api_instance):
        self.api = api_instance
        self._is_registered = False

    def on_receipt(self, frame):  # type: ignore[no-redef]
        """处理回执消息"""
        try:
            if not self._is_registered:
                self.log.warn("Receipt Listener 尚未注册，忽略回执")
                return
                
            headers = getattr(frame, 'headers', {}) or {}
            receipt_id = headers.get('receipt-id')
            if receipt_id:
                # 检查是否有错误信息
                success = True
                if 'error' in headers:
                    success = False
                    self.log.error(f"回执包含错误: {headers.get('error')}")
                
                self.api._handle_receipt(receipt_id, success)
                self.log.debug(f"处理回执: {receipt_id}, 成功: {success}")
            else:
                self.log.warn("收到回执但缺少receipt-id")
        except Exception as e:
            self.log.error(f"处理回执失败: {e}")
    
    def mark_as_registered(self):
        """标记 listener 已注册"""
        self._is_registered = True
        self.log.debug("Receipt Listener 已标记为注册状态")
    
    def mark_as_unregistered(self):
        """标记 listener 已取消注册"""
        self._is_registered = False
        self.log.debug("Receipt Listener 已标记为未注册状态")


@logger()
class ActivateMQApi:
    def __init__(self, config: Dict[str, Any]):
        '''
        Args:
            config: 配置
                方式1 - URL格式（推荐）:
                    url: "stomp://username:password@host:port"  # 例如: "stomp://admin:admin@0.0.0.0:61613"
                方式2 - 分别配置:
                    host: 主机地址 (默认: 127.0.0.1)
                    port: 端口号 (默认: 61613)
                    username: 用户名 (默认: admin)
                    password: 密码 (默认: admin)
                queue: 队列名称
        '''
        self.config = config or {}
        self._connection: Optional["stomp.Connection"] = None  # type: ignore[name-defined]
        self._subscriptions: Dict[str, str] = {}
        self._listener_lock = threading.Lock()
        self._pending_listeners = {}  # 存储待注册的 listener
        self._is_connected = False  # 连接状态标记
        self.device_sn = ""
        self._receipt_callbacks: Dict[str, Callable[[str, bool], None]] = {}  # 存储回执回调
        self._receipt_listener: Optional[_ReceiptListener] = None  # 回执监听器
        self._receipt_timeouts: Dict[str, float] = {}  # 存储回执超时时间
    '''
    检查是否安装stomp.py
    '''
    def _require_stomp(self) -> None:
        if stomp is None:
            raise ImportError(
                "未安装 stomp.py，请在 requirements 中添加 'stomp.py' 并安装，或在运行环境中执行: pip install stomp.py"
            )
    '''
    获取主机和端口
    Returns:
        tuple[str, int]: 主机和端口
    '''
    def _get_host_port(self) -> tuple[str, int]:
        # 支持 stomp:// URL 格式配置
        url = self.config.get('url', '')
        if url and url.startswith('stomp://'):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.hostname or '127.0.0.1'
                port = parsed.port or 61613
                self.log.info(f"使用 STOMP URL 配置: {url} -> {host}:{port}")
                return host, port
            except Exception as e:
                self.log.warn(f"解析 STOMP URL 失败: {url}, 错误: {e}, 使用默认配置")
        
        # 使用传统的 host 和 port 配置
        host = self.config.get('host', '127.0.0.1')
        port = int(self.config.get('port', 61613))
        self.log.info(f"使用传统配置: {host}:{port}")
        return host, port
    '''
    获取认证信息
    Returns:
        tuple[str, str]: 用户名和密码
    '''
    def _get_auth(self) -> tuple[str, str]:
        # 支持从 stomp:// URL 中解析认证信息
        url = self.config.get('url', '')
        if url and url.startswith('stomp://'):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if parsed.username and parsed.password:
                    self.log.info(f"使用 STOMP URL 中的认证信息: {parsed.username}")
                    return parsed.username, parsed.password
            except Exception as e:
                self.log.warn(f"解析 STOMP URL 认证信息失败: {url}, 错误: {e}, 使用默认配置")
        
        # 使用传统的 username 和 password 配置
        username = self.config.get('username', 'admin')
        password = self.config.get('password', 'admin')
        self.log.info(f"使用传统认证配置: {username}")
        return username, password
    '''
    标准化目的地
    Args:
        name_or_path: 目的地
    Returns:
        str: 标准化后的目的地
    '''
    def _normalize_destination(self, name_or_path: str) -> str:        
        if not self.device_sn:
            self.device_sn = self._get_device_sn()
        
        dest = str(name_or_path or '').strip()
        if dest.startswith('/queue/') or dest.startswith('/topic/'):
            return f"{dest}/{self.device_sn}"
        # 默认按队列前缀
        return f"/queue/{dest}/{self.device_sn}"
    
    def _get_device_sn(self) -> str:
        """获取设备序列号"""
        default_sn = "parking_mng_unit_1"
        url = "https://127.0.0.1:50103/nocos/nocos/configure/config"
        
        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                self.log.warn(f"API error: {data.get('message', 'Unknown error')}")
                return default_sn

            # 安全提取 sn
            sn = (
                data.get("data", {})
                .get("device", {})
                .get("GW", {})
                .get("sn")
            )
            
            if sn:
                self.log.info(f"成功获取设备序列号: {sn}")
                return sn
            else:
                self.log.warn("API返回的设备序列号为空，使用默认值")
                return default_sn

        except requests.exceptions.RequestException as e:
            self.log.error(f"获取设备序列号网络错误: {e}")
            return default_sn
        except Exception as e:
            self.log.error(f"获取设备序列号解析失败: {e}")
            return default_sn

    '''
    检查是否连接
    Returns:
        bool: 是否连接
    '''
    def is_connected(self) -> bool:
        return bool(self._connection and self._connection.is_connected())

    '''
    连接activeMQ
    Args:
        wait: 等待时间
    '''
    def connect(self, wait: float = 2.0):
        try:
            self._require_stomp()
            if self.is_connected():
                return ErrorCode.SUCCESS
            host, port = self._get_host_port()
            self._connection = stomp.Connection(host_and_ports=[(host, port)])
            username, password = self._get_auth()
            self._connection.connect(username=username, passcode=password, wait=True)
            # 给 broker 一点时间稳定连接（部分环境需要）
            if wait and wait > 0:
                time.sleep(min(wait, 3.0))
            
            # 连接成功后，注册回执监听器
            self._receipt_listener = _ReceiptListener(self)
            self._connection.set_listener("receipt", self._receipt_listener)
            self._receipt_listener.mark_as_registered()
            
            # 注册所有待注册的 listener
            self._is_connected = True
            self._register_pending_listeners()
            
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"Failed to connect to ActiveMQ: {str(e)}")
            self._is_connected = False
            return ErrorCode.ACTIVEMQ_CONNECTION_ERROR

    '''
    断开activeMQ连接
    '''
    def disconnect(self) -> ErrorCode:
        if self._connection is not None:
            try:
                if self._connection.is_connected():
                    self._connection.disconnect()
                return ErrorCode.SUCCESS
            except Exception as e:
                self.log.error(f"Failed to disconnect from ActiveMQ: {str(e)}")
                return ErrorCode.ACTIVEMQ_CONNECTION_ERROR
            finally:
                self._connection = None
                self._subscriptions.clear()
                self._is_connected = False
                # 清理回执监听器
                if self._receipt_listener:
                    self._receipt_listener.mark_as_unregistered()
                    self._receipt_listener = None
                # 清空回执回调
                self._receipt_callbacks.clear()
                # 标记所有 listener 为未注册状态
                self._mark_all_listeners_unregistered()
    '''
    发布消息
    Args:
        destination: 目的地
        message: 消息
        headers: 头信息
        receipt: 是否请求回执
        receipt_callback: 回执回调函数
    '''
    def publish(self, destination: str, message: str, headers: Optional[Dict[str, Any]] = None, 
                receipt: bool = False, receipt_callback: Optional[Callable[[str, bool], None]] = None,
                receipt_timeout: float = 10.0):
        try:
            if not self.is_connected():
                self.connect()
            assert self._connection is not None
            dest = self._normalize_destination(destination)
            
            # 准备消息头
            message_headers = headers or {}
            
            # 如果需要回执，添加receipt头
            if receipt:
                import uuid
                import time
                receipt_id = str(uuid.uuid4())
                message_headers['receipt'] = receipt_id
                
                # 如果提供了回调函数，注册回执监听器
                if receipt_callback:
                    self._register_receipt_callback(receipt_id, receipt_callback)
                    # 设置超时时间
                    self._receipt_timeouts[receipt_id] = time.time() + receipt_timeout
            
            self.log.info(f"publish message to ActiveMQ: {dest}, receipt: {receipt}")
            self._connection.send(destination=dest, body=message, headers=message_headers)
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"Failed to publish message to ActiveMQ: {str(e)}")
            return ErrorCode.ACTIVEMQ_PUBLISH_ERROR

    '''
    订阅目标目的地，消息通过 callback(body, headers) 回调。
    Args:
        destination: 目的地
        callback: 回调
        ack: 确认方式
        subscription_id: 订阅ID
    Returns:
        str: 订阅ID
    '''
    def subscribe(self,
                  destination: str,
                  callback: Callable[[str, Dict[str, Any]], None],
                  ack: str = 'auto',
                  subscription_id: Optional[str] = None) -> str:
        """订阅目标目的地，消息通过 callback(body, headers) 回调。

        返回值为订阅 ID，可用于取消订阅。
        """
        dest = self._normalize_destination(destination)
        
        # 为该订阅设置独立的 listener
        listener = _StompCallbackListener(callback)
        with self._listener_lock:
            lid = subscription_id or f"sub-{dest}-{len(self._subscriptions)+1}"
            
            # 如果已连接，立即注册 listener
            if self._is_connected and self._connection is not None:
                self._connection.set_listener(lid, listener)  # type: ignore[arg-type]
                self._connection.subscribe(destination=dest, id=lid, ack=ack)
                listener.mark_as_registered()
                self.log.info(f"Listener 已立即注册: {lid}")
            else:
                # 如果未连接，先存储到待注册列表
                self._pending_listeners[lid] = {
                    'listener': listener,
                    'destination': dest,
                    'ack': ack
                }
                self.log.info(f"Listener 已加入待注册列表: {lid}")
            
            self._subscriptions[lid] = dest
            return lid

    '''
    取消订阅
    Args:
        subscription_id: 订阅ID
    '''
    def unsubscribe(self, subscription_id: str) -> None:
        if not subscription_id:
            return
        if not self.is_connected():
            self._subscriptions.pop(subscription_id, None)
            return
        assert self._connection is not None
        try:
            self._connection.unsubscribe(id=subscription_id)
        finally:
            # 移除 listener
            try:
                self._connection.remove_listener(subscription_id)  # type: ignore[attr-defined]
            except Exception:
                pass
            self._subscriptions.pop(subscription_id, None)
    
    def _register_pending_listeners(self):
        """
        注册所有待注册的 listener
        仅在 STOMP 连接建立后调用
        """
        if not self._is_connected or self._connection is None:
            self.log.warn("连接未建立，无法注册待注册的 listener")
            return
        
        with self._listener_lock:
            for lid, listener_info in self._pending_listeners.items():
                try:
                    listener = listener_info['listener']
                    destination = listener_info['destination']
                    ack = listener_info['ack']
                    
                    # 注册 listener
                    self._connection.set_listener(lid, listener)  # type: ignore[arg-type]
                    self._connection.subscribe(destination=destination, id=lid, ack=ack)
                    listener.mark_as_registered()
                    
                    self.log.info(f"待注册的 listener 已注册: {lid}")
                except Exception as e:
                    self.log.error(f"注册待注册的 listener 失败: {lid}, 错误: {e}")
            
            # 清空待注册列表
            self._pending_listeners.clear()
            self.log.info("所有待注册的 listener 已处理完成")
    
    def _mark_all_listeners_unregistered(self):
        """
        标记所有 listener 为未注册状态
        在断开连接时调用
        """
        with self._listener_lock:
            # 标记待注册列表中的 listener
            for lid, listener_info in self._pending_listeners.items():
                listener = listener_info['listener']
                listener.mark_as_unregistered()
            
            # 清空待注册列表
            self._pending_listeners.clear()
            self.log.info("所有 listener 已标记为未注册状态")
    
    def get_pending_listeners_count(self) -> int:
        """
        获取待注册的 listener 数量
        
        Returns:
            int: 待注册的 listener 数量
        """
        with self._listener_lock:
            return len(self._pending_listeners)
    
    def get_registered_listeners_count(self) -> int:
        """
        获取已注册的 listener 数量
        
        Returns:
            int: 已注册的 listener 数量
        """
        with self._listener_lock:
            return len(self._subscriptions) - len(self._pending_listeners)
    
    def _register_receipt_callback(self, receipt_id: str, callback: Callable[[str, bool], None]):
        """
        注册回执回调函数
        
        Args:
            receipt_id: 回执ID
            callback: 回调函数，参数为(receipt_id, success)
        """
        with self._listener_lock:
            self._receipt_callbacks[receipt_id] = callback
            self.log.debug(f"注册回执回调: {receipt_id}")
    
    def _handle_receipt(self, receipt_id: str, success: bool = True):
        """
        处理回执消息
        
        Args:
            receipt_id: 回执ID
            success: 是否成功
        """
        with self._listener_lock:
            if receipt_id in self._receipt_callbacks:
                callback = self._receipt_callbacks.pop(receipt_id)
                try:
                    callback(receipt_id, success)
                    self.log.debug(f"执行回执回调: {receipt_id}, 成功: {success}")
                except Exception as e:
                    self.log.error(f"回执回调执行失败: {receipt_id}, 错误: {e}")
            else:
                self.log.warn(f"未找到回执回调: {receipt_id}")
    
    def check_receipt_timeouts(self):
        """
        检查超时的回执
        应该在定期任务中调用此方法
        """
        import time
        current_time = time.time()
        timeout_receipts = []
        
        with self._listener_lock:
            for receipt_id, timeout_time in self._receipt_timeouts.items():
                if current_time > timeout_time:
                    timeout_receipts.append(receipt_id)
            
            # 处理超时的回执
            for receipt_id in timeout_receipts:
                if receipt_id in self._receipt_callbacks:
                    callback = self._receipt_callbacks.pop(receipt_id)
                    try:
                        callback(receipt_id, False)  # 超时视为失败
                        self.log.warn(f"回执超时: {receipt_id}")
                    except Exception as e:
                        self.log.error(f"超时回执回调执行失败: {receipt_id}, 错误: {e}")
                
                # 清理超时记录
                self._receipt_timeouts.pop(receipt_id, None)

    