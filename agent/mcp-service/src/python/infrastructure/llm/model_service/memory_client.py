import time
import json
import hashlib
import requests
from typing import Any, Dict, List, Optional, Tuple
from infrastructure.common.error.errcode import ErrorCode, is_success
from infrastructure.common.logging.logging import logger, init_logging
from infrastructure.client.redis_client import RedisClient, RedisCache


@logger()
class MemoryClient:
    """
    记忆客户端
    - 短期记忆、上下文、工具记忆: 使用 Redis 存储
    - 长期记忆: 使用远程 API (向量数据库)
    """
    
    # Redis Key 前缀
    PREFIX_SHORT_TERM = "memory:short_term"      # 短期记忆
    PREFIX_CONTEXT = "memory:context"            # 对话上下文
    PREFIX_TOOL = "memory:tool"                  # 工具结果缓存
    
    # 默认过期时间 (秒)
    TTL_SHORT_TERM = 3600       # 短期记忆: 1小时
    TTL_CONTEXT = 3600          # 上下文: 1小时
    TTL_TOOL = 3600             # 工具结果: 1小时
    MAX_CONTEXT_MESSAGES = 20   # 最大上下文消息数
    
    def __init__(self, config: Dict[str, Any], redis_client: RedisClient = None):
        self.log.info(f"memory client config = {config}")
        self.config = config
        self.redis_client = redis_client
        self.is_initialized = False
        self.session = requests.Session()
        
        # 远程 API 配置 (用于长期记忆)
        self.base_url = config.get("url", "")
        self.uris = config.get("uris", {})
        self.api_key = config.get("api_key", "")
        
        # 初始化 Redis 缓存
        if self.redis_client:
            self.short_term_cache = RedisCache(redis_client, prefix=self.PREFIX_SHORT_TERM, ttl=self.TTL_SHORT_TERM)
            self.context_cache = RedisCache(redis_client, prefix=self.PREFIX_CONTEXT, ttl=self.TTL_CONTEXT)
            self.tool_cache = RedisCache(redis_client, prefix=self.PREFIX_TOOL, ttl=self.TTL_TOOL)
            self.is_initialized = True
            self.log.info("MemoryClient initialized with Redis storage")
        else:
            self.log.warning("Redis client not provided, using remote API for all memory operations")
            self.init_memory()
    
    def init_memory(self) -> ErrorCode:
        """初始化远程记忆服务 (用于长期记忆)"""
        try:
            self.log.info(f"init memory via remote API")
            if not self.base_url or not self.uris.get("health"):
                self.log.warning("Remote memory service not configured")
                return ErrorCode.SUCCESS
            result = self._post(self.uris.get("health"), {}, timeout=180)
            if result is None or result.get("status_code") != 200:
                self.log.error(f"status:init memory failed,result={result}")
                return ErrorCode.INIT_MEMORY_FAILURE
            self.is_initialized = True
            self.log.info(f"init memory success,result={result}")
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"init memory except,{e}")
            return ErrorCode.INIT_MEMORY_FAILURE
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头，包含认证信息"""
        headers = {"Content-Type": "application/json"}
        if self.api_key != "" and self.api_key is not None:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def _post(self, endpoint: str, data: Dict[str, Any] = None, timeout: int = 60) -> Dict[str, Any]:
        """发送 POST 请求，返回结果包含响应时间"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        try:
            response = self.session.post(
                url,
                json=data or {},
                timeout=timeout,
                headers=self._get_headers()
            )
            elapsed_ms = (time.time() - start_time) * 1000
            
            response_data = response.json() if response.content else {}
            
            # 调试日志：检查 400 错误
            if response.status_code >= 400:
                self.log.error(f"HTTP {response.status_code} for {endpoint}: {response_data}")
            
            # 返回时根据状态码和响应体判断业务成功
            is_success = response.status_code == 200 and response_data.get("success", True)
            
            return {
                "status_code": response.status_code,
                "data": response_data.get("data") if isinstance(response_data, dict) else response_data,
                "success": is_success,
                "message": response_data.get("message", ""),
                "elapsed_ms": elapsed_ms
            }
        except requests.exceptions.Timeout:
            elapsed_ms = (time.time() - start_time) * 1000
            return {"success": False, "error": "请求超时", "elapsed_ms": elapsed_ms}
        except requests.exceptions.ConnectionError:
            elapsed_ms = (time.time() - start_time) * 1000
            return {"success": False, "error": "连接失败，请确保服务已启动", "elapsed_ms": elapsed_ms}
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return {"success": False, "error": str(e), "elapsed_ms": elapsed_ms}
    
    def _get_session_id(self, message: Dict[str, Any]) -> str:
        """从消息中获取 session_id，默认为 'default'"""
        return message.get("session_id", "default")
    
    def _generate_tool_key(self, tool_name: str, input_data: Dict[str, Any]) -> str:
        """生成工具缓存的唯一 key"""
        # 对输入参数进行哈希，确保相同输入得到相同的 key
        input_str = json.dumps(input_data, sort_keys=True, ensure_ascii=False)
        input_hash = hashlib.md5(input_str.encode()).hexdigest()[:12]
        return f"{tool_name}:{input_hash}"
    
    # ==================== 长期记忆 (使用远程 API) ====================
    
    def search_long_term(self, query_json: Dict[str, Any]) -> Tuple[ErrorCode, List[str]]:
        '''搜索长期记忆 - POST /intelligence/memory/search'''
        try:
            self.log.info(f"search long term query={query_json}")
            result = self._post(self.uris.get("search_long_term"), query_json, timeout=180)
            if result is None or result.get("status_code") != 200:
                self.log.error(f"status:search long term failed,result={result}")
                return ErrorCode.SEARCH_LONG_TERM_FAILURE, []
            self.log.info(f"search long term success,result={result}")
            return ErrorCode.SUCCESS, result.get("data", [])
        except Exception as e:
            self.log.error(f"search long term except,{e}")
            return ErrorCode.SEARCH_LONG_TERM_FAILURE, []
    
    def add_long_term(self, text_json: Dict[str, Any]) -> ErrorCode:
        '''添加长期记忆'''
        try:
            self.log.info(f"add long term text_json={text_json}")
            result = self._post(self.uris.get("add_long_term"), text_json, timeout=180)
            if result is None or result.get("status_code") != 200:
                self.log.error(f"status:add long term failed,result={result}")
                return ErrorCode.ADD_LONG_TERM_FAILURE
            self.log.info(f"add long term success,result={result}")
            return ErrorCode.SUCCESS
        except Exception as e:
            self.log.error(f"add long term except,{e}")
            return ErrorCode.ADD_LONG_TERM_FAILURE
    
    # ==================== 短期记忆 (使用 Redis) ====================
    
    def update_short_term(self, message: Dict[str, Any]) -> ErrorCode:
        '''
        更新短期记忆 - 使用 Redis 存储
        
        Args:
            message: 消息字典，包含:
                - session_id: 会话ID
                - role: 角色 (user/assistant/system)
                - content: 消息内容
        '''
        try:
            session_id = self._get_session_id(message)
            self.log.info(f"update short term session_id={session_id}, message={message}")
            
            if not self.redis_client:
                # 回退到远程 API
                result = self._post(self.uris.get("update_short_term"), message, timeout=180)
                if result is None or result.get("status_code") != 200:
                    self.log.error(f"status:update short term failed,result={result}")
                    return ErrorCode.UPDATE_SHORT_TERM_FAILURE
                return ErrorCode.SUCCESS
            
            # 使用 Redis 存储
            key = f"{session_id}:messages"
            messages = self.short_term_cache.get(key, default=[])
            
            # 添加新消息
            new_message = {
                "role": message.get("role", "user"),
                "content": message.get("content", ""),
                "timestamp": time.time()
            }
            messages.append(new_message)
            
            # 限制消息数量
            if len(messages) > self.MAX_CONTEXT_MESSAGES:
                messages = messages[-self.MAX_CONTEXT_MESSAGES:]
            
            self.short_term_cache.set(key, messages)
            self.log.info(f"update short term success, total messages={len(messages)}")
            return ErrorCode.SUCCESS
            
        except Exception as e:
            self.log.error(f"update short term except,{e}")
            return ErrorCode.UPDATE_SHORT_TERM_FAILURE
    
    def get_conversation_context(self, query_json: Dict[str, Any]) -> Tuple[ErrorCode, List[Dict]]:
        '''
        获取对话上下文 - 使用 Redis 存储
        
        Args:
            query_json: 查询参数，包含:
                - session_id: 会话ID
                - k: 返回最近k条消息 (可选，默认10)
        
        Returns:
            (ErrorCode, List[Dict]): 错误码和消息列表
        '''
        try:
            session_id = query_json.get("session_id", "default")
            k = query_json.get("k", 10)
            self.log.info(f"get conversation context session_id={session_id}, k={k}")
            
            # 从 Redis 获取
            key = f"{session_id}:messages"
            messages = self.short_term_cache.get(key, default=[])
            
            # 返回最近 k 条消息
            recent_messages = messages[-k:] if len(messages) > k else messages
            self.log.info(f"get conversation context success, returned {len(recent_messages)} messages")
            return ErrorCode.SUCCESS, recent_messages
            
        except Exception as e:
            self.log.error(f"get conversation context except,{e}")
            return ErrorCode.GET_CONVERSATION_CONTEXT_FAILURE, []
    
    def clear_short_term(self, session_id: str = None) -> ErrorCode:
        '''
        清除短期记忆 - 使用 Redis 存储
        
        Args:
            session_id: 会话ID，如果为None则清除默认会话
        '''
        try:
            session_id = session_id or "default"
            self.log.info(f"clear short term session_id={session_id}")
            
            # 从 Redis 删除
            key = f"{session_id}:messages"
            self.short_term_cache.delete(key)
            self.log.info(f"clear short term success")
            return ErrorCode.SUCCESS
            
        except Exception as e:
            self.log.error(f"clear short term except,{e}")
            return ErrorCode.CLEAR_SHORT_TERM_FAILURE
    
    # ==================== 工具记忆 (使用 Redis) ====================
    
    def save_tool_result(self, tool_name: str, input_data: Dict[str, Any], output: str) -> ErrorCode:
        '''
        保存工具执行结果 - 使用 Redis 缓存
        
        Args:
            tool_name: 工具名称
            input_data: 输入参数
            output: 执行结果
        '''
        try:
            self.log.info(f"save tool result tool_name={tool_name}, input_data={input_data}")
            
            # 使用 Redis 存储
            key = self._generate_tool_key(tool_name, input_data)
            cache_data = {
                "tool_name": tool_name,
                "input_data": input_data,
                "output": output,
                "timestamp": time.time()
            }
            self.tool_cache.set(key, cache_data)
            self.log.info(f"save tool result success, key={key}")
            return ErrorCode.SUCCESS
            
        except Exception as e:
            self.log.error(f"save tool result except,{e}")
            return ErrorCode.SAVE_TOOL_RESULT_FAILURE
    
    def get_tool_memory(self, tool_name: str, input_data: Dict[str, Any]) -> Tuple[ErrorCode, Optional[str]]:
        '''
        获取工具记忆 (缓存的执行结果) - 使用 Redis 缓存
        
        Args:
            tool_name: 工具名称
            input_data: 输入参数
        
        Returns:
            (ErrorCode, Optional[str]): 错误码和缓存的输出结果
        '''
        try:
            self.log.info(f"get tool memory tool_name={tool_name}, input_data={input_data}")
            
            if not self.redis_client:
                # 回退到远程 API
                result = self._post(
                    self.uris.get("get_tool_memory"),
                    {"tool_name": tool_name, "input_data": input_data},
                    timeout=180
                )
                if result is None or result.get("status_code") != 200:
                    self.log.error(f"status:get tool memory failed,result={result}")
                    return ErrorCode.GET_TOOL_MEMORY_FAILURE, None
                return ErrorCode.SUCCESS, result.get("data", {}).get("output")
            
            # 从 Redis 获取
            key = self._generate_tool_key(tool_name, input_data)
            cache_data = self.tool_cache.get(key)
            
            if cache_data is None:
                self.log.info(f"tool memory not found, key={key}")
                return ErrorCode.SUCCESS, None
            
            output = cache_data.get("output")
            self.log.info(f"get tool memory success, key={key}")
            return ErrorCode.SUCCESS, output
            
        except Exception as e:
            self.log.error(f"get tool memory except,{e}")
            return ErrorCode.GET_TOOL_MEMORY_FAILURE, None
    
    # ==================== 辅助方法 ====================
    
    def get_all_context_for_llm(self, session_id: str = "default", k: int = 10) -> List[Dict[str, str]]:
        '''
        获取适合传给 LLM 的上下文格式
        
        Returns:
            List[Dict]: [{"role": "user", "content": "..."}, ...]
        '''
        err_code, messages = self.get_conversation_context({"session_id": session_id, "k": k})
        if not is_success(err_code):
            return []
        
        # 转换为 LLM 格式 (去掉 timestamp)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]
