"""MCP 资源定义."""

import json
from typing import Any

from mcp.types import Resource, TextResourceContents

# ============================================================
# Schema 模板数据
# ============================================================

SCHEMA_TEMPLATES: dict[str, dict[str, Any]] = {
    "scoring": {
        "description": "评分标注模板 - 使用 scoring_rubric 定义评分等级",
        "schema": {
            "project_name": "评分标注项目",
            "fields": [
                {"name": "instruction", "display_name": "用户指令", "type": "text"},
                {"name": "response", "display_name": "模型回答", "type": "text"},
            ],
            "scoring_rubric": [
                {"score": 1, "label": "优秀", "description": "回答完整准确，逻辑清晰"},
                {"score": 0.5, "label": "一般", "description": "回答基本正确但有遗漏"},
                {"score": 0, "label": "差", "description": "回答错误或离题"},
            ],
        },
    },
    "single_choice": {
        "description": "单选标注模板 - 从预定义选项中选择一个",
        "schema": {
            "project_name": "分类标注项目",
            "fields": [
                {"name": "text", "display_name": "文本内容", "type": "text"},
            ],
            "annotation_config": {
                "type": "single_choice",
                "options": [
                    {"value": "positive", "label": "正面"},
                    {"value": "negative", "label": "负面"},
                    {"value": "neutral", "label": "中性"},
                ],
            },
        },
    },
    "multi_choice": {
        "description": "多选标注模板 - 从预定义选项中选择多个",
        "schema": {
            "project_name": "多维度标注项目",
            "fields": [
                {"name": "text", "display_name": "文本内容", "type": "text"},
            ],
            "annotation_config": {
                "type": "multi_choice",
                "options": [
                    {"value": "informative", "label": "信息丰富"},
                    {"value": "accurate", "label": "准确"},
                    {"value": "fluent", "label": "流畅"},
                    {"value": "relevant", "label": "相关"},
                ],
            },
        },
    },
    "text": {
        "description": "文本标注模板 - 自由文本输入（翻译、改写等）",
        "schema": {
            "project_name": "文本标注项目",
            "fields": [
                {"name": "text", "display_name": "原文", "type": "text"},
            ],
            "annotation_config": {
                "type": "text",
                "placeholder": "请输入标注文本...",
                "max_length": 500,
            },
        },
    },
    "ranking": {
        "description": "排序标注模板 - 拖拽排列选项顺序",
        "schema": {
            "project_name": "排序标注项目",
            "fields": [
                {"name": "text", "display_name": "查询", "type": "text"},
            ],
            "annotation_config": {
                "type": "ranking",
                "options": [
                    {"value": "result_a", "label": "结果 A"},
                    {"value": "result_b", "label": "结果 B"},
                    {"value": "result_c", "label": "结果 C"},
                ],
            },
        },
    },
}

ANNOTATION_TYPES_REFERENCE = {
    "annotation_types": [
        {
            "type": "scoring",
            "description": "数值评分，使用 scoring_rubric 定义评分等级",
            "response_keys": ["score", "comment"],
            "use_cases": ["质量评估", "模型输出评分", "满意度打分"],
        },
        {
            "type": "single_choice",
            "description": "单选分类，从预定义选项中选择一个",
            "response_keys": ["choice", "comment"],
            "use_cases": ["情感分析", "意图分类", "主题分类"],
        },
        {
            "type": "multi_choice",
            "description": "多选分类，从预定义选项中选择多个",
            "response_keys": ["choices", "comment"],
            "use_cases": ["多标签分类", "属性标注", "多维度评估"],
        },
        {
            "type": "text",
            "description": "自由文本输入，支持 placeholder 和 max_length",
            "response_keys": ["text", "comment"],
            "use_cases": ["翻译", "文本改写", "摘要生成", "纠错"],
        },
        {
            "type": "ranking",
            "description": "拖拽排序，将选项按优劣排列",
            "response_keys": ["ranking", "comment"],
            "use_cases": ["搜索结果排序", "偏好排序", "方案比较"],
        },
    ]
}


# ============================================================
# 同步处理函数（可独立测试）
# ============================================================


def read_resource_content(uri: str) -> str:
    """根据 URI 读取资源内容，返回 JSON 字符串."""
    uri_str = str(uri)

    if uri_str.startswith("datalabel://schemas/"):
        ann_type = uri_str.split("datalabel://schemas/")[1]
        if ann_type in SCHEMA_TEMPLATES:
            return json.dumps(
                SCHEMA_TEMPLATES[ann_type]["schema"],
                indent=2,
                ensure_ascii=False,
            )
        raise ValueError(f"未知的 Schema 类型: {ann_type}")

    if uri_str == "datalabel://reference/annotation-types":
        return json.dumps(
            ANNOTATION_TYPES_REFERENCE, indent=2, ensure_ascii=False
        )

    raise ValueError(f"未知资源: {uri}")


# ============================================================
# 注册到 MCP Server
# ============================================================


def register_resources(server: Any) -> None:
    """注册所有资源到 MCP 服务器."""

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        resources = []
        for ann_type, template in SCHEMA_TEMPLATES.items():
            resources.append(
                Resource(
                    uri=f"datalabel://schemas/{ann_type}",
                    name=f"Schema 模板: {ann_type}",
                    description=template["description"],
                    mimeType="application/json",
                )
            )
        resources.append(
            Resource(
                uri="datalabel://reference/annotation-types",
                name="标注类型参考",
                description="所有支持的标注类型及其用途说明",
                mimeType="application/json",
            )
        )
        return resources

    @server.read_resource()
    async def read_resource(uri: Any) -> list[TextResourceContents]:
        content = read_resource_content(str(uri))
        return [
            TextResourceContents(
                uri=str(uri),
                mimeType="application/json",
                text=content,
            )
        ]
