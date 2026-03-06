from datetime import datetime
from typing import Dict, List, Optional, Tuple
import asyncio
import re
import json
from openai import AsyncOpenAI

from infrastructure.config.sys_config import SysConfig
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.repositories.prompt_repository import PromptRepository
from interfaces.dto.prompt_dto import (
    PromptStatus,
    PromptVariable,
    PromptTemplateInfo,
    PromptTemplatePage,
    PromptTemplateListRequest,
    PromptTemplateSaveRequest,
    PromptTemplateIdRequest,
    PromptTemplateToggleStatusRequest,
    PromptTestType,
    PromptTestInfo,
    PromptAbTestRunRequest,
    PromptAbTestRunResult,
    PromptQuickTestRunRequest,
    PromptQuickTestRunResult,
    PromptBatchTestRunRequest,
    PromptBatchTestRunResult,
)


@logger()
class PromptService:
    def __init__(self, config: SysConfig, mysql_client=None):
        self.config = config
        self.repo = PromptRepository(config, mysql_client)
        
        # Initialize LLM Client
        system_config = self.config.get_system_config()
        vllm_config = system_config.get('vllm', {})
        llm_root_config = vllm_config.get('llm', {})
        
        llm_type = llm_root_config.get('type', 'hsyq')
        llm_config = llm_root_config.get(llm_type, {})
        
        self.llm_client = AsyncOpenAI(
            api_key=llm_config.get('key'),
            base_url=llm_config.get('base_url')
        )
        self.model = llm_config.get('model', 'doubao-seed-1-8-251228')

    def _status_db_to_enum(self, value: Optional[int]) -> PromptStatus:
        if value == 1:
            return PromptStatus.ENABLED
        if value == 0:
            return PromptStatus.DISABLED
        return PromptStatus.DRAFT

    def _status_enum_to_db(self, status: PromptStatus) -> int:
        if status == PromptStatus.ENABLED:
            return 1
        if status == PromptStatus.DISABLED:
            return 0
        return 2

    def _format_time(self, value: object) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if value is None:
            return ""
        return str(value)

    def _build_variable_models(self, rows: List[Dict[str, object]]) -> List[PromptVariable]:
        variables: List[PromptVariable] = []
        for row in rows:
            key = row.get("variable_name") or ""
            if not key:
                continue
            default_value = row.get("default_value")
            description = row.get("description")
            required = bool(row.get("is_required", 0))
            variables.append(
                PromptVariable(
                    key=str(key),
                    defaultValue=str(default_value) if default_value is not None else None,
                    description=str(description) if description is not None else None,
                    required=required,
                )
            )
        return variables

    def list_templates(
        self,
        req: PromptTemplateListRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptTemplatePage]]:
        page = req.page if req.page and req.page > 0 else 1
        size = req.size if req.size and req.size > 0 else 10
        size = min(size, 100)
        status_db: Optional[int] = None
        if req.status is not None:
            status_db = self._status_enum_to_db(req.status)
        err_count, total = self.repo.count_templates(creator_id, req.keyword, status_db)
        if err_count != ErrorCode.SUCCESS:
            return err_count, None
        if total == 0:
            page_obj = PromptTemplatePage(items=[], total=0, page=page, size=size)
            return ErrorCode.SUCCESS, page_obj
        offset = (page - 1) * size
        err_list, rows = self.repo.list_templates(creator_id, req.keyword, status_db, size, offset)
        if err_list != ErrorCode.SUCCESS:
            return err_list, None
        items: List[PromptTemplateInfo] = []
        for row in rows:
            template_id = int(row.get("id"))
            name = str(row.get("template_name") or "")
            content = str(row.get("template_content") or "")
            category = str(row.get("category") or "general")
            version = str(row.get("version") or "1.0.0")
            status_enum = self._status_db_to_enum(row.get("status"))
            created_at = self._format_time(row.get("created_at"))
            updated_at = self._format_time(row.get("updated_at"))
            items.append(
                PromptTemplateInfo(
                    id=template_id,
                    name=name,
                    content=content,
                    category=category,
                    version=version,
                    status=status_enum,
                    createdAt=created_at,
                    updatedAt=updated_at,
                    variables=[],
                )
            )
        page_obj = PromptTemplatePage(items=items, total=total, page=page, size=size)
        return ErrorCode.SUCCESS, page_obj

    def get_template(
        self,
        req: PromptTemplateIdRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptTemplateInfo]]:
        err, row = self.repo.get_template_by_id(req.id, creator_id)
        if err != ErrorCode.SUCCESS:
            return err, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
        err_var, vars_rows = self.repo.list_variables_by_template(req.id)
        if err_var != ErrorCode.SUCCESS:
            return err_var, None
        variables = self._build_variable_models(vars_rows)
        status_enum = self._status_db_to_enum(row.get("status"))
        created_at = self._format_time(row.get("created_at"))
        updated_at = self._format_time(row.get("updated_at"))
        info = PromptTemplateInfo(
            id=int(row.get("id")),
            name=str(row.get("template_name") or ""),
            content=str(row.get("template_content") or ""),
            category=str(row.get("category") or "general"),
            version=str(row.get("version") or "1.0.0"),
            status=status_enum,
            createdAt=created_at,
            updatedAt=updated_at,
            variables=variables,
        )
        return ErrorCode.SUCCESS, info

    def create_template(
        self,
        req: PromptTemplateSaveRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptTemplateInfo]]:
        name = req.name.strip()
        if not name:
            return ErrorCode.INVALID_PARAMETER, None
        content = req.content
        if not content:
            return ErrorCode.INVALID_PARAMETER, None
        status_enum = req.status or PromptStatus.DRAFT
        status_db = self._status_enum_to_db(status_enum)
        category = (req.category or "").strip() or "general"
        version = (req.version or "").strip() or "1.0.0"
        data = {
            "template_name": name,
            "template_content": content,
            "description": "",
            "category": category,
            "version": version,
            "status": status_db,
            "is_default": 0,
            "creator_id": creator_id,
        }
        err_ins, template_id = self.repo.insert_template(data)
        if err_ins != ErrorCode.SUCCESS or not template_id:
            return err_ins, None
        vars_rows: List[Dict[str, object]] = []
        for idx, v in enumerate(req.variables or []):
            key = (v.key or "").strip()
            if not key:
                continue
            row_var: Dict[str, object] = {
                "variable_name": key,
                "display_name": key,
                "default_value": v.defaultValue,
                "description": v.description,
                "data_type": "string",
                "is_required": 1 if v.required else 0,
                "validation_rule": None,
                "sort_order": idx,
            }
            vars_rows.append(row_var)
        if vars_rows:
            err_vars, _ = self.repo.insert_variables(template_id, vars_rows)
            if err_vars != ErrorCode.SUCCESS:
                return err_vars, None
        get_req = PromptTemplateIdRequest(id=template_id)
        return self.get_template(get_req, creator_id)

    def update_template(
        self,
        req: PromptTemplateSaveRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptTemplateInfo]]:
        if not req.id:
            return ErrorCode.MISSING_PARAMETER, None
        name = req.name.strip()
        if not name:
            return ErrorCode.INVALID_PARAMETER, None
        content = req.content
        if not content:
            return ErrorCode.INVALID_PARAMETER, None
        err_exist, row = self.repo.get_template_by_id(req.id, creator_id)
        if err_exist != ErrorCode.SUCCESS:
            return err_exist, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
        data: Dict[str, object] = {
            "template_name": name,
            "template_content": content,
        }
        if req.category is not None:
            data["category"] = (req.category or "").strip() or "general"
        if req.version is not None:
            data["version"] = (req.version or "").strip() or "1.0.0"
        if req.status is not None:
            data["status"] = self._status_enum_to_db(req.status)
        err_upd, _ = self.repo.update_template(req.id, data)
        if err_upd != ErrorCode.SUCCESS:
            return err_upd, None
        err_del, _ = self.repo.delete_variables_by_template(req.id)
        if err_del != ErrorCode.SUCCESS:
            return err_del, None
        vars_rows: List[Dict[str, object]] = []
        for idx, v in enumerate(req.variables or []):
            key = (v.key or "").strip()
            if not key:
                continue
            row_var: Dict[str, object] = {
                "variable_name": key,
                "display_name": key,
                "default_value": v.defaultValue,
                "description": v.description,
                "data_type": "string",
                "is_required": 1 if v.required else 0,
                "validation_rule": None,
                "sort_order": idx,
            }
            vars_rows.append(row_var)
        if vars_rows:
            err_vars, _ = self.repo.insert_variables(req.id, vars_rows)
            if err_vars != ErrorCode.SUCCESS:
                return err_vars, None
        get_req = PromptTemplateIdRequest(id=req.id)
        return self.get_template(get_req, creator_id)

    def delete_template(
        self,
        req: PromptTemplateIdRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[object]]:
        err_exist, row = self.repo.get_template_by_id(req.id, creator_id)
        if err_exist != ErrorCode.SUCCESS:
            return err_exist, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
        err_del_vars, _ = self.repo.delete_variables_by_template(req.id)
        if err_del_vars != ErrorCode.SUCCESS:
            return err_del_vars, None
        err_del_tpl, _ = self.repo.delete_template(req.id, creator_id)
        if err_del_tpl != ErrorCode.SUCCESS:
            return err_del_tpl, None
        return ErrorCode.SUCCESS, None

    def get_prompt_constant(
        self,
        user_id: int,
        application_type: str,
        prompt_type: str,
        current_time: Optional[str] = None
    ) -> Tuple[ErrorCode, Optional[str]]:
        """
        获取用户在指定时间的prompt
        
        Args:
            user_id: 用户ID
            application_type: 应用类型（如 agent-coordinator, agent-planning 等）
            prompt_type: prompt类型（如 system_prompt, user_prompt 等）
            current_time: 当前时间字符串（格式：YYYY-MM-DD HH:MM:SS），默认为None表示使用当前时间
        
        Returns:
            (ErrorCode, prompt内容)
        """
        # 如果没有提供时间，使用当前时间
        if current_time is None:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        err, row = self.repo.get_prompt_constant_at_time(user_id, application_type, prompt_type, current_time)
        if err != ErrorCode.SUCCESS or not row:
            return err, None
        return ErrorCode.SUCCESS, str(row.get("value") or "")

    def toggle_status(
        self,
        req: PromptTemplateToggleStatusRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptTemplateInfo]]:
        err_exist, row = self.repo.get_template_by_id(req.id, creator_id)
        if err_exist != ErrorCode.SUCCESS:
            return err_exist, None
        if not row:
            return ErrorCode.DATA_NOT_FOUND, None
        status_db = self._status_enum_to_db(req.status)
        err_upd, _ = self.repo.update_template(req.id, {"status": status_db})
        if err_upd != ErrorCode.SUCCESS:
            return err_upd, None
        get_req = PromptTemplateIdRequest(id=req.id)
        return self.get_template(get_req, creator_id)

    def _build_test_info(
        self,
        row: Dict[str, object],
        test_type: PromptTestType,
    ) -> PromptTestInfo:
        test_id = int(row.get("id"))
        name = str(row.get("test_name") or "")
        status = str(row.get("status") or "")
        total_cases = int(row.get("total_cases") or 0)
        passed_cases = int(row.get("passed_cases") or 0)
        failed_cases = int(row.get("failed_cases") or 0)
        created_at = self._format_time(row.get("created_at"))
        return PromptTestInfo(
            id=test_id,
            name=name,
            type=test_type,
            status=status,
            totalCases=total_cases,
            passedCases=passed_cases,
            failedCases=failed_cases,
            createdAt=created_at,
        )

    def _auto_fill_variables(
        self,
        content: str,
        variables: Optional[Dict[str, str]],
        input_text: str,
    ) -> Dict[str, str]:
        if variables:
            return variables

        if not input_text:
            return {}

        keys = re.findall(r'\{\{\s*([a-zA-Z0-9_]+)\s*\}\}', content)
        unique_keys = list(set(keys))

        if not unique_keys:
            return {}

        # Heuristic 1: If only 1 variable, use it
        if len(unique_keys) == 1:
            return {unique_keys[0]: input_text}

        # Heuristic 2: Check for common names
        common_names = ['input', 'text', 'question', 'query', 'content', 'user_input']
        for name in common_names:
            if name in unique_keys:
                return {name: input_text}

        # Fallback: Use the first one
        return {unique_keys[0]: input_text}

    async def _generate_response(self, content: str, variables: Dict[str, str]) -> str:
        # Replace variables in content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
            
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            self.log.error(f"LLM generation failed: {e}")
            return f"Error: {str(e)}"

    async def _generate_response_stream(self, content: str, variables: Dict[str, str]):
        # Replace variables in content
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
            
        try:
            stream = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                stream=True
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            self.log.error(f"LLM generation failed: {e}")
            yield f"Error: {str(e)}"

    async def run_ab_test(
        self,
        req: PromptAbTestRunRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptAbTestRunResult]]:
        if not req.templateAId or not req.templateBId:
            return ErrorCode.INVALID_PARAMETER, None
            
        # Fetch templates
        err_a, row_a = self.repo.get_template_by_id(req.templateAId, creator_id)
        if err_a != ErrorCode.SUCCESS or not row_a:
            return ErrorCode.DATA_NOT_FOUND, None
        
        err_b, row_b = self.repo.get_template_by_id(req.templateBId, creator_id)
        if err_b != ErrorCode.SUCCESS or not row_b:
            return ErrorCode.DATA_NOT_FOUND, None
            
        content_a = str(row_a.get("template_content") or "")
        content_b = str(row_b.get("template_content") or "")

        # Auto-fill variables
        vars_a = self._auto_fill_variables(content_a, req.variablesA, req.inputText)
        vars_b = self._auto_fill_variables(content_b, req.variablesB, req.inputText)

        # Generate responses
        task_a = self._generate_response(content_a, vars_a)
        task_b = self._generate_response(content_b, vars_b)
        res_a, res_b = await asyncio.gather(task_a, task_b)
        
        # Check results
        passed_cases = 0
        failed_cases = 0
        status_a = "success"
        status_b = "success"
        
        if res_a.startswith("Error:"):
            failed_cases += 1
            status_a = "failed"
        else:
            passed_cases += 1
            
        if res_b.startswith("Error:"):
            failed_cases += 1
            status_b = "failed"
        else:
            passed_cases += 1
        
        name = (req.name or "").strip() or "A/B Test"
        description = req.description or ""
        now = datetime.utcnow()
        data = {
            "test_name": name,
            "test_type": "ab_test",
            "description": description,
            "creator_id": creator_id,
            "status": "completed",
            "total_cases": 2,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "start_time": now,
            "end_time": now,
        }
        err_test, test_id = self.repo.insert_test(data)
        if err_test != ErrorCode.SUCCESS or not test_id:
            return err_test, None
        ab_data: Dict[str, object] = {
            "test_id": test_id,
            "template_a_id": req.templateAId,
            "template_b_id": req.templateBId,
            "test_input": req.inputText,
            "variables_a": req.variablesA or {},
            "variables_b": req.variablesB or {},
            "evaluation_criteria": [],
        }
        err_ab, _ = self.repo.insert_ab_test(ab_data)
        if err_ab != ErrorCode.SUCCESS:
            return err_ab, None
            
        # Store results
        cases = [
            {
                "test_id": test_id,
                "case_index": 1,
                "input_data": req.inputText,
                "variables": req.variablesA,
                "expected_output": "",
                "actual_output": res_a,
                "execution_status": status_a,
                "execution_time": 0,
                "executed_at": now
            },
            {
                "test_id": test_id,
                "case_index": 2,
                "input_data": req.inputText,
                "variables": req.variablesB,
                "expected_output": "",
                "actual_output": res_b,
                "execution_status": status_b,
                "execution_time": 0,
                "executed_at": now
            }
        ]
        self.repo.batch_insert_test_cases(cases)
            
        test_row = {
            "id": test_id,
            "test_name": name,
            "status": "completed",
            "total_cases": 2,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "created_at": now,
        }
        info = self._build_test_info(test_row, PromptTestType.AB_TEST)
        results = [
            {"template_id": req.templateAId, "output": res_a},
            {"template_id": req.templateBId, "output": res_b}
        ]
        result = PromptAbTestRunResult(test=info, results=results)
        return ErrorCode.SUCCESS, result

    async def run_quick_test(
        self,
        req: PromptQuickTestRunRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptQuickTestRunResult]]:
        if not req.templateId:
            return ErrorCode.INVALID_PARAMETER, None
            
        # Fetch template
        err, row = self.repo.get_template_by_id(req.templateId, creator_id)
        if err != ErrorCode.SUCCESS or not row:
            return ErrorCode.DATA_NOT_FOUND, None
        content = str(row.get("template_content") or "")
        
        # Generate response
        vars = self._auto_fill_variables(content, req.variables, req.inputText)
        res = await self._generate_response(content, vars)
        
        passed_cases = 0
        failed_cases = 0
        status = "success"
        if res.startswith("Error:"):
            failed_cases = 1
            status = "failed"
        else:
            passed_cases = 1
            
        name = (req.name or "").strip() or "Quick Test"
        description = req.description or ""
        now = datetime.utcnow()
        data = {
            "test_name": name,
            "test_type": "quick_test",
            "description": description,
            "creator_id": creator_id,
            "status": "completed",
            "total_cases": 1,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "start_time": now,
            "end_time": now,
        }
        err_test, test_id = self.repo.insert_test(data)
        if err_test != ErrorCode.SUCCESS or not test_id:
            return err_test, None
        case_row = {
            "test_id": test_id,
            "case_index": 1,
            "input_data": req.inputText,
            "variables": req.variables or {},
            "expected_output": "",
            "actual_output": res,
            "execution_status": status,
            "execution_time": 0,
            "similarity_score": None,
            "evaluation_result": {},
            "error_message": res if status == "failed" else None,
            "executed_at": now,
        }
        err_case, _ = self.repo.batch_insert_test_cases([case_row])
        if err_case != ErrorCode.SUCCESS:
            return err_case, None
        test_row = {
            "id": test_id,
            "test_name": name,
            "status": "completed",
            "total_cases": 1,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "created_at": now,
        }
        info = self._build_test_info(test_row, PromptTestType.QUICK_TEST)
        result = PromptQuickTestRunResult(test=info, output=res)
        return ErrorCode.SUCCESS, result

    async def run_batch_test(
        self,
        req: PromptBatchTestRunRequest,
        creator_id: int,
    ) -> Tuple[ErrorCode, Optional[PromptBatchTestRunResult]]:
        if not req.templateId:
            return ErrorCode.INVALID_PARAMETER, None
            
        # Fetch template
        err, row = self.repo.get_template_by_id(req.templateId, creator_id)
        if err != ErrorCode.SUCCESS or not row:
            return ErrorCode.DATA_NOT_FOUND, None
        content = str(row.get("template_content") or "")

        valid_cases = req.cases or []
        if not valid_cases:
             return ErrorCode.INVALID_PARAMETER, None
        
        # Prepare tasks
        tasks = []
        for case in valid_cases:
            vars = self._auto_fill_variables(content, case.variables, case.inputData)
            tasks.append(self._generate_response(content, vars))
            
        results = await asyncio.gather(*tasks)
        
        passed_cases = 0
        failed_cases = 0
        case_results = []
        
        now = datetime.utcnow()
        
        for idx, res in enumerate(results):
            case = valid_cases[idx]
            status = "success"
            error_msg = None
            
            if res.startswith("Error:"):
                failed_cases += 1
                status = "failed"
                error_msg = res
            else:
                passed_cases += 1
                
            case_result = {
                "test_id": 0, # Placeholder
                "case_index": case.index,
                "input_data": case.inputData,
                "variables": case.variables or {},
                "expected_output": case.expectedOutput,
                "actual_output": res,
                "execution_status": status,
                "execution_time": 0,
                "error_message": error_msg,
                "executed_at": now
            }
            case_results.append(case_result)

        name = (req.name or "").strip() or "Batch Test"
        description = req.description or ""
        
        test_data = {
            "test_name": name,
            "test_type": "batch_test",
            "description": description,
            "creator_id": creator_id,
            "status": "completed",
            "total_cases": len(valid_cases),
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "start_time": now,
            "end_time": now,
        }
        
        err_test, test_id = self.repo.insert_test(test_data)
        if err_test != ErrorCode.SUCCESS or not test_id:
            return err_test, None
            
        # Update test_id in cases
        for cr in case_results:
            cr["test_id"] = test_id
            
        # Batch insert cases
        err_case, _ = self.repo.batch_insert_test_cases(case_results)
        if err_case != ErrorCode.SUCCESS:
            return err_case, None
            
        test_row = {
            "id": test_id,
            "test_name": name,
            "status": "completed",
            "total_cases": len(valid_cases),
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "created_at": now,
        }
        
        info = self._build_test_info(test_row, PromptTestType.BATCH_TEST)
        
        # Build result list for response
        result_list = []
        for cr in case_results:
            result_list.append({
                "case_index": cr["case_index"],
                "output": cr["actual_output"],
                "status": cr["execution_status"]
            })
            
        result = PromptBatchTestRunResult(test=info, results=result_list)
        return ErrorCode.SUCCESS, result

    async def run_quick_test_stream(
        self,
        req: PromptQuickTestRunRequest,
        creator_id: int,
    ):
        if not req.templateId:
            yield "Error: Invalid parameter"
            return
            
        # Fetch template
        err, row = self.repo.get_template_by_id(req.templateId, creator_id)
        if err != ErrorCode.SUCCESS or not row:
            yield "Error: Template not found"
            return
        content = str(row.get("template_content") or "")
        
        # Generate response
        vars = self._auto_fill_variables(content, req.variables, req.inputText)
        
        full_response = []
        async for chunk in self._generate_response_stream(content, vars):
            full_response.append(chunk)
            yield chunk
            
        res = "".join(full_response)
        
        passed_cases = 0
        failed_cases = 0
        status = "success"
        if res.startswith("Error:"):
            failed_cases = 1
            status = "failed"
        else:
            passed_cases = 1
            
        name = (req.name or "").strip() or "Quick Test"
        description = req.description or ""
        now = datetime.utcnow()
        data = {
            "test_name": name,
            "test_type": "quick_test",
            "description": description,
            "creator_id": creator_id,
            "status": "completed",
            "total_cases": 1,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "start_time": now,
            "end_time": now,
        }
        err_test, test_id = self.repo.insert_test(data)
        if err_test != ErrorCode.SUCCESS or not test_id:
            # yield f"\nError saving test result: {err_test}"
            return

        case_row = {
            "test_id": test_id,
            "case_index": 1,
            "input_data": req.inputText,
            "variables": req.variables or {},
            "expected_output": "",
            "actual_output": res,
            "execution_status": status,
            "execution_time": 0,
            "similarity_score": None,
            "evaluation_result": {},
            "error_message": res if status == "failed" else None,
            "executed_at": now,
        }
        self.repo.batch_insert_test_cases([case_row])

    async def run_ab_test_stream(
        self,
        req: PromptAbTestRunRequest,
        creator_id: int,
    ):
        if not req.templateAId or not req.templateBId:
            yield json.dumps({"error": "Invalid parameter"})
            return
            
        # Fetch templates
        err_a, row_a = self.repo.get_template_by_id(req.templateAId, creator_id)
        if err_a != ErrorCode.SUCCESS or not row_a:
            yield json.dumps({"error": "Template A not found"})
            return
        
        err_b, row_b = self.repo.get_template_by_id(req.templateBId, creator_id)
        if err_b != ErrorCode.SUCCESS or not row_b:
            yield json.dumps({"error": "Template B not found"})
            return
            
        content_a = str(row_a.get("template_content") or "")
        content_b = str(row_b.get("template_content") or "")

        vars_a = self._auto_fill_variables(content_a, req.variablesA, req.inputText)
        vars_b = self._auto_fill_variables(content_b, req.variablesB, req.inputText)
        
        queue = asyncio.Queue()
        full_a = []
        full_b = []

        async def produce(tag, content, vars, storage):
            try:
                async for chunk in self._generate_response_stream(content, vars):
                    storage.append(chunk)
                    await queue.put({"tag": tag, "chunk": chunk})
            except Exception as e:
                await queue.put({"tag": tag, "error": str(e)})
            finally:
                await queue.put({"tag": tag, "done": True})

        tasks = [
            asyncio.create_task(produce("A", content_a, vars_a, full_a)),
            asyncio.create_task(produce("B", content_b, vars_b, full_b))
        ]
        
        done_count = 0
        while done_count < 2:
            item = await queue.get()
            if "done" in item:
                done_count += 1
            else:
                yield json.dumps(item, ensure_ascii=False) + "\n"
                
        # Save results
        res_a = "".join(full_a)
        res_b = "".join(full_b)
        
        passed_cases = 0
        failed_cases = 0
        status_a = "success"
        status_b = "success"
        
        if res_a.startswith("Error:"):
            failed_cases += 1
            status_a = "failed"
        else:
            passed_cases += 1
            
        if res_b.startswith("Error:"):
            failed_cases += 1
            status_b = "failed"
        else:
            passed_cases += 1
        
        name = (req.name or "").strip() or "A/B Test"
        description = req.description or ""
        now = datetime.utcnow()
        data = {
            "test_name": name,
            "test_type": "ab_test",
            "description": description,
            "creator_id": creator_id,
            "status": "completed",
            "total_cases": 2,
            "passed_cases": passed_cases,
            "failed_cases": failed_cases,
            "start_time": now,
            "end_time": now,
        }
        err_test, test_id = self.repo.insert_test(data)
        if err_test != ErrorCode.SUCCESS or not test_id:
            return

        ab_data: Dict[str, object] = {
            "test_id": test_id,
            "template_a_id": req.templateAId,
            "template_b_id": req.templateBId,
            "test_input": req.inputText,
            "variables_a": req.variablesA or {},
            "variables_b": req.variablesB or {},
            "evaluation_criteria": [],
        }
        self.repo.insert_ab_test(ab_data)
            
        cases = [
            {
                "test_id": test_id,
                "case_index": 1,
                "input_data": req.inputText,
                "variables": req.variablesA,
                "expected_output": "",
                "actual_output": res_a,
                "execution_status": status_a,
                "execution_time": 0,
                "executed_at": now
            },
            {
                "test_id": test_id,
                "case_index": 2,
                "input_data": req.inputText,
                "variables": req.variablesB,
                "expected_output": "",
                "actual_output": res_b,
                "execution_status": status_b,
                "execution_time": 0,
                "executed_at": now
            }
        ]
        self.repo.batch_insert_test_cases(cases)
