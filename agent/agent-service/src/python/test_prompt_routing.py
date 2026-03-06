import unittest
import os
import sys
from unittest.mock import MagicMock, AsyncMock

current_dir = os.path.dirname(os.path.abspath(__file__))
agent_service_src = os.path.join(os.path.dirname(current_dir), "agent-service", "src", "python")
sys.path.insert(0, agent_service_src)

from domain.service.agent_service import AgentService
from infrastructure.common.error.errcode import ErrorCode
from interfaces.dto.role_dto import ApplicationRoleInfo
from interfaces.dto.prompt_dto import PromptTemplateInfo, PromptVariable


class TestPromptRouting(unittest.IsolatedAsyncioTestCase):
    def _make_service(self) -> AgentService:
        service = AgentService.__new__(AgentService)
        service.role_service = MagicMock()
        service.prompt_service = MagicMock()
        service.llm_client = MagicMock()
        service.llm_client.chat = MagicMock()
        service.llm_client.chat.completions = MagicMock()
        service.llm_client.chat.completions.create = AsyncMock()
        service.model = "mock-model"
        service.log = MagicMock()
        return service

    async def test_single_prompt_no_routing(self):
        service = self._make_service()
        role = ApplicationRoleInfo(
            id=1,
            name="r",
            mode="fixed",
            promptId=11,
            fixedPrompts=[],
            dynamicPrompts=[],
            customPrompt="custom",
        )
        service.role_service.get_role.return_value = (ErrorCode.SUCCESS, role)
        template = PromptTemplateInfo(id=11, name="p", content="hello")
        service.prompt_service.get_template.return_value = (ErrorCode.SUCCESS, template)

        out = await service._resolve_system_prompt(1, 1, "hi")
        self.assertEqual(out, "hello")
        service.llm_client.chat.completions.create.assert_not_awaited()

    async def test_multiple_prompts_routes_to_selected(self):
        service = self._make_service()
        role = ApplicationRoleInfo(
            id=1,
            name="r",
            mode="dynamic",
            promptId=None,
            fixedPrompts=[],
            dynamicPrompts=[1, 2],
            customPrompt="custom",
        )
        service.role_service.get_role.return_value = (ErrorCode.SUCCESS, role)

        template1 = PromptTemplateInfo(id=1, name="p1", content="P1")
        template2 = PromptTemplateInfo(
            id=2,
            name="p2",
            content="time={{current_time}}",
            variables=[PromptVariable(key="current_time")],
        )
        service.prompt_service.get_template.side_effect = [
            (ErrorCode.SUCCESS, template1),
            (ErrorCode.SUCCESS, template2),
            (ErrorCode.SUCCESS, template2),
        ]

        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content='{"prompt_id": 2}'))]
        service.llm_client.chat.completions.create.return_value = resp

        out = await service._resolve_system_prompt(1, 1, "hi")
        self.assertRegex(out, r"^time=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    async def test_multiple_prompts_invalid_llm_response_fallback(self):
        service = self._make_service()
        role = ApplicationRoleInfo(
            id=1,
            name="r",
            mode="dynamic",
            promptId=None,
            fixedPrompts=[],
            dynamicPrompts=[1, 2],
            customPrompt="custom",
        )
        service.role_service.get_role.return_value = (ErrorCode.SUCCESS, role)

        template1 = PromptTemplateInfo(id=1, name="p1", content="P1")
        template2 = PromptTemplateInfo(id=2, name="p2", content="P2")
        service.prompt_service.get_template.side_effect = [
            (ErrorCode.SUCCESS, template1),
            (ErrorCode.SUCCESS, template2),
            (ErrorCode.SUCCESS, template1),
        ]

        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content="no"))]
        service.llm_client.chat.completions.create.return_value = resp

        out = await service._resolve_system_prompt(1, 1, "hi")
        self.assertEqual(out, "P1")


if __name__ == "__main__":
    unittest.main()
