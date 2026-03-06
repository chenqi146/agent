import asyncio
import re
from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
import hashlib

from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode


@logger()
class FastTextClient:
    """
    FastText轻量级意图分类客户端
    用于快速粗分类（<5ms），配合Neo4j进行精确意图识别
    """
    
    # 预定义意图关键词库（可扩展为从配置/数据库加载）
    INTENT_KEYWORDS = {
        "city_parking": [
            "停车", "车位", "停车场", "泊位", "收费", "缴费", "停车管理",
            "停车位", "停车难", "停车费用", "停车时间", "parking", "park"
        ],
        "steward": [
            "管家", "监控", "报警", "告警", "巡逻", "巡查", "巡检",
            "车牌", "识别", "取证", "证据", "外部服务", "steward", "monitor"
        ],
        "vehicle_query": [
            "车辆", "车", "车牌号", "查询车辆", "找车", "那辆车", "这辆车",
            "vehicle", "car", "plate", "query vehicle"
        ],
        "data_analysis": [
            "分析", "统计", "报表", "图表", "趋势", "数据分析", "数据报告",
            "analytics", "statistics", "report", "chart"
        ],
        "task_management": [
            "任务", "工单", "分配", "处理", "待办", "create task", "task"
        ]
    }
    
    # 指代词映射用于上下文解析
    REFERENCE_PATTERNS = {
        "vehicle": ["车", "车辆", "那辆车", "这辆车", "该车", "车子", "该车辆"],
        "parking_spot": ["车位", "泊位", "停车位", "该车位", "那个车位"],
        "task": ["任务", "工单", "该任务", "这个任务"]
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._keyword_cache = {}  # 缓存分词结果
        self._reference_cache = {}
        self.log.info("FastTextClient initialized")
    
    def _tokenize(self, text: str) -> List[str]:
        """简单中文分词（可替换为jieba等）"""
        # 去除标点，保留中英文数字
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        # 按空格分割
        tokens = [t.strip() for t in text.split() if t.strip()]
        
        # 生成n-gram（1-gram和2-gram用于匹配）
        ngrams = tokens.copy()
        for i in range(len(tokens) - 1):
            bigram = tokens[i] + tokens[i+1]
            ngrams.append(bigram)
        
        return ngrams
    
    def _calculate_similarity(self, text: str, keywords: List[str]) -> float:
        """计算文本与关键词集合的相似度"""
        tokens = self._tokenize(text)
        if not tokens:
            return 0.0
        
        # 统计匹配的关键词
        matches = 0
        token_set = set(tokens)
        
        for keyword in keywords:
            keyword_tokens = self._tokenize(keyword)
            for kt in keyword_tokens:
                if any(kt in t or t in kt for t in token_set):
                    matches += 1
                    break
        
        # 计算加权得分
        keyword_coverage = matches / len(keywords) if keywords else 0
        token_coverage = sum(1 for t in tokens if any(kw in t for kw in keywords)) / len(tokens)
        
        return (keyword_coverage * 0.6 + token_coverage * 0.4)
    
    async def classify_intent(self, query: str, top_k: int = 3) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        FastText第一阶段：快速意图分类
        
        Args:
            query: 用户查询文本
            top_k: 返回Top-K候选意图
            
        Returns:
            (ErrorCode, [{"intent": str, "confidence": float, "matched_keywords": []}])
        """
        try:
            # 缓存检查
            cache_key = hashlib.md5(query.encode()).hexdigest()[:16]
            if cache_key in self._keyword_cache:
                return ErrorCode.SUCCESS, self._keyword_cache[cache_key]
            
            # 计算各意图相似度
            intent_scores = []
            for intent, keywords in self.INTENT_KEYWORDS.items():
                score = self._calculate_similarity(query, keywords)
                # 提取匹配的关键词
                matched = [kw for kw in keywords if kw in query or any(kw in t for t in self._tokenize(query))]
                intent_scores.append({
                    "intent": intent,
                    "confidence": min(score * 1.5, 1.0),  # 放大得分并限制在1.0内
                    "matched_keywords": matched[:5],  # 最多返回5个匹配词
                    "score": score
                })
            
            # 按置信度排序
            intent_scores.sort(key=lambda x: x["confidence"], reverse=True)
            
            # 返回Top-K
            result = intent_scores[:top_k]
            
            # 缓存结果（简单LRU）
            if len(self._keyword_cache) > 1000:
                self._keyword_cache.clear()
            self._keyword_cache[cache_key] = result
            
            self.log.debug(f"FastText classification: {query[:30]}... -> {result[0]['intent']} ({result[0]['confidence']:.3f})")
            return ErrorCode.SUCCESS, result
            
        except Exception as e:
            self.log.error(f"FastText classification failed: {e}")
            return ErrorCode.SYSTEM_ERROR, [{"intent": "unknown", "confidence": 0.0, "matched_keywords": [], "score": 0.0}]
    
    def detect_reference_type(self, query: str) -> Tuple[ErrorCode, Dict[str, Any]]:
        """
        检测查询中的指代类型
        
        Returns:
            (ErrorCode, {"reference_type": str, "confidence": float, "matched_terms": []})
        """
        try:
            query_lower = query.lower()
            
            # 检查各类指代词
            type_scores = {}
            for ref_type, patterns in self.REFERENCE_PATTERNS.items():
                matches = [p for p in patterns if p in query or p in query_lower]
                if matches:
                    type_scores[ref_type] = len(matches)
            
            if not type_scores:
                return ErrorCode.SUCCESS, {"reference_type": "none", "confidence": 0.0, "matched_terms": []}
            
            # 选择得分最高的类型
            best_type = max(type_scores.items(), key=lambda x: x[1])
            matched = [p for p in self.REFERENCE_PATTERNS[best_type[0]] if p in query or p in query_lower]
            
            result = {
                "reference_type": best_type[0],
                "confidence": min(best_type[1] * 0.3, 1.0),
                "matched_terms": matched
            }
            
            return ErrorCode.SUCCESS, result
            
        except Exception as e:
            self.log.error(f"Reference detection failed: {e}")
            return ErrorCode.SYSTEM_ERROR, {"reference_type": "none", "confidence": 0.0, "matched_terms": [], "error": str(e)}
    
    async def resolve_reference(
        self, 
        query: str, 
        dialogue_history: List[Dict[str, Any]], 
        confirmed_slots: Dict[str, Any]
    ) -> Tuple[ErrorCode, Dict[str, Any]]:
        """
        解析查询中的指代词（如"那辆车"）
        
        Args:
            query: 当前查询
            dialogue_history: 对话历史
            confirmed_slots: 已确认的槽位
            
        Returns:
            (ErrorCode, {"resolved_entity": str, "entity_type": str, "entity_value": Any})
        """
        try:
            # 检测指代类型
            err, ref_info = self.detect_reference_type(query)
            if err != ErrorCode.SUCCESS or ref_info["reference_type"] == "none":
                return ErrorCode.SUCCESS, {"resolved": False}
            
            ref_type = ref_info["reference_type"]
            
            # 从confirmed_slots查找
            if ref_type == "vehicle" and "vehicle" in confirmed_slots:
                return ErrorCode.SUCCESS, {
                    "resolved": True,
                    "entity_type": "vehicle",
                    "entity_value": confirmed_slots["vehicle"]
                }
            
            # 从历史对话查找最近提到的实体
            for turn in reversed(dialogue_history[-5:]):  # 最近5轮
                user_msg = turn.get("user", "")
                
                if ref_type == "vehicle":
                    # 从历史消息中提取车牌号
                    plate_pattern = r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]'
                    matches = re.findall(plate_pattern, user_msg)
                    if matches:
                        return ErrorCode.SUCCESS, {
                            "resolved": True,
                            "entity_type": "vehicle",
                            "entity_value": {"plate_number": matches[-1]}
                        }
            
            return ErrorCode.SUCCESS, {"resolved": False, "reference_type": ref_type}
            
        except Exception as e:
            self.log.error(f"Reference resolution failed: {e}")
            return ErrorCode.SYSTEM_ERROR, {"resolved": False, "error": str(e)}
