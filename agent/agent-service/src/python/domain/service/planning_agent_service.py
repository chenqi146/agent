"""
Planning Agent Service
规划智能体核心服务
包含7大核心模块：
1. 目标拆解模块 (Goal Decomposition)
2. 依赖分析模块 (Dependency Analysis)
3. 工具匹配模块 (Tool Matching)
4. 任务清单生成器 (Task List Generator)
5. 执行引擎 (Execution Engine)
6. 策略知识库 (Strategy Knowledge Base)
7. 经验提取与策略更新 (Experience Extraction & Strategy Update)
"""
import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig
from infrastructure.persistences.mysql_persistence import MysqlPersistence
from infrastructure.repositories.planning_agent_repository import PlanningAgentRepository

from interfaces.dto.planning_agent_dto import (
    CreatePlanningSessionRequest,
    ExecutePlanningRequest,
    PlanningResult,
    PlanningSessionResponse,
    PlanningSessionStatus,
    TaskInfo,
    TaskStatus,
    TaskType,
    ToolMatchInfo,
    StrategyKnowledgeInfo,
    PlanningIntermediateState
)


@logger()
class PlanningAgentService:
    """规划智能体服务"""
    
    def __init__(self, config: SysConfig, mysql_client: Optional[MysqlPersistence] = None):
        self.config = config
        self.repo = PlanningAgentRepository(mysql_client) if mysql_client else None
        
        # 初始化LLM客户端
        llm_cfg = config.get_system_config().get("llm", {})
        self.llm_client = AsyncOpenAI(
            api_key=llm_cfg.get("api_key"),
            base_url=llm_cfg.get("base_url")
        )
        self.model = llm_cfg.get("model", "gpt-4")
        
        # 初始化7大核心模块
        self.goal_decomposer = GoalDecompositionModule(self)
        self.dependency_analyzer = DependencyAnalysisModule(self)
        self.tool_matcher = ToolMatchingModule(self)
        self.task_generator = TaskListGenerator(self)
        self.execution_engine = ExecutionEngine(self)
        self.knowledge_base = StrategyKnowledgeBase(self)
        self.experience_extractor = ExperienceExtractionModule(self)
    
    # ==================== 1. 目标拆解模块 (Goal Decomposition) ====================
    
    async def decompose_goal(
        self,
        session_id: str,
        agent_type: str,
        goal: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ErrorCode, List[Dict[str, Any]]]:
        """
        目标拆解：将复杂目标拆解为可执行的子目标
        
        Args:
            session_id: 会话ID
            agent_type: 智能体类型
            goal: 目标描述
            context: 上下文信息
            
        Returns:
            (ErrorCode, 子目标列表)
        """
        self.log.info("=" * 80)
        self.log.info("📍 [规划智能体] 目标拆解阶段")
        self.log.info(f"🆔 会话ID: {session_id}")
        self.log.info(f"🤖 智能体类型: {agent_type}")
        self.log.info(f"🎯 目标: {goal[:50]}...")
        
        # 获取智能体配置
        err, config = self.repo.get_agent_config(agent_type)
        if err != ErrorCode.SUCCESS:
            return err, []
        
        self.log.info(f"⚙️  智能体配置: {config.get('agent_name', agent_type)}")
        self.log.info(f"🔧 能力范围: {config.get('capabilities', [])}")
        self.log.info("-" * 80)
        
        # 使用LLM进行目标拆解
        system_prompt = f"""你是一个目标拆解专家。请将用户的目标拆解为具体的、可执行的子目标。
        
智能体类型: {config.get('agent_name', agent_type)}
能力范围: {config.get('capabilities', [])}

拆解要求：
1. 每个子目标必须是具体、可衡量的
2. 子目标之间要逻辑清晰，有明确的依赖关系
3. 每个子目标应该对应智能体的一个能力
4. 输出JSON格式，包含子目标名称、类型、描述和预期输出

输出格式：
{{
  "sub_goals": [
    {{
      "name": "子目标名称",
      "type": "analysis/decision/action/verification",
      "description": "详细描述",
      "expected_output": "预期输出",
      "dependencies": ["依赖的子目标名称"]
    }}
  ]
}}"""
        
        self.log.info("🤖 目标拆解 - 发送给LLM的System Prompt:")
        self.log.info(system_prompt)
        self.log.info("-" * 80)
        self.log.info("👤 User Query:")
        user_query = f"目标: {goal}\n\n上下文: {json.dumps(context, ensure_ascii=False) if context else '无'}"
        self.log.info(user_query)
        self.log.info("=" * 80)
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"目标: {goal}\n\n上下文: {json.dumps(context, ensure_ascii=False) if context else '无'}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            sub_goals = result.get("sub_goals", [])
            
            self.log.info("🤖 目标拆解 - LLM返回结果:")
            self.log.info(f"  📊 拆解完成，共 {len(sub_goals)} 个子目标")
            for i, goal in enumerate(sub_goals, 1):
                self.log.info(f"  🎯 子目标 {i}: {goal.get('name', 'N/A')} ({goal.get('type', 'N/A')})")
                self.log.info(f"     📝 描述: {goal.get('description', 'N/A')[:50]}...")
                self.log.info(f"     📤 预期输出: {goal.get('expected_output', 'N/A')[:50]}...")
                self.log.info(f"     🔗 依赖: {goal.get('dependencies', [])}")
            
            # 保存中间态
            if self.repo:
                await asyncio.to_thread(
                    self.repo.save_intermediate_state,
                    session_id, "decomposition",
                    {"sub_goals": sub_goals, "original_goal": goal},
                    f"目标拆解完成，共 {len(sub_goals)} 个子目标"
                )
            
            self.log.info("=" * 80)
            self.log.info("🎯 [规划智能体] 目标拆解阶段完成")
            self.log.info("=" * 80)
            return ErrorCode.SUCCESS, sub_goals
            
        except Exception as e:
            self.log.error(f"【目标拆解】会话 {session_id} 拆解失败: {e}")
            return ErrorCode.SYSTEM_ERROR, []
    
    # ==================== 2. 依赖分析模块 (Dependency Analysis) ====================
    
    async def analyze_dependencies(
        self,
        session_id: str,
        sub_goals: List[Dict[str, Any]]
    ) -> Tuple[ErrorCode, Dict[str, Any]]:
        """
        依赖分析：构建任务DAG图，识别关键路径，串行/并行关系映射、冲突与竞争检测
        
        Args:
            session_id: 会话ID
            sub_goals: 子目标列表
            
        Returns:
            (ErrorCode, 依赖分析结果包含DAG、关键路径、并行组、冲突信息)
        """
        self.log.info("=" * 80)
        self.log.info("📍 [规划智能体] 依赖分析阶段")
        self.log.info(f"🆔 会话ID: {session_id}")
        self.log.info(f"📊 分析 {len(sub_goals)} 个子目标的依赖关系")
        self.log.info("-" * 80)
        
        try:
            # 构建依赖图
            dag = self._build_dependency_graph(sub_goals)
            self.log.info(f"🔗 构建依赖图完成: {len(dag)} 个节点")
            
            # 识别关键路径
            critical_path = self._identify_critical_path(dag)
            self.log.info(f"🎯 关键路径识别完成: {len(critical_path)} 个任务")
            self.log.info(f"   路径: {' → '.join(critical_path)}")
            
            # 识别并行执行组
            parallel_groups = self._identify_parallel_groups(dag)
            self.log.info(f"⚡ 并行组识别完成: {len(parallel_groups)} 组")
            for i, group in enumerate(parallel_groups, 1):
                self.log.info(f"   组 {i}: {group} (可并行执行)")
            
            # 检测冲突
            conflicts = self._detect_conflicts(sub_goals, dag)
            if conflicts:
                self.log.warning(f"⚠️  检测到 {len(conflicts)} 个冲突:")
                for conflict in conflicts:
                    self.log.warning(f"   ❌ {conflict.get('type', 'unknown')}: {conflict.get('description', 'N/A')}")
            else:
                self.log.info("✅ 未检测到冲突")
            
            result = {
                "dag": dag,
                "critical_path": critical_path,
                "parallel_groups": parallel_groups,
                "conflicts": conflicts,
                "total_tasks": len(sub_goals)
            }
            
            # 保存中间态
            if self.repo:
                await asyncio.to_thread(
                    self.repo.save_intermediate_state,
                    session_id, "dependency_analysis",
                    result,
                    f"依赖分析完成，关键路径长度: {len(critical_path)}, 并行组数: {len(parallel_groups)}, 冲突数: {len(conflicts)}",
                    conflicts if conflicts else None,
                    [{"type": "resolve", "description": "自动调整执行顺序"}] if conflicts else None
                )
            
            self.log.info("=" * 80)
            self.log.info("🎯 [规划智能体] 依赖分析阶段完成")
            self.log.info("=" * 80)
            return ErrorCode.SUCCESS, result
            
        except Exception as e:
            self.log.error(f"【依赖分析】会话 {session_id} 分析失败: {e}")
            return ErrorCode.SYSTEM_ERROR, {}
    
    def _build_dependency_graph(self, sub_goals: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """构建依赖图"""
        dag = {}
        for goal in sub_goals:
            name = goal.get("name", "")
            deps = goal.get("dependencies", [])
            dag[name] = deps if deps else []
        return dag
    
    def _identify_critical_path(self, dag: Dict[str, List[str]]) -> List[str]:
        """识别关键路径（简化版：最长路径）"""
        # 使用DFS找出最长路径
        def dfs(node, visited):
            if node in visited:
                return []
            visited.add(node)
            
            deps = dag.get(node, [])
            if not deps:
                return [node]
            
            longest = []
            for dep in deps:
                path = dfs(dep, visited.copy())
                if len(path) > len(longest):
                    longest = path
            
            return longest + [node]
        
        all_nodes = list(dag.keys())
        if not all_nodes:
            return []
        
        # 找出最长路径作为关键路径
        critical = []
        for node in all_nodes:
            path = dfs(node, set())
            if len(path) > len(critical):
                critical = path
        
        return critical
    
    def _identify_parallel_groups(self, dag: Dict[str, List[str]]) -> List[List[str]]:
        """识别可并行执行的组"""
        # 拓扑分层
        in_degree = {node: 0 for node in dag}
        for node, deps in dag.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        groups = []
        current_group = [node for node, degree in in_degree.items() if degree == 0]
        
        while current_group:
            groups.append(current_group)
            next_group = []
            for node in current_group:
                # 找到依赖于此节点的所有节点
                for n, deps in dag.items():
                    if node in deps:
                        in_degree[n] -= 1
                        if in_degree[n] == 0 and n not in sum(groups, []) and n not in next_group:
                            next_group.append(n)
            current_group = next_group
        
        return groups
    
    def _detect_conflicts(
        self,
        sub_goals: List[Dict[str, Any]],
        dag: Dict[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """检测冲突与竞争"""
        conflicts = []
        
        # 检测资源冲突（简化：同名任务）
        names = [g.get("name") for g in sub_goals]
        for i, name in enumerate(names):
            if name in names[i+1:]:
                conflicts.append({
                    "type": "resource_conflict",
                    "description": f"任务名称重复: {name}",
                    "severity": "high"
                })
        
        # 检测循环依赖
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for dep in dag.get(node, []):
                if dep not in visited:
                    if has_cycle(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for node in dag:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    conflicts.append({
                        "type": "circular_dependency",
                        "description": f"检测到循环依赖",
                        "severity": "critical"
                    })
                    break
        
        return conflicts
    
    # ==================== 3. 工具匹配模块 (Tool Matching) ====================
    
    async def match_tools(
        self,
        session_id: str,
        task: Dict[str, Any],
        available_tools: List[Dict[str, Any]]
    ) -> Tuple[ErrorCode, List[ToolMatchInfo]]:
        """
        工具匹配：工具能力匹配、多工具组合优化、回退方案
        
        Args:
            session_id: 会话ID
            task: 任务信息
            available_tools: 可用工具列表
            
        Returns:
            (ErrorCode, 工具匹配列表)
        """
        task_name = task.get("name", "")
        self.log.info("=" * 80)
        self.log.info("📍 [规划智能体] 工具匹配阶段")
        self.log.info(f"🆔 会话ID: {session_id}")
        self.log.info(f"🎯 任务名称: '{task_name}'")
        self.log.info(f"🔧 可用工具数量: {len(available_tools)}")
        self.log.info("-" * 80)
        
        try:
            matches = []
            
            # 使用LLM进行工具匹配
            system_prompt = """你是工具匹配专家。请为给定任务匹配最合适的工具。
            
匹配标准：
1. 工具能力是否满足任务需求
2. 工具的可靠性和性能
3. 输入输出格式是否兼容
4. 是否有回退方案

输出JSON格式：
{
  "matches": [
    {
      "tool_id": "工具ID",
      "tool_name": "工具名称", 
      "match_score": 85,
      "match_reason": "匹配原因",
      "is_primary": true,
      "fallback_tools": ["备选工具ID"]
    }
  ]
}"""
            
            tools_desc = json.dumps([{
                "id": t.get("id"),
                "name": t.get("name"),
                "capabilities": t.get("capabilities", []),
                "description": t.get("description", "")
            } for t in available_tools], ensure_ascii=False)
            
            self.log.info("🤖 工具匹配 - 发送给LLM的System Prompt:")
            self.log.info(system_prompt)
            self.log.info("-" * 80)
            self.log.info("🔧 可用工具列表:")
            self.log.info(tools_desc)
            self.log.info("-" * 80)
            self.log.info("👤 Task Info:")
            task_info = json.dumps(task, ensure_ascii=False)
            self.log.info(task_info)
            self.log.info("=" * 80)
            
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"任务: {json.dumps(task, ensure_ascii=False)}\n\n可用工具: {tools_desc}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            matches_data = result.get("matches", [])
            
            self.log.info("🤖 工具匹配 - LLM返回结果:")
            self.log.info(f"  📊 匹配完成，共 {len(matches_data)} 个工具")
            for i, match in enumerate(matches_data, 1):
                self.log.info(f"  🔧 工具 {i}: {match.get('tool_name', 'N/A')} (ID: {match.get('tool_id', 'N/A')})")
                self.log.info(f"     📊 匹配分数: {match.get('match_score', 0)}")
                self.log.info(f"     💡 匹配原因: {match.get('match_reason', 'N/A')[:50]}...")
                self.log.info(f"     ⭐ 是否主工具: {match.get('is_primary', False)}")
                self.log.info(f"     🔄 回退工具: {match.get('fallback_tools', [])}")
            
            for match_data in matches_data:
                matches.append(ToolMatchInfo(
                    tool_id=match_data.get("tool_id", ""),
                    tool_name=match_data.get("tool_name", ""),
                    match_score=match_data.get("match_score", 0),
                    match_reason=match_data.get("match_reason"),
                    is_primary=match_data.get("is_primary", True),
                    fallback_tools=match_data.get("fallback_tools", [])
                ))
            
            # 保存工具匹配记录
            if self.repo and matches:
                primary = matches[0]
                await asyncio.to_thread(
                    self.repo.create_tool_match,
                    session_id,
                    task.get("id", task_name),
                    primary.tool_id,
                    primary.tool_name,
                    primary.match_score,
                    primary.match_reason,
                    task.get("input_data"),
                    primary.fallback_tools,
                    primary.is_primary
                )
            
            self.log.info("=" * 80)
            self.log.info("🎯 [规划智能体] 工具匹配阶段完成")
            self.log.info("=" * 80)
            return ErrorCode.SUCCESS, matches
            
        except Exception as e:
            self.log.error(f"【工具匹配】会话 {session_id} 工具匹配失败: {e}")
            return ErrorCode.SYSTEM_ERROR, []
    
    # ==================== 4. 任务清单生成器 (Task List Generator) ====================
    
    async def generate_task_list(
        self,
        session_id: str,
        dependency_analysis: Dict[str, Any],
        tool_matches: Dict[str, List[ToolMatchInfo]]
    ) -> Tuple[ErrorCode, PlanningResult]:
        """
        任务清单生成：输出任务链、工具调用序列、超时重试策略、监控指标
        
        Args:
            session_id: 会话ID
            dependency_analysis: 依赖分析结果
            tool_matches: 任务-工具匹配结果
            
        Returns:
            (ErrorCode, 规划结果)
        """
        self.log.info("=" * 80)
        self.log.info("📍 [规划智能体] 任务清单生成阶段")
        self.log.info(f"🆔 会话ID: {session_id}")
        self.log.info(f"📊 开始生成任务清单")
        self.log.info("-" * 80)
        
        try:
            dag = dependency_analysis.get("dag", {})
            critical_path = dependency_analysis.get("critical_path", [])
            parallel_groups = dependency_analysis.get("parallel_groups", [])
            
            self.log.info(f"🔗 依赖图节点数: {len(dag)}")
            self.log.info(f"🎯 关键路径长度: {len(critical_path)}")
            self.log.info(f"⚡ 并行组数量: {len(parallel_groups)}")
            
            tasks = []
            execution_order = 0
            
            # 为每个节点创建任务
            for group_idx, group in enumerate(parallel_groups):
                self.log.info(f"📋 处理并行组 {group_idx + 1}: {group}")
                for node in group:
                    is_critical = node in critical_path
                    deps = dag.get(node, [])
                    
                    # 获取工具匹配
                    tools = tool_matches.get(node, [])
                    primary_tool = tools[0] if tools else None
                    
                    task = TaskInfo(
                        task_id=f"task_{node}",
                        task_name=node,
                        task_type=TaskType.ACTION,
                        status=TaskStatus.PENDING,
                        dependencies=[f"task_{d}" for d in deps],
                        is_critical_path=is_critical,
                        execution_order=execution_order,
                        parallel_group=group_idx,
                        max_retries=3 if is_critical else 2,
                        timeout_seconds=60 if is_critical else 30
                    )
                    tasks.append(task)
                    
                    self.log.info(f"  ✅ 创建任务: {task.task_id}")
                    self.log.info(f"     🎯 任务名称: {task.task_name}")
                    self.log.info(f"     📍 关键路径: {'是' if is_critical else '否'}")
                    self.log.info(f"     🔗 依赖: {task.dependencies}")
                    self.log.info(f"     🔧 主工具: {primary_tool.tool_name if primary_tool else 'N/A'}")
                    
                    execution_order += 1
            
            result = PlanningResult(
                session_id=session_id,
                status=PlanningSessionStatus.PLANNING,
                tasks=tasks,
                critical_path=[f"task_{n}" for n in critical_path],
                parallel_groups=[[f"task_{n}" for n in group] for group in parallel_groups],
                tool_matches={k: [v] for k, v in tool_matches.items()}
            )
            
            # 保存规划结果到数据库
            if self.repo:
                # 保存所有任务
                for task in tasks:
                    await asyncio.to_thread(
                        self.repo.create_task,
                        session_id,
                        task.task_id,
                        task.task_name,
                        task.task_type.value,
                        None,  # description
                        task.dependencies,
                        task.is_critical_path,
                        task.execution_order,
                        task.parallel_group,
                        task.max_retries,
                        task.timeout_seconds
                    )
                
                # 保存中间态
                await asyncio.to_thread(
                    self.repo.save_intermediate_state,
                    session_id, "task_generation",
                    {"tasks_count": len(tasks), "critical_path_length": len(critical_path)},
                    f"任务清单生成完成，共 {len(tasks)} 个任务"
                )
            
            self.log.info(f"📊 任务清单生成完成:")
            self.log.info(f"  📋 总任务数: {len(tasks)}")
            self.log.info(f"  🎯 关键路径任务: {len(critical_path)}")
            self.log.info(f"  ⚡ 并行组数: {len(parallel_groups)}")
            self.log.info(f"  🔧 工具匹配数: {len(tool_matches)}")
            
            self.log.info("=" * 80)
            self.log.info("🎯 [规划智能体] 任务清单生成阶段完成")
            self.log.info("=" * 80)
            return ErrorCode.SUCCESS, result
            
        except Exception as e:
            self.log.error(f"【任务清单生成】会话 {session_id} 生成失败: {e}")
            return ErrorCode.SYSTEM_ERROR, PlanningResult(session_id=session_id, status=PlanningSessionStatus.FAILED)
    
    # ==================== 5. 执行引擎 (Execution Engine) ====================
    
    async def execute_task(
        self,
        session_id: str,
        task: TaskInfo,
        tools: List[ToolMatchInfo]
    ) -> Tuple[ErrorCode, Dict[str, Any]]:
        """
        执行引擎：工具调用、结果处理
        
        Args:
            session_id: 会话ID
            task: 任务信息
            tools: 工具匹配列表
            
        Returns:
            (ErrorCode, 执行结果)
        """
        self.log.info("=" * 80)
        self.log.info("📍 [规划智能体] 执行引擎阶段")
        self.log.info(f"🆔 会话ID: {session_id}")
        self.log.info(f"🎯 任务名称: '{task.task_name}'")
        self.log.info(f"🔧 可用工具数: {len(tools)}")
        self.log.info("-" * 80)
        
        try:
            # 更新任务状态为运行中
            if self.repo:
                await asyncio.to_thread(
                    self.repo.update_task,
                    session_id,
                    task.task_id,
                    {"status": "running", "started_at": datetime.now()}
                )
            
            # 获取主工具和回退工具
            primary_tool = next((t for t in tools if t.is_primary), tools[0] if tools else None)
            fallback_tools = [t for t in tools if not t.is_primary]
            
            self.log.info(f"🔧 主工具: {primary_tool.tool_name if primary_tool else 'N/A'}")
            self.log.info(f"🔄 回退工具数: {len(fallback_tools)}")
            
            if not primary_tool:
                raise ValueError(f"任务 '{task.task_name}' 没有匹配的工具")
            
            # 尝试执行主工具
            result = None
            error = None
            
            for attempt in range(task.max_retries):
                try:
                    self.log.info(f"🚀 第 {attempt+1}/{task.max_retries} 次尝试执行工具 '{primary_tool.tool_name}'")
                    
                    # 模拟工具调用（实际实现中这里调用真实的工具）
                    result = await self._call_tool(
                        session_id,
                        primary_tool.tool_id,
                        task.task_name,
                        {}
                    )
                    
                    if result.get("success", False):
                        self.log.info(f"✅ 工具执行成功!")
                        self.log.info(f"📊 执行结果: {result.get('output', 'N/A')[:100]}...")
                        break
                        
                except Exception as e:
                    error = str(e)
                    self.log.warning(f"⚠️  工具执行失败: {e}")
                    
                    # 如果有回退工具，尝试使用
                    if fallback_tools and attempt == task.max_retries - 1:
                        self.log.info(f"🔄 主工具失败，尝试回退工具...")
                        for fallback in fallback_tools:
                            try:
                                self.log.info(f"🔄 尝试回退工具 '{fallback.tool_name}'")
                                result = await self._call_tool(
                                    session_id,
                                    fallback.tool_id,
                                    task.task_name,
                                    {}
                                )
                                if result.get("success", False):
                                    self.log.info(f"✅ 回退工具执行成功!")
                                    error = None
                                    break
                            except Exception as e2:
                                self.log.warning(f"⚠️  回退工具也失败: {e2}")
                    
                    await asyncio.sleep(2 ** attempt)  # 指数退避
            
            # 更新任务状态
            final_status = "completed" if (result and result.get("success")) else "failed"
            if self.repo:
                update_data = {
                    "status": final_status,
                    "completed_at": datetime.now(),
                    "output_data": result,
                    "retry_count": attempt + 1
                }
                if error:
                    update_data["error_info"] = {"error": error}
                
                await asyncio.to_thread(
                    self.repo.update_task,
                    session_id,
                    task.task_id,
                    update_data
                )
            
            if result and result.get("success"):
                self.log.info(f"🎉 任务 '{task.task_name}' 执行成功!")
                self.log.info(f"📊 最终状态: {final_status}")
                self.log.info(f"🔄 重试次数: {attempt + 1}")
                self.log.info("=" * 80)
                self.log.info("🎯 [规划智能体] 执行引擎阶段完成")
                self.log.info("=" * 80)
                return ErrorCode.SUCCESS, result
            else:
                self.log.error(f"❌ 任务 '{task.task_name}' 执行失败")
                self.log.error(f"📊 最终状态: {final_status}")
                self.log.error(f"🔄 重试次数: {attempt + 1}")
                self.log.error(f"❌ 错误信息: {error or '执行失败'}")
                self.log.info("=" * 80)
                self.log.info("🎯 [规划智能体] 执行引擎阶段完成 (失败)")
                self.log.info("=" * 80)
                return ErrorCode.SYSTEM_ERROR, {"error": error or "执行失败"}
                
        except Exception as e:
            self.log.error(f"【执行引擎】会话 {session_id} 任务 '{task.task_name}' 执行异常: {e}")
            if self.repo:
                await asyncio.to_thread(
                    self.repo.update_task,
                    session_id,
                    task.task_id,
                    {
                        "status": "failed",
                        "completed_at": datetime.now(),
                        "error_info": {"error": str(e)}
                    }
                )
            return ErrorCode.SYSTEM_ERROR, {"error": str(e)}
    
    async def _call_tool(
        self,
        session_id: str,
        tool_id: str,
        task_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用工具（模拟实现）"""
        # 这里应该调用实际的工具
        # 目前返回模拟结果
        return {
            "success": True,
            "tool_id": tool_id,
            "task_name": task_name,
            "output": f"工具 {tool_id} 执行 {task_name} 的结果",
            "execution_time_ms": 100
        }
    
    # ==================== 6. 策略知识库 (Strategy Knowledge Base) ====================
    
    async def query_strategy_knowledge(
        self,
        agent_type: str,
        scenario_type: Optional[str] = None
    ) -> Tuple[ErrorCode, List[StrategyKnowledgeInfo]]:
        """
        策略知识库查询：成功模式识别、失败教训分析、最佳实践匹配
        
        Args:
            agent_type: 智能体类型
            scenario_type: 场景类型
            
        Returns:
            (ErrorCode, 策略知识列表)
        """
        self.log.info(f"【策略知识库】查询 {agent_type} 的策略知识，场景: {scenario_type}")
        
        if not self.repo:
            return ErrorCode.SUCCESS, []
        
        try:
            err, rows = await asyncio.to_thread(
                self.repo.get_strategy_knowledge,
                agent_type,
                scenario_type,
                True  # is_active
            )
            
            if err != ErrorCode.SUCCESS:
                return err, []
            
            knowledge_list = []
            for row in rows:
                knowledge_list.append(StrategyKnowledgeInfo(
                    knowledge_id=row.get("knowledge_id", ""),
                    agent_type=row.get("agent_type", ""),
                    scenario_type=row.get("scenario_type", ""),
                    pattern_name=row.get("pattern_name", ""),
                    description=row.get("description"),
                    success_criteria=row.get("success_criteria", []),
                    best_practice=row.get("best_practice"),
                    tool_combination=row.get("tool_combination", []),
                    effectiveness_score=row.get("effectiveness_score", 0.0)
                ))
            
            self.log.info(f"【策略知识库】查询到 {len(knowledge_list)} 条策略知识")
            return ErrorCode.SUCCESS, knowledge_list
            
        except Exception as e:
            self.log.error(f"【策略知识库】查询失败: {e}")
            return ErrorCode.SYSTEM_ERROR, []
    
    # ==================== 7. 经验提取与策略更新 (Experience Extraction) ====================
    
    async def extract_experience(
        self,
        session_id: str
    ) -> Tuple[ErrorCode, Dict[str, Any]]:
        """
        经验提取与策略更新：轨迹分析、错误诊断、策略优化建议
        
        Args:
            session_id: 会话ID
            
        Returns:
            (ErrorCode, 经验分析结果)
        """
        self.log.info(f"【经验提取】会话 {session_id} 开始提取经验")
        
        if not self.repo:
            return ErrorCode.SUCCESS, {}
        
        try:
            # 获取会话信息
            err, session = await asyncio.to_thread(
                self.repo.get_planning_session,
                session_id
            )
            if err != ErrorCode.SUCCESS:
                return err, {}
            
            # 获取所有任务执行结果
            err, tasks = await asyncio.to_thread(
                self.repo.list_session_tasks,
                session_id
            )
            if err != ErrorCode.SUCCESS:
                return err, {}
            
            # 分析成功模式
            success_patterns = []
            failure_lessons = []
            
            for task in tasks:
                if task.get("status") == "completed":
                    success_patterns.append({
                        "task_name": task.get("task_name"),
                        "tool_used": task.get("tool_calls", []),
                        "execution_time": task.get("execution_time_ms")
                    })
                elif task.get("status") == "failed":
                    failure_lessons.append({
                        "task_name": task.get("task_name"),
                        "error": task.get("error_info", {}),
                        "retry_count": task.get("retry_count", 0)
                    })
            
            # 生成优化建议
            optimization_suggestions = []
            
            # 1. 重试策略优化建议
            failed_tasks = [t for t in tasks if t.get("status") == "failed"]
            if failed_tasks:
                avg_retry = sum(t.get("retry_count", 0) for t in failed_tasks) / len(failed_tasks)
                if avg_retry > 2:
                    optimization_suggestions.append({
                        "type": "retry_optimization",
                        "description": f"失败任务平均重试 {avg_retry:.1f} 次，建议增加回退工具或优化主工具"
                    })
            
            # 2. 关键路径优化建议
            critical_tasks = [t for t in tasks if t.get("is_critical_path")]
            critical_failures = [t for t in critical_tasks if t.get("status") == "failed"]
            if critical_failures:
                optimization_suggestions.append({
                    "type": "critical_path_optimization", 
                    "description": f"关键路径上 {len(critical_failures)} 个任务失败，建议增加冗余或备用路径"
                })
            
            # 3. 并行度优化建议
            parallel_groups = {}
            for task in tasks:
                group = task.get("parallel_group", 0)
                if group not in parallel_groups:
                    parallel_groups[group] = []
                parallel_groups[group].append(task)
            
            max_group_size = max(len(g) for g in parallel_groups.values()) if parallel_groups else 0
            if max_group_size > 5:
                optimization_suggestions.append({
                    "type": "parallel_optimization",
                    "description": f"最大并行组包含 {max_group_size} 个任务，可能需要更多执行资源"
                })
            
            # 保存执行轨迹
            trajectory_id = f"traj_{uuid.uuid4().hex[:16]}"
            await asyncio.to_thread(
                self.repo.save_execution_trajectory,
                session_id,
                trajectory_id,
                {
                    "session": session,
                    "tasks": tasks,
                    "analysis_timestamp": datetime.now().isoformat()
                },
                {
                    "total_tasks": len(tasks),
                    "success_count": len([t for t in tasks if t.get("status") == "completed"]),
                    "failure_count": len(failed_tasks),
                    "success_rate": len([t for t in tasks if t.get("status") == "completed"]) / len(tasks) if tasks else 0
                },
                [json.dumps(p) for p in success_patterns],
                [json.dumps(l) for l in failure_lessons],
                [json.dumps(s) for s in optimization_suggestions],
                len(optimization_suggestions) > 0
            )
            
            result = {
                "trajectory_id": trajectory_id,
                "success_patterns": success_patterns,
                "failure_lessons": failure_lessons,
                "optimization_suggestions": optimization_suggestions,
                "strategy_update_needed": len(optimization_suggestions) > 0
            }
            
            self.log.info(f"【经验提取】会话 {session_id} 经验提取完成，发现 {len(success_patterns)} 个成功模式，{len(failure_lessons)} 个失败教训")
            return ErrorCode.SUCCESS, result
            
        except Exception as e:
            self.log.error(f"【经验提取】会话 {session_id} 经验提取失败: {e}")
            return ErrorCode.SYSTEM_ERROR, {}
    
    # ==================== 主流程控制 ====================
    
    async def create_session(
        self,
        request: CreatePlanningSessionRequest
    ) -> Tuple[ErrorCode, PlanningSessionResponse]:
        """创建规划会话"""
        session_id = f"plan_{uuid.uuid4().hex[:16]}"
        
        if not self.repo:
            return ErrorCode.SYSTEM_ERROR, None
        
        try:
            err, _ = await asyncio.to_thread(
                self.repo.create_planning_session,
                session_id,
                request.user_id,
                request.agent_type.value,
                request.goal,
                request.initial_context
            )
            
            if err != ErrorCode.SUCCESS:
                return err, None
            
            return ErrorCode.SUCCESS, PlanningSessionResponse(
                session_id=session_id,
                user_id=request.user_id,
                agent_type=request.agent_type,
                goal=request.goal,
                status=PlanningSessionStatus.PLANNING
            )
            
        except Exception as e:
            self.log.error(f"创建规划会话失败: {e}")
            return ErrorCode.SYSTEM_ERROR, None
    
    async def execute_planning(
        self,
        request: ExecutePlanningRequest
    ) -> Tuple[ErrorCode, PlanningResult]:
        """执行规划流程"""
        self.log.info("=" * 80)
        self.log.info(f"🚀 [规划智能体] 执行规划流程开始 session_id={request.session_id}")
        if not self.repo:
            return ErrorCode.SYSTEM_ERROR, PlanningResult(session_id=request.session_id, status=PlanningSessionStatus.FAILED)
        
        try:
            # 1. 获取会话信息
            err, session = await asyncio.to_thread(
                self.repo.get_planning_session,
                request.session_id
            )
            if err != ErrorCode.SUCCESS:
                self.log.error(f"❌ 获取规划会话失败: err={err}, session_id={request.session_id}")
                return err, PlanningResult(session_id=request.session_id, status=PlanningSessionStatus.FAILED)
            
            agent_type = session.get("agent_type", "")
            goal = session.get("goal", "")
            context = session.get("initial_context", {})
            self.log.info(f"🧠 会话信息: agent_type={agent_type}, goal='{goal[:100]}...'")
            
            # 2. 目标拆解
            err, sub_goals = await self.decompose_goal(
                request.session_id,
                agent_type,
                goal,
                context
            )
            if err != ErrorCode.SUCCESS:
                self.log.error(f"❌ 目标拆解失败: err={err}")
                return err, PlanningResult(session_id=request.session_id, status=PlanningSessionStatus.FAILED)
            
            # 3. 依赖分析
            err, dependency_analysis = await self.analyze_dependencies(
                request.session_id,
                sub_goals
            )
            if err != ErrorCode.SUCCESS:
                self.log.error(f"❌ 依赖分析失败: err={err}")
                return err, PlanningResult(session_id=request.session_id, status=PlanningSessionStatus.FAILED)
            
            # 4. 工具匹配（为每个任务匹配工具）
            tool_matches = {}
            for goal in sub_goals:
                goal_name = goal.get("name", "")
                # 获取可用工具列表（实际应该从工具注册中心获取）
                available_tools = []  # 简化实现
                err, matches = await self.match_tools(
                    request.session_id,
                    goal,
                    available_tools
                )
                if err == ErrorCode.SUCCESS and matches:
                    tool_matches[goal_name] = matches
            
            # 5. 生成任务清单
            err, result = await self.generate_task_list(
                request.session_id,
                dependency_analysis,
                tool_matches
            )
            if err != ErrorCode.SUCCESS:
                return err, PlanningResult(session_id=request.session_id, status=PlanningSessionStatus.FAILED)
            
            # 6. 更新会话状态
            await asyncio.to_thread(
                self.repo.update_planning_session,
                request.session_id,
                {
                    "status": "planning_complete",
                    "plan_result": result.model_dump()
                }
            )
            
            return ErrorCode.SUCCESS, result
            
        except Exception as e:
            self.log.error(f"执行规划失败: {e}")
            return ErrorCode.SYSTEM_ERROR, PlanningResult(session_id=request.session_id, status=PlanningSessionStatus.FAILED)
    
    async def execute_plan(
        self,
        session_id: str
    ) -> Tuple[ErrorCode, Dict[str, Any]]:
        """执行规划好的任务"""
        if not self.repo:
            return ErrorCode.SYSTEM_ERROR, {"error": "Repository not available"}
        
        try:
            # 更新会话状态
            await asyncio.to_thread(
                self.repo.update_planning_session,
                session_id,
                {"status": "executing"}
            )
            
            # 获取所有任务
            err, tasks = await asyncio.to_thread(
                self.repo.list_session_tasks,
                session_id
            )
            if err != ErrorCode.SUCCESS:
                return err, {}
            
            # 按执行顺序排序
            tasks = sorted(tasks, key=lambda t: t.get("execution_order", 0))
            
            # 执行任务
            execution_results = []
            for task_data in tasks:
                task = TaskInfo(
                    task_id=task_data.get("task_id", ""),
                    task_name=task_data.get("task_name", ""),
                    task_type=TaskType(task_data.get("task_type", "action")),
                    status=TaskStatus(task_data.get("status", "pending")),
                    dependencies=task_data.get("dependencies", []),
                    is_critical_path=task_data.get("is_critical_path", False),
                    execution_order=task_data.get("execution_order", 0),
                    max_retries=task_data.get("max_retries", 3),
                    timeout_seconds=task_data.get("timeout_seconds", 30)
                )
                
                # 检查依赖是否都已完成
                deps_completed = all(
                    any(t.get("task_id") == dep and t.get("status") == "completed" for t in execution_results)
                    for dep in task.dependencies
                )
                
                if not deps_completed:
                    self.log.warning(f"任务 {task.task_name} 的依赖未完成，跳过执行")
                    continue
                
                # 执行task
                err, result = await self.execute_task(session_id, task, [])
                execution_results.append({
                    "task_id": task.task_id,
                    "status": "completed" if err == ErrorCode.SUCCESS else "failed",
                    "result": result
                })
            
            # 更新会话状态
            await asyncio.to_thread(
                self.repo.update_planning_session,
                session_id,
                {
                    "status": "completed",
                    "execution_log": {"results": execution_results},
                    "completed_at": datetime.now()
                }
            )
            
            # 7. 经验提取
            await self.extract_experience(session_id)
            
            return ErrorCode.SUCCESS, {"execution_results": execution_results}
            
        except Exception as e:
            self.log.error(f"执行计划失败: {e}")
            await asyncio.to_thread(
                self.repo.update_planning_session,
                session_id,
                {"status": "failed", "execution_log": {"error": str(e)}}
            )
            return ErrorCode.SYSTEM_ERROR, {"error": str(e)}
    
    async def get_session_status(
        self,
        session_id: str
    ) -> Tuple[ErrorCode, Optional[PlanningSessionResponse]]:
        """获取会话状态"""
        if not self.repo:
            return ErrorCode.SYSTEM_ERROR, None
        
        try:
            err, session = await asyncio.to_thread(
                self.repo.get_planning_session,
                session_id
            )
            if err != ErrorCode.SUCCESS:
                return err, None
            
            return ErrorCode.SUCCESS, PlanningSessionResponse(
                session_id=session.get("session_id", ""),
                user_id=session.get("user_id", 0),
                agent_type=PlanningAgentType(session.get("agent_type", "parking_billing")),
                goal=session.get("goal", ""),
                status=PlanningSessionStatus(session.get("status", "planning")),
                plan_result=session.get("plan_result"),
                execution_log=session.get("execution_log"),
                created_at=session.get("created_at"),
                updated_at=session.get("updated_at")
            )
            
        except Exception as e:
            self.log.error(f"获取会话状态失败: {e}")
            return ErrorCode.SYSTEM_ERROR, None


# ==================== 7大核心模块类 ====================

class GoalDecompositionModule:
    """目标拆解模块"""
    def __init__(self, service: PlanningAgentService):
        self.service = service


class DependencyAnalysisModule:
    """依赖分析模块"""
    def __init__(self, service: PlanningAgentService):
        self.service = service


class ToolMatchingModule:
    """工具匹配模块"""
    def __init__(self, service: PlanningAgentService):
        self.service = service


class TaskListGenerator:
    """任务清单生成器"""
    def __init__(self, service: PlanningAgentService):
        self.service = service


class ExecutionEngine:
    """执行引擎"""
    def __init__(self, service: PlanningAgentService):
        self.service = service


class StrategyKnowledgeBase:
    """策略知识库"""
    def __init__(self, service: PlanningAgentService):
        self.service = service


class ExperienceExtractionModule:
    """经验提取与策略更新模块"""
    def __init__(self, service: PlanningAgentService):
        self.service = service
