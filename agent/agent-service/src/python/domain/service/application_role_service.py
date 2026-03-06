from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
import json

from infrastructure.common.error.errcode import ErrorCode
from infrastructure.common.logging.logging import logger
from infrastructure.config.sys_config import SysConfig
from infrastructure.repositories.application_role_repository import ApplicationRoleRepository
from interfaces.dto.role_dto import (
    ApplicationRoleInfo,
    ApplicationRoleListRequest,
    ApplicationRolePage,
    ApplicationRoleSaveRequest,
    ApplicationRoleToggleStatusRequest,
    ApplicationRoleIdRequest,
    ApplicationRoleStatus,
    ApplicationRoleActiveRequest,
    ApplicationRoleActiveResult,
)


@logger()
class ApplicationRoleService:
    def __init__(self, config: SysConfig, mysql_client=None):
        self.config = config
        self.repo = ApplicationRoleRepository(config, mysql_client)

    def _status_db_to_enum(self, value: Optional[int]) -> ApplicationRoleStatus:
        if value == 1:
            return ApplicationRoleStatus.ENABLED
        return ApplicationRoleStatus.DISABLED

    def _status_enum_to_db(self, status: Optional[ApplicationRoleStatus]) -> Optional[int]:
        if status is None:
            return None
        if status == ApplicationRoleStatus.ENABLED:
            return 1
        if status == ApplicationRoleStatus.DISABLED:
            return 0
        return None

    def _format_datetime(self, value: object) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if value is None:
            return ""
        return str(value)

    def _format_time_range(self, start: Optional[datetime], end: Optional[datetime]) -> str:
        if not start or not end:
            return ""
        return f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"

    def _format_date_range(self, start: Optional[datetime], end: Optional[datetime]) -> str:
        if not start or not end:
            return ""
        return f"{start.strftime('%Y-%m-%d')} 至 {end.strftime('%Y-%m-%d')}"

    def _parse_enable_time(self, value: str) -> Tuple[datetime, datetime]:
        today = date.today()
        default_start = datetime(today.year, today.month, today.day, 0, 0, 0)
        default_end = datetime(today.year, today.month, today.day, 23, 59, 59)
        if not value:
            return default_start, default_end
        parts = value.split("-")
        if len(parts) != 2:
            return default_start, default_end
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        try:
            h, m = start_str.split(":")
            start_dt = datetime(today.year, today.month, today.day, int(h), int(m), 0)
        except Exception:
            start_dt = default_start
        try:
            h2, m2 = end_str.split(":")
            end_dt = datetime(today.year, today.month, today.day, int(h2), int(m2), 0)
        except Exception:
            end_dt = default_end
        return start_dt, end_dt

    def _parse_enable_period(self, value: str) -> Tuple[datetime, datetime]:
        today = date.today()
        default_start = datetime(today.year, today.month, today.day, 0, 0, 0)
        default_end = datetime(today.year, today.month, today.day, 23, 59, 59)
        if not value:
            return default_start, default_end
        parts = value.split("至")
        if len(parts) != 2:
            return default_start, default_end
        start_str = parts[0].strip()
        end_str = parts[1].strip()
        try:
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        except Exception:
            start_dt = default_start
        try:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d")
        except Exception:
            end_dt = default_end
        return start_dt, end_dt

    def _build_role_model(self, row: Dict[str, object]) -> ApplicationRoleInfo:
        role_id = int(row.get("id"))
        name = str(row.get("name") or "")
        upload_time = row.get("upload_time")
        daily_start = row.get("daily_activation_start_time")
        daily_end = row.get("daily_activation_end_time")
        period_start = row.get("period_start_time")
        period_end = row.get("period_end_time")
        enable_time = self._format_time_range(daily_start, daily_end)
        enable_period = self._format_date_range(period_start, period_end)
        status_enum = self._status_db_to_enum(row.get("status"))
        enabled = status_enum == ApplicationRoleStatus.ENABLED
        prompt_template_id = row.get("prompt_template_id")
        prompt_id: Optional[int] = None
        if prompt_template_id is not None:
            pid = int(prompt_template_id)
            if pid > 0:
                prompt_id = pid
        
        description = row.get("description")
        custom_prompt = None
        mode = "fixed"
        fixed_prompts = []
        dynamic_prompts = []

        if description:
            try:
                desc_obj = json.loads(str(description))
                if isinstance(desc_obj, dict):
                    mode = desc_obj.get("mode", "fixed")
                    custom_prompt = desc_obj.get("customPrompt")
                    fixed_prompts = desc_obj.get("fixedPrompts", [])
                    dynamic_prompts = desc_obj.get("dynamicPrompts", [])
                else:
                    custom_prompt = str(description)
            except Exception:
                custom_prompt = str(description)

        created_at = self._format_datetime(upload_time)
        return ApplicationRoleInfo(
            id=role_id,
            name=name,
            createdAt=created_at,
            enableTime=enable_time,
            enablePeriod=enable_period,
            enabled=enabled,
            promptId=prompt_id,
            customPrompt=custom_prompt,
            mode=mode,
            fixedPrompts=fixed_prompts,
            dynamicPrompts=dynamic_prompts,
        )

    def list_roles(
        self,
        user_id: int,
        req: ApplicationRoleListRequest,
    ) -> Tuple[ErrorCode, Optional[ApplicationRolePage]]:
        page = req.page if req.page and req.page > 0 else 1
        size = req.size if req.size and req.size > 0 else 10
        size = min(size, 100)
        status_db = self._status_enum_to_db(req.status)
        err_count, total = self.repo.count_roles(user_id, req.keyword, status_db)
        if err_count != ErrorCode.SUCCESS:
            return err_count, None
        if total == 0:
            page_obj = ApplicationRolePage(items=[], total=0, page=page, size=size)
            return ErrorCode.SUCCESS, page_obj
        offset = (page - 1) * size
        err_list, rows = self.repo.list_roles(user_id, req.keyword, status_db, size, offset)
        if err_list != ErrorCode.SUCCESS:
            return err_list, None
        items: List[ApplicationRoleInfo] = []
        for row in rows:
            items.append(self._build_role_model(row))
        page_obj = ApplicationRolePage(items=items, total=total, page=page, size=size)
        return ErrorCode.SUCCESS, page_obj

    def get_role(
        self,
        user_id: int,
        req: ApplicationRoleIdRequest,
    ) -> Tuple[ErrorCode, Optional[ApplicationRoleInfo]]:
        err, row = self.repo.get_role_by_id(req.id, user_id)
        if err != ErrorCode.SUCCESS:
            return err, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
        info = self._build_role_model(row)
        return ErrorCode.SUCCESS, info

    def _update_role_relations(self, role_id: int, req: ApplicationRoleSaveRequest) -> None:
        prompt_ids = set()
        
        # 1. Main promptId
        if req.promptId is not None:
            try:
                pid = int(req.promptId)
                if pid > 0:
                    prompt_ids.add(pid)
            except Exception:
                pass
        
        # 2. Fixed mode prompts
        if req.fixedPrompts:
            for item in req.fixedPrompts:
                pid = item.get("promptId")
                if pid:
                    try:
                        prompt_ids.add(int(pid))
                    except Exception:
                        pass
        
        # 3. Dynamic mode prompts
        if req.dynamicPrompts:
            for pid in req.dynamicPrompts:
                if pid:
                    try:
                        prompt_ids.add(int(pid))
                    except Exception:
                        pass
        
        # Update relations
        self.repo.delete_role_relations(role_id)
        
        if prompt_ids:
            relations = [{"role_id": role_id, "prompt_id": pid} for pid in prompt_ids]
            self.repo.insert_role_relations(relations)

    def create_role(
        self,
        user_id: int,
        req: ApplicationRoleSaveRequest,
    ) -> Tuple[ErrorCode, Optional[ApplicationRoleInfo]]:
        name = req.name.strip()
        if not name:
            return ErrorCode.INVALID_PARAMETER, None
        status_flag = 1 if (req.enabled is None or req.enabled) else 0
        
        daily_start, daily_end = self._parse_enable_time(req.enableTime or "")
        period_start, period_end = self._parse_enable_period(req.enablePeriod or "")
        prompt_template_id = 0
        if req.promptId is not None:
            try:
                pid = int(req.promptId)
            except Exception:
                pid = 0
            if pid > 0:
                prompt_template_id = pid
        
        description_data = {
            "mode": req.mode or "fixed",
            "customPrompt": req.customPrompt,
            "fixedPrompts": req.fixedPrompts or [],
            "dynamicPrompts": req.dynamicPrompts or []
        }
        description = json.dumps(description_data, ensure_ascii=False)

        data: Dict[str, object] = {
            "name": name,
            "status": status_flag,
            "upload_time": datetime.utcnow(),
            "period_start_time": period_start,
            "period_end_time": period_end,
            "daily_activation_start_time": daily_start,
            "daily_activation_end_time": daily_end,
            "description": description,
            "prompt_template_id": prompt_template_id,
            "binding_user_id": int(user_id),
        }
        err_ins, role_id = self.repo.insert_role(data)
        if err_ins != ErrorCode.SUCCESS or not role_id:
            return err_ins, None
            
        # Update relations
        self._update_role_relations(role_id, req)
        
        get_req = ApplicationRoleIdRequest(id=role_id)
        return self.get_role(user_id, get_req)

    def update_role(
        self,
        user_id: int,
        req: ApplicationRoleSaveRequest,
    ) -> Tuple[ErrorCode, Optional[ApplicationRoleInfo]]:
        if not req.id:
            return ErrorCode.MISSING_PARAMETER, None
        name = req.name.strip()
        if not name:
            return ErrorCode.INVALID_PARAMETER, None
        err_exist, row = self.repo.get_role_by_id(req.id, user_id)
        if err_exist != ErrorCode.SUCCESS:
            return err_exist, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
        daily_start, daily_end = self._parse_enable_time(req.enableTime or "")
        period_start, period_end = self._parse_enable_period(req.enablePeriod or "")
        prompt_template_id = row.get("prompt_template_id") or 0
        if req.promptId is not None:
            try:
                pid = int(req.promptId)
            except Exception:
                pid = 0
            if pid > 0:
                prompt_template_id = pid
        
        description_data = {
            "mode": req.mode or "fixed",
            "customPrompt": req.customPrompt,
            "fixedPrompts": req.fixedPrompts or [],
            "dynamicPrompts": req.dynamicPrompts or []
        }
        description = json.dumps(description_data, ensure_ascii=False)

        status_flag = row.get("status") or 0
        if req.enabled is not None:
            status_flag = 1 if req.enabled else 0
        data: Dict[str, object] = {
            "name": name,
            "status": status_flag,
            "period_start_time": period_start,
            "period_end_time": period_end,
            "daily_activation_start_time": daily_start,
            "daily_activation_end_time": daily_end,
            "description": description,
            "prompt_template_id": prompt_template_id,
        }
        err_upd, _ = self.repo.update_role(req.id, user_id, data)
        if err_upd != ErrorCode.SUCCESS:
            return err_upd, None
            
        # Update relations
        self._update_role_relations(req.id, req)
        
        get_req = ApplicationRoleIdRequest(id=req.id)
        return self.get_role(user_id, get_req)

    def delete_role(
        self,
        user_id: int,
        req: ApplicationRoleIdRequest,
    ) -> Tuple[ErrorCode, Optional[object]]:
        err_exist, row = self.repo.get_role_by_id(req.id, user_id)
        if err_exist != ErrorCode.SUCCESS:
            return err_exist, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
            
        # Delete relations first
        self.repo.delete_role_relations(req.id)
        
        err_del, _ = self.repo.delete_role(req.id, user_id)
        if err_del != ErrorCode.SUCCESS:
            return err_del, None
        return ErrorCode.SUCCESS, None

    def toggle_status(
        self,
        user_id: int,
        req: ApplicationRoleToggleStatusRequest,
    ) -> Tuple[ErrorCode, Optional[ApplicationRoleInfo]]:
        err_exist, row = self.repo.get_role_by_id(req.id, user_id)
        if err_exist != ErrorCode.SUCCESS:
            return err_exist, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
        status_flag = 1 if req.enabled else 0
        err_upd, _ = self.repo.update_role(req.id, user_id, {"status": status_flag})
        if err_upd != ErrorCode.SUCCESS:
            return err_upd, None
        get_req = ApplicationRoleIdRequest(id=req.id)
        return self.get_role(user_id, get_req)

    def get_active_roles_at_time(
        self,
        user_id: int,
        req: ApplicationRoleActiveRequest,
    ) -> Tuple[ErrorCode, Optional[ApplicationRoleActiveResult]]:
        """
        获取指定时间有效的角色列表
        
        逻辑：
        1. 查询用户所有启用的角色
        2. 筛选出在指定时间段内有效的角色（检查period和daily时间范围）
        3. 如果有多个角色有效，标记需要用户选择
        """
        from datetime import datetime
        
        # 确定查询时间
        if req.current_time:
            try:
                query_time = datetime.strptime(req.current_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return ErrorCode.INVALID_PARAMETER, None
        else:
            query_time = datetime.now()
        
        current_time_str = query_time.strftime("%Y-%m-%d %H:%M:%S")
        current_date = query_time.date()
        current_time_only = query_time.time()
        
        self.log.info(f"查询用户 {user_id} 在 {current_time_str} 有效的角色")
        
        # 查询所有启用的角色
        list_req = ApplicationRoleListRequest(
            page=1,
            size=100,
            status=ApplicationRoleStatus.ENABLED
        )
        err, page = self.list_roles(user_id, list_req)
        if err != ErrorCode.SUCCESS:
            return err, None
        
        active_roles: List[ApplicationRoleInfo] = []
        
        for role in page.items:
            # 解析角色时间设置
            daily_start, daily_end = self._parse_enable_time(role.enableTime or "")
            period_start, period_end = self._parse_enable_period(role.enablePeriod or "")
            
            # 检查是否在有效期内
            in_period = period_start.date() <= current_date <= period_end.date()
            in_daily_time = daily_start.time() <= current_time_only <= daily_end.time()
            
            if in_period and in_daily_time:
                active_roles.append(role)
                self.log.info(f"角色 '{role.name}' (ID: {role.id}) 在当前时间有效")
        
        has_multiple = len(active_roles) > 1
        
        # 处理用户指定的角色选择
        selected_role = None
        if req.selected_role_id is not None and active_roles:
            # 查找用户指定的角色是否在有效列表中
            for role in active_roles:
                if role.id == req.selected_role_id:
                    selected_role = role
                    self.log.info(f"用户指定选择角色 '{role.name}' (ID: {role.id})")
                    break
            if not selected_role:
                self.log.warning(f"用户指定的角色ID {req.selected_role_id} 不在有效角色列表中")
        
        # 如果没有指定选择且只有一个角色有效，自动选择第一个
        if selected_role is None and active_roles and not has_multiple:
            selected_role = active_roles[0]
        
        require_selection = has_multiple and req.require_selection and selected_role is None
        
        self.log.info(f"找到 {len(active_roles)} 个有效角色，已选择: {selected_role.name if selected_role else '无'}，需要选择: {require_selection}")
        
        result = ApplicationRoleActiveResult(
            roles=active_roles,
            has_multiple=has_multiple,
            require_selection=require_selection,
            selected_role=selected_role,
            current_time=current_time_str
        )
        
        return ErrorCode.SUCCESS, result
