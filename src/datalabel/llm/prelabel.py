"""自动预标注 — 使用 LLM 对任务数据进行批量预标注。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from datalabel.llm.client import LLMClient, LLMUsage
from datalabel.llm.prompts import PRELABEL_SYSTEM, PRELABEL_USER_BATCH


@dataclass
class PreLabelResult:
    """预标注结果。"""

    success: bool = True
    responses: list[dict] = field(default_factory=list)
    total_tasks: int = 0
    labeled_tasks: int = 0
    total_usage: LLMUsage = field(default_factory=LLMUsage)
    output_path: str | None = None
    error: str | None = None


def _detect_annotation_type(schema: dict) -> str:
    """从 schema 推断标注类型。"""
    if "annotation_config" in schema:
        return schema["annotation_config"].get("type", "scoring")
    if "scoring_rubric" in schema:
        return "scoring"
    return "scoring"


def _build_annotation_spec(schema: dict, annotation_type: str) -> str:
    """构建标注规范描述文本。"""
    lines = []
    if annotation_type == "scoring" and "scoring_rubric" in schema:
        lines.append("评分标准:")
        for item in schema["scoring_rubric"]:
            score = item.get("score", "")
            label = item.get("label", "")
            desc = item.get("description", "")
            lines.append(f"  - {score} 分 ({label}): {desc}" if label else f"  - {score} 分: {desc}")
    elif annotation_type in ("single_choice", "multi_choice"):
        config = schema.get("annotation_config", {})
        options = config.get("options", [])
        choice_type = "单选" if annotation_type == "single_choice" else "多选"
        lines.append(f"{choice_type}选项:")
        for opt in options:
            lines.append(f"  - {opt.get('value', '')}: {opt.get('label', '')}")
    elif annotation_type == "text":
        config = schema.get("annotation_config", {})
        placeholder = config.get("placeholder", "")
        if placeholder:
            lines.append(f"文本标注说明: {placeholder}")
    elif annotation_type == "ranking":
        config = schema.get("annotation_config", {})
        options = config.get("options", [])
        lines.append("排序项:")
        for opt in options:
            lines.append(f"  - {opt.get('value', '')}: {opt.get('label', '')}")
    return "\n".join(lines) if lines else "（无额外标注规范）"


def _build_output_fields(annotation_type: str) -> str:
    """构建输出字段描述。"""
    mapping = {
        "scoring": '"score": 分数值',
        "single_choice": '"choice": 选中的 value',
        "multi_choice": '"choices": [选中的 value 列表]',
        "text": '"text": 标注文本',
        "ranking": '"ranking": [按顺序排列的 value 列表]',
    }
    return mapping.get(annotation_type, '"score": 分数值')


def _format_tasks_for_prompt(tasks: list[dict], fields: list[dict]) -> str:
    """格式化任务数据用于 prompt。"""
    items = []
    for task in tasks:
        data = task.get("data", {})
        parts = [f"ID: {task.get('id', 'unknown')}"]
        for f in fields:
            name = f["name"]
            display = f.get("display_name", name)
            parts.append(f"{display}: {data.get(name, '')}")
        items.append("\n".join(parts))
    return "\n---\n".join(items)


class PreLabeler:
    """自动预标注器。"""

    def __init__(self, client: LLMClient | None = None, **kwargs):
        if client is None:
            client = LLMClient(**kwargs)
        self.client = client

    def prelabel(
        self,
        schema: dict,
        tasks: list[dict],
        output_path: str | None = None,
        batch_size: int = 5,
    ) -> PreLabelResult:
        """对任务进行 LLM 预标注。

        Args:
            schema: 标注规范（与 generator 使用的 schema 格式一致）
            tasks: 任务列表
            output_path: 输出文件路径（可选）
            batch_size: 每批处理的任务数

        Returns:
            PreLabelResult
        """
        annotation_type = _detect_annotation_type(schema)
        project_name = schema.get("project_name", "未命名项目")
        fields = schema.get("fields", [])
        annotation_spec = _build_annotation_spec(schema, annotation_type)
        output_fields = _build_output_fields(annotation_type)

        all_responses = []
        total_usage = LLMUsage()

        # 分批处理
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            tasks_json = _format_tasks_for_prompt(batch, fields)

            user_content = PRELABEL_USER_BATCH.format(
                project_name=project_name,
                annotation_type=annotation_type,
                annotation_spec=annotation_spec,
                tasks_json=tasks_json,
                output_fields=output_fields,
            )

            messages = [
                {"role": "system", "content": PRELABEL_SYSTEM},
                {"role": "user", "content": user_content},
            ]

            parsed, resp = self.client.chat_json(messages)
            if not resp.success:
                return PreLabelResult(
                    success=False,
                    error=f"LLM 调用失败（批次 {i // batch_size + 1}）: {resp.error}",
                    responses=all_responses,
                    total_tasks=len(tasks),
                    labeled_tasks=len(all_responses),
                    total_usage=total_usage,
                )

            # 累计 token 用量
            total_usage.prompt_tokens += resp.usage.prompt_tokens
            total_usage.completion_tokens += resp.usage.completion_tokens
            total_usage.total_tokens += resp.usage.total_tokens

            # 解析批次结果
            batch_items = parsed if isinstance(parsed, list) else []
            for item in batch_items:
                if isinstance(item, dict) and "task_id" in item:
                    item["source"] = "llm_prelabel"
                    all_responses.append(item)

        result = PreLabelResult(
            success=True,
            responses=all_responses,
            total_tasks=len(tasks),
            labeled_tasks=len(all_responses),
            total_usage=total_usage,
        )

        # 写入输出文件
        if output_path:
            output_data = {"responses": all_responses}
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            result.output_path = output_path

        return result
