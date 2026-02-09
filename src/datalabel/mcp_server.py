"""DataLabel MCP Server - Model Context Protocol 服务."""

import json
from typing import Any, Dict, List

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from datalabel.generator import AnnotatorGenerator
from datalabel.merger import ResultMerger


def create_server() -> "Server":
    """创建 MCP 服务器实例."""
    if not HAS_MCP:
        raise ImportError("MCP 未安装。请运行: pip install datalabel[mcp]")

    server = Server("datalabel")
    generator = AnnotatorGenerator()
    merger = ResultMerger()

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """列出可用的工具."""
        return [
            Tool(
                name="generate_annotator",
                description="从 DataRecipe 分析结果生成 HTML 标注界面",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "analysis_dir": {
                            "type": "string",
                            "description": "DataRecipe 分析输出目录的路径",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出 HTML 文件路径（可选）",
                        },
                    },
                    "required": ["analysis_dir"],
                },
            ),
            Tool(
                name="create_annotator",
                description="从 Schema 和任务数据创建 HTML 标注界面",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schema": {
                            "type": "object",
                            "description": "数据 Schema 定义。支持 scoring_rubric（评分）或 annotation_config（单选/多选/文本/排序）",
                        },
                        "tasks": {
                            "type": "array",
                            "description": "待标注任务列表",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出 HTML 文件路径",
                        },
                        "guidelines": {
                            "type": "string",
                            "description": "标注指南（Markdown 格式）",
                        },
                        "title": {
                            "type": "string",
                            "description": "标注界面标题",
                        },
                    },
                    "required": ["schema", "tasks", "output_path"],
                },
            ),
            Tool(
                name="merge_annotations",
                description="合并多个标注员的标注结果",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "result_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "标注结果 JSON 文件路径列表",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "合并结果输出路径",
                        },
                        "strategy": {
                            "type": "string",
                            "enum": ["majority", "average", "strict"],
                            "description": "合并策略（默认: majority）",
                        },
                    },
                    "required": ["result_files", "output_path"],
                },
            ),
            Tool(
                name="calculate_iaa",
                description="计算标注员间一致性 (Inter-Annotator Agreement)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "result_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "标注结果 JSON 文件路径列表",
                        },
                    },
                    "required": ["result_files"],
                },
            ),
            Tool(
                name="llm_prelabel",
                description="使用 LLM 自动预标注任务数据",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schema": {
                            "type": "object",
                            "description": "标注规范 Schema",
                        },
                        "tasks": {
                            "type": "array",
                            "description": "待标注任务列表",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出文件路径",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["moonshot", "openai", "anthropic"],
                            "description": "LLM 提供商 (默认: moonshot)",
                        },
                        "model": {
                            "type": "string",
                            "description": "模型名称（可选）",
                        },
                        "batch_size": {
                            "type": "integer",
                            "description": "每批任务数 (默认: 5)",
                        },
                    },
                    "required": ["schema", "tasks", "output_path"],
                },
            ),
            Tool(
                name="llm_quality_analysis",
                description="使用 LLM 分析标注质量，检测可疑标注和分歧",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schema": {
                            "type": "object",
                            "description": "标注规范 Schema",
                        },
                        "result_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "标注结果文件路径列表",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "报告输出路径（可选）",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["moonshot", "openai", "anthropic"],
                            "description": "LLM 提供商 (默认: moonshot)",
                        },
                        "model": {
                            "type": "string",
                            "description": "模型名称（可选）",
                        },
                    },
                    "required": ["schema", "result_files"],
                },
            ),
            Tool(
                name="llm_gen_guidelines",
                description="使用 LLM 根据 Schema 和样例自动生成标注指南",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schema": {
                            "type": "object",
                            "description": "标注规范 Schema",
                        },
                        "tasks": {
                            "type": "array",
                            "description": "样例任务列表（可选）",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "输出文件路径 (Markdown)",
                        },
                        "provider": {
                            "type": "string",
                            "enum": ["moonshot", "openai", "anthropic"],
                            "description": "LLM 提供商 (默认: moonshot)",
                        },
                        "model": {
                            "type": "string",
                            "description": "模型名称（可选）",
                        },
                        "language": {
                            "type": "string",
                            "enum": ["zh", "en"],
                            "description": "指南语言 (默认: zh)",
                        },
                    },
                    "required": ["schema", "output_path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """调用工具."""

        if name == "generate_annotator":
            result = generator.generate_from_datarecipe(
                analysis_dir=arguments["analysis_dir"],
                output_path=arguments.get("output_path"),
            )

            if result.success:
                return [
                    TextContent(
                        type="text",
                        text=f"标注界面已生成:\n"
                        f"- 输出路径: {result.output_path}\n"
                        f"- 任务数量: {result.task_count}\n\n"
                        f"在浏览器中打开此文件即可开始标注。",
                    )
                ]
            else:
                return [TextContent(type="text", text=f"生成失败: {result.error}")]

        elif name == "create_annotator":
            result = generator.generate(
                schema=arguments["schema"],
                tasks=arguments["tasks"],
                output_path=arguments["output_path"],
                guidelines=arguments.get("guidelines"),
                title=arguments.get("title"),
            )

            if result.success:
                return [
                    TextContent(
                        type="text",
                        text=f"标注界面已创建:\n"
                        f"- 输出路径: {result.output_path}\n"
                        f"- 任务数量: {result.task_count}\n\n"
                        f"在浏览器中打开此文件即可开始标注。",
                    )
                ]
            else:
                return [TextContent(type="text", text=f"创建失败: {result.error}")]

        elif name == "merge_annotations":
            result = merger.merge(
                result_files=arguments["result_files"],
                output_path=arguments["output_path"],
                strategy=arguments.get("strategy", "majority"),
            )

            if result.success:
                return [
                    TextContent(
                        type="text",
                        text=f"标注结果已合并:\n"
                        f"- 输出路径: {result.output_path}\n"
                        f"- 任务总数: {result.total_tasks}\n"
                        f"- 标注员数: {result.annotator_count}\n"
                        f"- 一致率: {result.agreement_rate:.1%}\n"
                        f"- 冲突数: {len(result.conflicts)}",
                    )
                ]
            else:
                return [TextContent(type="text", text=f"合并失败: {result.error}")]

        elif name == "calculate_iaa":
            metrics = merger.calculate_iaa(arguments["result_files"])

            if "error" in metrics:
                return [TextContent(type="text", text=f"计算失败: {metrics['error']}")]

            return [
                TextContent(
                    type="text",
                    text=f"标注员间一致性 (IAA) 指标:\n"
                    f"- 标注员数: {metrics['annotator_count']}\n"
                    f"- 共同任务: {metrics['common_tasks']}\n"
                    f"- 完全一致率: {metrics['exact_agreement_rate']:.1%}\n\n"
                    f"详细指标:\n{json.dumps(metrics, indent=2, ensure_ascii=False)}",
                )
            ]

        elif name == "llm_prelabel":
            from datalabel.llm import LLMClient, LLMConfig, PreLabeler

            provider = arguments.get("provider", "moonshot")
            config = LLMConfig(provider=provider, model=arguments.get("model"))
            client = LLMClient(config=config)
            labeler = PreLabeler(client=client)

            result = labeler.prelabel(
                schema=arguments["schema"],
                tasks=arguments["tasks"],
                output_path=arguments["output_path"],
                batch_size=arguments.get("batch_size", 5),
            )

            if result.success:
                return [
                    TextContent(
                        type="text",
                        text=f"预标注完成:\n"
                        f"- 输出: {result.output_path}\n"
                        f"- 标注数: {result.labeled_tasks}/{result.total_tasks}\n"
                        f"- Token: {result.total_usage.total_tokens}",
                    )
                ]
            else:
                return [TextContent(type="text", text=f"预标注失败: {result.error}")]

        elif name == "llm_quality_analysis":
            from datalabel.llm import LLMClient, LLMConfig, QualityAnalyzer

            provider = arguments.get("provider", "moonshot")
            config = LLMConfig(provider=provider, model=arguments.get("model"))
            client = LLMClient(config=config)
            analyzer = QualityAnalyzer(client=client)

            report = analyzer.analyze(
                schema=arguments["schema"],
                result_files=arguments["result_files"],
                output_path=arguments.get("output_path"),
            )

            if report.success:
                issues_text = ""
                if report.issues:
                    issues_text = "\n问题列表:\n" + "\n".join(
                        f"- [{i.severity}] {i.task_id}: {i.description}"
                        for i in report.issues
                    )
                return [
                    TextContent(
                        type="text",
                        text=f"质量分析完成:\n{report.summary}{issues_text}\n"
                        f"Token: {report.total_usage.total_tokens}",
                    )
                ]
            else:
                return [TextContent(type="text", text=f"质量分析失败: {report.error}")]

        elif name == "llm_gen_guidelines":
            from datalabel.llm import GuidelinesGenerator, LLMClient, LLMConfig

            provider = arguments.get("provider", "moonshot")
            config = LLMConfig(provider=provider, model=arguments.get("model"))
            client = LLMClient(config=config)
            gen = GuidelinesGenerator(client=client)

            result = gen.generate(
                schema=arguments["schema"],
                tasks=arguments.get("tasks"),
                output_path=arguments["output_path"],
                language=arguments.get("language", "zh"),
            )

            if result.success:
                return [
                    TextContent(
                        type="text",
                        text=f"标注指南已生成:\n"
                        f"- 输出: {result.output_path}\n"
                        f"- Token: {result.total_usage.total_tokens}",
                    )
                ]
            else:
                return [TextContent(type="text", text=f"指南生成失败: {result.error}")]

        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]

    return server


async def serve():
    """启动 MCP 服务器."""
    if not HAS_MCP:
        raise ImportError("MCP 未安装。请运行: pip install datalabel[mcp]")

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


def main():
    """主入口."""
    import asyncio

    asyncio.run(serve())


if __name__ == "__main__":
    main()
