"""MCP Prompt 模板定义."""

import json
from typing import Any

from mcp.types import Prompt, PromptArgument, PromptMessage, TextContent

from datalabel.mcp_server._resources import SCHEMA_TEMPLATES

# ============================================================
# Prompt 定义
# ============================================================

PROMPTS = [
    Prompt(
        name="create-annotation-schema",
        description="根据标注任务描述生成 DataLabel Schema",
        arguments=[
            PromptArgument(
                name="task_description",
                description="标注任务的自然语言描述",
                required=True,
            ),
            PromptArgument(
                name="annotation_type",
                description="标注类型: scoring, single_choice, multi_choice, text, ranking",
                required=False,
            ),
        ],
    ),
    Prompt(
        name="review-annotations",
        description="分析标注结果，检查质量和一致性",
        arguments=[
            PromptArgument(
                name="schema",
                description="标注规范 Schema (JSON 字符串)",
                required=True,
            ),
            PromptArgument(
                name="results",
                description="标注结果数据 (JSON 字符串)",
                required=True,
            ),
        ],
    ),
    Prompt(
        name="annotation-workflow",
        description="完整的标注工作流引导 - 从 Schema 设计到结果合并",
        arguments=[
            PromptArgument(
                name="project_description",
                description="标注项目描述",
                required=True,
            ),
            PromptArgument(
                name="data_sample",
                description="示例数据 (JSON 字符串，可选)",
                required=False,
            ),
        ],
    ),
]


# ============================================================
# 同步处理函数（可独立测试）
# ============================================================


def get_prompt_messages(
    name: str, arguments: dict[str, str] | None = None
) -> list[PromptMessage]:
    """根据 prompt 名称和参数生成消息列表."""
    args = arguments or {}

    if name == "create-annotation-schema":
        return _build_create_schema_prompt(args)
    elif name == "review-annotations":
        return _build_review_prompt(args)
    elif name == "annotation-workflow":
        return _build_workflow_prompt(args)
    else:
        raise ValueError(f"未知 Prompt: {name}")


def _build_create_schema_prompt(args: dict[str, str]) -> list[PromptMessage]:
    task_desc = args.get("task_description", "")
    ann_type = args.get("annotation_type", "")

    type_hint = ""
    if ann_type:
        type_hint = f"\n指定标注类型: {ann_type}"
        if ann_type in SCHEMA_TEMPLATES:
            example = json.dumps(
                SCHEMA_TEMPLATES[ann_type]["schema"],
                indent=2,
                ensure_ascii=False,
            )
            type_hint += f"\n\n该类型的 Schema 示例:\n```json\n{example}\n```"
    else:
        example = json.dumps(
            SCHEMA_TEMPLATES["scoring"]["schema"],
            indent=2,
            ensure_ascii=False,
        )
        type_hint = (
            f"\n\n可用标注类型: scoring, single_choice, multi_choice, text, ranking"
            f"\n请根据任务描述推断合适的类型。"
            f"\n\nScoring 类型 Schema 示例:\n```json\n{example}\n```"
        )

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"请根据以下标注任务描述，生成一个 DataLabel Schema（JSON 格式）。\n\n"
                    f"任务描述: {task_desc}"
                    f"{type_hint}\n\n"
                    f"要求:\n"
                    f"1. Schema 必须包含 project_name 和 fields 字段\n"
                    f"2. 根据标注类型，包含 scoring_rubric（评分）或 annotation_config（分类/文本/排序）\n"
                    f"3. 每个 field 需要 name, display_name, type\n"
                    f"4. 如果是 single_choice/multi_choice/ranking，必须包含 options\n\n"
                    f"请直接输出 JSON Schema。"
                ),
            ),
        )
    ]


def _build_review_prompt(args: dict[str, str]) -> list[PromptMessage]:
    schema_str = args.get("schema", "{}")
    results_str = args.get("results", "[]")

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"请分析以下标注结果的质量和一致性。\n\n"
                    f"标注规范 Schema:\n```json\n{schema_str}\n```\n\n"
                    f"标注结果:\n```json\n{results_str}\n```\n\n"
                    f"请从以下维度分析:\n"
                    f"1. 标注完成度: 是否所有任务都已标注\n"
                    f"2. 标注一致性: 不同标注员之间的一致程度\n"
                    f"3. 异常检测: 是否有可疑的标注模式（如全部选同一选项）\n"
                    f"4. 质量建议: 改进标注质量的建议\n\n"
                    f"请给出详细的分析报告。"
                ),
            ),
        )
    ]


def _build_workflow_prompt(args: dict[str, str]) -> list[PromptMessage]:
    project_desc = args.get("project_description", "")
    data_sample = args.get("data_sample", "")

    sample_section = ""
    if data_sample:
        sample_section = f"\n\n示例数据:\n```json\n{data_sample}\n```"

    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"请帮我完成以下标注项目的完整工作流。\n\n"
                    f"项目描述: {project_desc}"
                    f"{sample_section}\n\n"
                    f"请按以下步骤引导我:\n\n"
                    f"**步骤 1: 设计 Schema**\n"
                    f"根据项目描述设计标注规范，然后用 `validate_schema` 工具验证。\n\n"
                    f"**步骤 2: 准备任务数据**\n"
                    f"如果数据是 CSV/JSONL 格式，用 `import_tasks` 工具转换。\n\n"
                    f"**步骤 3: 生成标注界面**\n"
                    f"用 `create_annotator` 工具生成 HTML 标注页面。\n\n"
                    f"**步骤 4: 标注**\n"
                    f"分发 HTML 文件给标注员，在浏览器中离线标注。\n\n"
                    f"**步骤 5: 合并与分析**\n"
                    f"收集结果后用 `merge_annotations` 合并，用 `calculate_iaa` 计算一致性。\n"
                    f"如需导出，用 `export_results` 转换格式。\n\n"
                    f"请从步骤 1 开始，帮我设计 Schema。"
                ),
            ),
        )
    ]


# ============================================================
# 注册到 MCP Server
# ============================================================


def register_prompts(server: Any) -> None:
    """注册所有 Prompt 到 MCP 服务器."""

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return PROMPTS

    @server.get_prompt()
    async def get_prompt(
        name: str, arguments: dict[str, str] | None = None
    ) -> Any:
        from mcp.types import GetPromptResult

        messages = get_prompt_messages(name, arguments)
        prompt_def = next((p for p in PROMPTS if p.name == name), None)
        return GetPromptResult(
            description=prompt_def.description if prompt_def else "",
            messages=messages,
        )
