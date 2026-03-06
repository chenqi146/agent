import asyncio
import threading
import time
import requests
from typing import Optional
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig


@logger()
class DevOpsRunner:
    """
    DevOps 运行器 - 负责后台运维任务
    - Nacos 心跳维持
    - 健康检查
    - 监控指标上报
    """

    def __init__(self, config: SysConfig):
        self.config = config
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._nacos_instance_id: Optional[str] = None
        
        # Nacos 配置
        system_cfg = config.get_system_config() or {}
        self.nacos_cfg = system_cfg.get("nacos", {})
        self.nacos_enabled = self.nacos_cfg.get("enabled", False)
        
        if self.nacos_enabled:
            self.nacos_server_addr = self.nacos_cfg.get("server_addr", "127.0.0.1:8848")
            self.nacos_namespace = self.nacos_cfg.get("namespace", "public")
            self.nacos_group = self.nacos_cfg.get("group", "DEFAULT_GROUP")
            self.nacos_service_name = self.nacos_cfg.get("service_name", "pg-agent-application")
            self.nacos_weight = self.nacos_cfg.get("weight", 1.0)
            self.nacos_ephemeral = self.nacos_cfg.get("ephemeral", True)
            
            # 服务配置
            server_cfg = config.get_server_config() or {}
            self.service_ip = server_cfg.get("address", "127.0.0.1")
            self.service_port = server_cfg.get("port", 19093)
            
            # 如果是 0.0.0.0，注册时使用 127.0.0.1 或实际 IP
            if self.service_ip == "0.0.0.0":
                self.service_ip = "127.0.0.1"

    def start_heartbeat(self):
        """启动心跳线程"""
        if not self.nacos_enabled:
            self.log.info("Nacos heartbeat disabled")
            return

        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self.log.warning("Heartbeat thread already running")
            return

        self._stop_event.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            name="nacos-heartbeat",
            daemon=True
        )
        self._heartbeat_thread.start()
        self.log.info(f"Nacos heartbeat thread started for service {self.nacos_service_name}")

    def stop_heartbeat(self):
        """停止心跳线程"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._stop_event.set()
            self._heartbeat_thread.join(timeout=5.0)
            self.log.info("Nacos heartbeat thread stopped")

    def _heartbeat_worker(self):
        """心跳工作线程"""
        self.log.info("Starting Nacos heartbeat worker")
        
        # 心跳间隔（秒）
        heartbeat_interval = self.nacos_cfg.get("heartbeat_interval", 30)
        
        while not self._stop_event.is_set():
            try:
                # 发送心跳
                self._send_heartbeat()
                
                # 等待下一次心跳
                if self._stop_event.wait(heartbeat_interval):
                    break
                    
            except Exception as e:
                self.log.error(f"Heartbeat worker error: {e}")
                # 出错时等待较短时间后重试
                if self._stop_event.wait(5):
                    break

        self.log.info("Nacos heartbeat worker stopped")

    def _send_heartbeat(self):
        """发送心跳到 Nacos"""
        try:
            # 构造心跳请求参数
            params = {
                "serviceName": self.nacos_service_name,
                "ip": self.service_ip,
                "port": self.service_port,
                "namespaceId": self.nacos_namespace,
                "groupName": self.nacos_group,
                "weight": self.nacos_weight,
                "healthy": "true",
                "enabled": "true",
                "ephemeral": "true" if self.nacos_ephemeral else "false",
            }
            
            # 如果有实例ID，添加到参数中
            if self._nacos_instance_id:
                params["instanceId"] = self._nacos_instance_id

            url = f"http://{self.nacos_server_addr}/nacos/v1/ns/instance"
            response = requests.put(url, params=params, timeout=5)
            
            if response.status_code == 200:
                if not self._nacos_instance_id:
                    # 第一次心跳成功，保存实例ID
                    response_data = response.text
                    if response_data:
                        self._nacos_instance_id = response_data
                        self.log.info(f"Nacos heartbeat established, instance ID: {self._nacos_instance_id}")
            else:
                self.log.warning(f"Nacos heartbeat failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            self.log.warning("Nacos heartbeat timeout")
        except requests.exceptions.ConnectionError:
            self.log.warning("Nacos heartbeat connection failed")
        except Exception as e:
            self.log.error(f"Nacos heartbeat error: {e}")

    def get_service_status(self) -> dict:
        """获取服务状态信息"""
        return {
            "nacos_enabled": self.nacos_enabled,
            "nacos_server": self.nacos_server_addr if self.nacos_enabled else None,
            "nacos_service": self.nacos_service_name if self.nacos_enabled else None,
            "nacos_instance_id": self._nacos_instance_id if self.nacos_enabled else None,
            "heartbeat_running": self._heartbeat_thread.is_alive() if self._heartbeat_thread else False,
            "service_ip": self.service_ip,
            "service_port": self.service_port,
        }

    def __del__(self):
        """析构函数 - 确保心跳线程停止"""
        try:
            self.stop_heartbeat()
        except Exception:
            pass
