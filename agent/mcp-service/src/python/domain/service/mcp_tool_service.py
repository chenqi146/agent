import importlib
import pkgutil
import inspect
from typing import List, Dict, Any, Optional
from domain.model.tool import BaseTool, InterfaceType
from infrastructure.repositories.mcp_tool_repository import McpToolRepository
from interfaces.dto.mcp_tool_dto import ToolExecutionRequest, ToolExecutionResponse, InterfaceType, ToolType
from infrastructure.common.logging.logging import logger
from infrastructure.common.error.errcode import ErrorCode
from infrastructure.client.embedding_client import EmbeddingClient
from infrastructure.persistences.qdrant_persistence import QDrantPersistence

@logger()
class McpToolService:
    def __init__(self, repository: McpToolRepository, embedding_client: EmbeddingClient = None, qdrant_client: QDrantPersistence = None):
        self.repo = repository
        self.embedding_client = embedding_client
        self.qdrant_client = qdrant_client
        self.tools_registry: Dict[str, BaseTool] = {}
        
        # Init Qdrant collection if client exists
        if self.qdrant_client:
            try:
                self.qdrant_client.init_collection("mcp_tools")
            except Exception as e:
                self.log.error(f"Failed to init Qdrant collection: {e}")

        self._load_tools()

    def _load_tools(self):
        """
        Dynamically load tools from the tools directory
        """
        from domain.service import tools
        
        # Walk through the tools package
        for _, name, is_pkg in pkgutil.iter_modules(tools.__path__):
            if not is_pkg:
                module_name = f"domain.service.tools.{name}"
                try:
                    module = importlib.import_module(module_name)
                    for attribute_name in dir(module):
                        attribute = getattr(module, attribute_name)
                        if (inspect.isclass(attribute) and 
                            issubclass(attribute, BaseTool) and 
                            attribute is not BaseTool):
                            # Instantiate and register
                            tool_instance = attribute()
                            self.tools_registry[tool_instance.name] = tool_instance
                            self.log.info(f"Loaded tool: {tool_instance.name}")
                            
                            # Auto-register to DB
                            self._register_tool_to_db(tool_instance)
                except Exception as e:
                    self.log.error(f"Failed to load module {module_name}: {e}")

    def _register_tool_to_db(self, tool: BaseTool):
        """
        Register or update tool in the database
        """
        try:
            err, existing_tool = self.repo.get_tool_by_name(tool.name)
            if err != ErrorCode.SUCCESS:
                self.log.error(f"Error checking tool {tool.name}: {err}")
                return

            definition = tool.get_definition()
            
            tool_data = {
                "name": tool.name,
                "display_name": tool.name, # Can be enhanced
                "description_short": tool.description[:100],
                "description_full": tool.description,
                "tool_type": ToolType.FUNCTION,
                "category": "utility", # Default
                "tags": getattr(tool, "tags", []),
                # "primary_skill_id": None # Removed in decoupled table
            }

            if not existing_tool:
                err, tool_id = self.repo.create_tool(tool_data)
                if err == ErrorCode.SUCCESS:
                    self.log.info(f"Registered new tool in DB: {tool.name} (ID: {tool_id})")
            else:
                tool_id = existing_tool['id']
                # Update existing tool
                self.repo.update_tool(tool_id, tool_data)
                self.log.info(f"Updated tool in DB: {tool.name}")

            # Register Interfaces (Full & Compact)
            import json
            for interface_type in [InterfaceType.FULL, InterfaceType.COMPACT]:
                definition = tool.get_definition(interface_type)
                interface_data = {
                    "tool_id": tool_id,
                    "interface_type": interface_type.value,
                    "version": "v1", # Default version
                    "is_default": 1 if interface_type == InterfaceType.FULL else 0,
                    "endpoint_url": f"/v1/tools/{tool.name}/execute", # Generic execution endpoint
                    "description": definition.get("description", ""),
                    "input_schema": json.dumps(definition.get("input_schema", {}), ensure_ascii=False),
                    "estimated_token_length": 0
                }
                self.repo.create_tool_interface(interface_data)
                
            # Sync to RAG
            self.sync_tool_to_rag(tool)

        except Exception as e:
            self.log.error(f"Failed to register tool {tool.name}: {e}")

    def sync_tool_to_rag(self, tool: BaseTool):
        """
        Sync tool description to RAG knowledge base
        """
        if not self.embedding_client or not self.qdrant_client:
            self.log.warning("RAG clients not initialized, skipping sync")
            return

        try:
            # Use full definition for RAG
            definition = tool.get_definition(InterfaceType.FULL)
            text_to_embed = f"Tool Name: {tool.name}\nDescription: {definition.get('description')}\nSchema: {definition.get('input_schema')}"
            
            # Get target dimension from Qdrant client
            target_dim = getattr(self.qdrant_client, 'vector_size', 512)
            err, embeddings = self.embedding_client.embed([text_to_embed], dimensions=target_dim)
            
            if err != ErrorCode.SUCCESS or not embeddings:
                self.log.error(f"Failed to embed tool {tool.name}")
                return

            # Use a consistent integer ID for the tool
            # In production, use UUID or hash
            import hashlib
            tool_hash = int(hashlib.md5(tool.name.encode()).hexdigest(), 16) % (2**63 - 1)
            
            from qdrant_client.models import PointStruct
            
            point = PointStruct(
                id=tool_hash,
                vector=embeddings[0],
                payload={
                    "name": tool.name,
                    "description": definition.get("description"),
                    "schema": definition.get("input_schema")
                }
            )
            
            self.qdrant_client.client.upsert(
                collection_name="mcp_tools",
                points=[point]
            )
            self.log.info(f"Synced tool {tool.name} to RAG")
        except Exception as e:
            self.log.error(f"Failed to sync tool {tool.name} to RAG: {e}")

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResponse:
        tool_name = request.tool_name
        
        if tool_name not in self.tools_registry:
            return ToolExecutionResponse(
                status="error",
                error_message=f"Tool {tool_name} not found"
            )
        
        tool = self.tools_registry[tool_name]
        
        try:
            result = tool.execute(request.arguments)
            return ToolExecutionResponse(
                status="success",
                result=result
            )
        except Exception as e:
            self.log.error(f"Error executing tool {tool_name}: {e}")
            return ToolExecutionResponse(
                status="error",
                error_message=str(e)
            )

    def list_tools(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        err, tools, total = self.repo.list_tools(page, page_size)
        if err != ErrorCode.SUCCESS:
            return {"items": [], "total": 0}
        return {"items": tools, "total": total}

    def get_tool_definition(self, tool_name: str, interface_type: InterfaceType = InterfaceType.FULL) -> Optional[Dict[str, Any]]:
        # This would retrieve the specific interface definition from DB
        # For now, return from code if available
        if tool_name in self.tools_registry:
            return self.tools_registry[tool_name].get_definition()
        return None
