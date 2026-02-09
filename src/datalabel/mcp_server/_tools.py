"""MCP 工具定义与处理函数."""

import json
from typing import Any

from mcp.types import TextContent, Tool

from datalabel.generator import AnnotatorGenerator
from datalabel.io import export_responses, extract_responses, import_tasks_from_file
from datalabel.merger import ResultMerger
from datalabel.validator import SchemaValidator

# 共享实例
_generator = AnnotatorGenerator()
_merger = ResultMerger()
_validator = SchemaValidator()

# ============================================================
# Tool 定义
# ============================================================

TOOLS = [
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
        name="validate_schema",
        description="验证 DataLabel Schema 和任务数据的格式正确性",
        inputSchema={
            "type": "object",
            "properties": {
                "schema": {
                    "type": "object",
                    "description": "待验证的 Schema 定义",
                },
                "tasks": {
                    "type": "array",
                    "description": "待验证的任务列表（可选）",
                },
            },
            "required": ["schema"],
        },
    ),
    Tool(
        name="export_results",
        description="将标注结果导出为 JSON/JSONL/CSV 格式",
        inputSchema={
            "type": "object",
            "properties": {
                "result_file": {
                    "type": "string",
                    "description": "标注结果 JSON 文件路径",
                },
                "output_path": {
                    "type": "string",
                    "description": "输出文件路径",
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "jsonl", "csv"],
                    "description": "输出格式 (默认: json)",
                },
            },
            "required": ["result_file", "output_path"],
        },
    ),
    Tool(
        name="import_tasks",
        description="从 JSON/JSONL/CSV 导入任务数据并转换为 DataLabel 格式",
        inputSchema={
            "type": "object",
            "properties": {
                "input_file": {
                    "type": "string",
                    "description": "输入文件路径 (JSON/JSONL/CSV)",
                },
                "output_path": {
                    "type": "string",
                    "description": "输出 JSON 文件路径",
                },
                "format": {
                    "type": "string",
                    "enum": ["json", "jsonl", "csv"],
                    "description": "输入格式 (默认: 自动检测)",
                },
            },
            "required": ["input_file", "output_path"],
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

# ============================================================
# Handler 函数（同步，可独立测试）
# ============================================================


def handle_generate_annotator(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 generate_annotator 工具调用."""
    result = _generator.generate_from_datarecipe(
        analysis_dir=arguments["analysis_dir"],
        output_path=arguments.get("output_path"),
    )
    if result.success:
        return [
            TextContent(
                type="text",
                text=(
                    f"标注界面已生成:\n"
                    f"- 输出路径: {result.output_path}\n"
                    f"- 任务数量: {result.task_count}\n\n"
                    f"在浏览器中打开此文件即可开始标注。"
                ),
            )
        ]
    return [TextContent(type="text", text=f"生成失败: {result.error}")]


def handle_create_annotator(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 create_annotator 工具调用."""
    result = _generator.generate(
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
                text=(
                    f"标注界面已创建:\n"
                    f"- 输出路径: {result.output_path}\n"
                    f"- 任务数量: {result.task_count}\n\n"
                    f"在浏览器中打开此文件即可开始标注。"
                ),
            )
        ]
    return [TextContent(type="text", text=f"创建失败: {result.error}")]


def handle_merge_annotations(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 merge_annotations 工具调用."""
    result = _merger.merge(
        result_files=arguments["result_files"],
        output_path=arguments["output_path"],
        strategy=arguments.get("strategy", "majority"),
    )
    if result.success:
        return [
            TextContent(
                type="text",
                text=(
                    f"标注结果已合并:\n"
                    f"- 输出路径: {result.output_path}\n"
                    f"- 任务总数: {result.total_tasks}\n"
                    f"- 标注员数: {result.annotator_count}\n"
                    f"- 一致率: {result.agreement_rate:.1%}\n"
                    f"- 冲突数: {len(result.conflicts)}"
                ),
            )
        ]
    return [TextContent(type="text", text=f"合并失败: {result.error}")]


def handle_calculate_iaa(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 calculate_iaa 工具调用."""
    metrics = _merger.calculate_iaa(arguments["result_files"])
    if "error" in metrics:
        return [TextContent(type="text", text=f"计算失败: {metrics['error']}")]
    return [
        TextContent(
            type="text",
            text=(
                f"标注员间一致性 (IAA) 指标:\n"
                f"- 标注员数: {metrics['annotator_count']}\n"
                f"- 共同任务: {metrics['common_tasks']}\n"
                f"- 完全一致率: {metrics['exact_agreement_rate']:.1%}\n\n"
                f"详细指标:\n{json.dumps(metrics, indent=2, ensure_ascii=False)}"
            ),
        )
    ]


def handle_validate_schema(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 validate_schema 工具调用."""
    parts = []
    schema_result = _validator.validate_schema(arguments["schema"])
    if schema_result.valid:
        parts.append("Schema 验证通过 ✓")
    else:
        parts.append("Schema 验证失败:")
        for e in schema_result.errors:
            parts.append(f"  - {e}")
    if schema_result.warnings:
        parts.append("警告:")
        for w in schema_result.warnings:
            parts.append(f"  - {w}")

    if "tasks" in arguments:
        task_result = _validator.validate_tasks(arguments["tasks"], arguments["schema"])
        if task_result.valid:
            parts.append(f"\n任务数据验证通过 ✓ ({len(arguments['tasks'])} 条)")
        else:
            parts.append("\n任务数据验证失败:")
            for e in task_result.errors:
                parts.append(f"  - {e}")
        if task_result.warnings:
            parts.append("警告:")
            for w in task_result.warnings:
                parts.append(f"  - {w}")

    return [TextContent(type="text", text="\n".join(parts))]


def handle_export_results(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 export_results 工具调用."""
    result_file = arguments["result_file"]
    output_path = arguments["output_path"]
    fmt = arguments.get("format", "json")

    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    responses = extract_responses(data)
    if responses is None:
        return [TextContent(type="text", text="导出失败: 无法识别的结果文件格式")]

    count = export_responses(responses, output_path, fmt)
    return [
        TextContent(
            type="text",
            text=f"导出成功: {output_path} ({fmt}, {count} 条)",
        )
    ]


def handle_import_tasks(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 import_tasks 工具调用."""
    input_file = arguments["input_file"]
    output_path = arguments["output_path"]
    fmt = arguments.get("format")

    tasks = import_tasks_from_file(input_file, fmt)

    from pathlib import Path

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    return [
        TextContent(
            type="text",
            text=f"导入成功: {output_path} ({len(tasks)} 条)",
        )
    ]


def handle_llm_prelabel(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 llm_prelabel 工具调用."""
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
                text=(
                    f"预标注完成:\n"
                    f"- 输出: {result.output_path}\n"
                    f"- 标注数: {result.labeled_tasks}/{result.total_tasks}\n"
                    f"- Token: {result.total_usage.total_tokens}"
                ),
            )
        ]
    return [TextContent(type="text", text=f"预标注失败: {result.error}")]


def handle_llm_quality_analysis(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 llm_quality_analysis 工具调用."""
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
                text=(
                    f"质量分析完成:\n{report.summary}{issues_text}\n"
                    f"Token: {report.total_usage.total_tokens}"
                ),
            )
        ]
    return [TextContent(type="text", text=f"质量分析失败: {report.error}")]


def handle_llm_gen_guidelines(arguments: dict[str, Any]) -> list[TextContent]:
    """处理 llm_gen_guidelines 工具调用."""
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
                text=(
                    f"标注指南已生成:\n"
                    f"- 输出: {result.output_path}\n"
                    f"- Token: {result.total_usage.total_tokens}"
                ),
            )
        ]
    return [TextContent(type="text", text=f"指南生成失败: {result.error}")]


# Handler 映射
TOOL_HANDLERS: dict[str, Any] = {
    "generate_annotator": handle_generate_annotator,
    "create_annotator": handle_create_annotator,
    "merge_annotations": handle_merge_annotations,
    "calculate_iaa": handle_calculate_iaa,
    "validate_schema": handle_validate_schema,
    "export_results": handle_export_results,
    "import_tasks": handle_import_tasks,
    "llm_prelabel": handle_llm_prelabel,
    "llm_quality_analysis": handle_llm_quality_analysis,
    "llm_gen_guidelines": handle_llm_gen_guidelines,
}


# ============================================================
# 注册到 MCP Server
# ============================================================


def register_tools(server: Any) -> None:
    """注册所有工具到 MCP 服务器."""

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[TextContent]:
        handler = TOOL_HANDLERS.get(name)
        if handler:
            return handler(arguments)
        return [TextContent(type="text", text=f"未知工具: {name}")]
