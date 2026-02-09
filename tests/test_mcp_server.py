"""MCP Server 集成测试."""

import inspect

from datalabel.mcp_server import create_server, main, serve
from datalabel.mcp_server._tools import TOOLS, TOOL_HANDLERS
from datalabel.mcp_server._resources import SCHEMA_TEMPLATES
from datalabel.mcp_server._prompts import PROMPTS


class TestServerCreation:
    """测试服务器创建."""

    def test_create_server_returns_server(self):
        server = create_server()
        assert server is not None

    def test_create_server_name(self):
        server = create_server()
        assert server.name == "datalabel"

    def test_serve_is_async(self):
        assert inspect.iscoroutinefunction(serve)

    def test_main_is_callable(self):
        assert callable(main)


class TestRegistrationCompleteness:
    """测试注册完整性."""

    def test_tool_definitions(self):
        assert len(TOOLS) == 11
        names = {t.name for t in TOOLS}
        expected = {
            "generate_annotator",
            "create_annotator",
            "merge_annotations",
            "calculate_iaa",
            "validate_schema",
            "export_results",
            "import_tasks",
            "generate_dashboard",
            "llm_prelabel",
            "llm_quality_analysis",
            "llm_gen_guidelines",
        }
        assert names == expected

    def test_resource_templates(self):
        assert len(SCHEMA_TEMPLATES) == 5

    def test_prompt_definitions(self):
        assert len(PROMPTS) == 3

    def test_handler_for_every_tool(self):
        for tool in TOOLS:
            assert tool.name in TOOL_HANDLERS, f"缺少 handler: {tool.name}"
