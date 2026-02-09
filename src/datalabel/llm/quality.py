"""标注质量分析 — 使用 LLM 检测可疑标注和分析标注分歧。"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field

from datalabel.llm.client import LLMClient, LLMUsage
from datalabel.llm.prompts import (
    DISAGREEMENT_SYSTEM,
    DISAGREEMENT_USER,
    QUALITY_SYSTEM,
    QUALITY_USER,
)


@dataclass
class QualityIssue:
    """单个质量问题。"""

    task_id: str
    issue_type: str  # suspicious | inconsistent | outlier
    severity: str  # high | medium | low
    description: str
    suggestion: str = ""


@dataclass
class QualityReport:
    """质量分析报告。"""

    success: bool = True
    issues: list[QualityIssue] = field(default_factory=list)
    disagreement_analysis: dict | None = None
    summary: str = ""
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
    """构建标注规范描述。"""
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
        for opt in config.get("options", []):
            lines.append(f"  - {opt.get('value')}: {opt.get('label')}")
    return "\n".join(lines) if lines else "（无额外规范）"


def _load_results(result_files: list[str]) -> list[dict]:
    """加载多个标注结果文件。"""
    all_results = []
    for path in result_files:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        responses = data.get("responses", [])
        # 尝试从 metadata 获取标注员 ID
        annotator = data.get("metadata", {}).get("annotator", path)
        for r in responses:
            r["_annotator"] = annotator
        all_results.append({"annotator": annotator, "responses": responses})
    return all_results


def _find_disagreements(results_list: list[dict]) -> list[dict]:
    """找出标注员之间有分歧的任务。"""
    # 按 task_id 分组
    task_annotations: dict[str, list[dict]] = {}
    for result in results_list:
        annotator = result["annotator"]
        for resp in result["responses"]:
            tid = resp.get("task_id", "")
            if tid not in task_annotations:
                task_annotations[tid] = []
            entry = {"annotator": annotator}
            for key in ("score", "choice", "choices", "text", "ranking", "comment"):
                if key in resp:
                    entry[key] = resp[key]
            task_annotations[tid].append(entry)

    disagreements = []
    for tid, ann_list in task_annotations.items():
        if len(ann_list) < 2:
            continue
        # 比较标注值
        values = set()
        for ann in ann_list:
            val = ann.get("score", ann.get("choice", ann.get("text", "")))
            if isinstance(val, list):
                val = tuple(sorted(val))
            values.add(val)
        if len(values) > 1:
            disagreements.append({"task_id": tid, "annotations": ann_list})

    return disagreements


def _sample_results(results_list: list[dict], sample_size: int) -> list[dict]:
    """对标注结果进行抽样。"""
    sampled = []
    for result in results_list:
        responses = result["responses"]
        if len(responses) > sample_size:
            responses = random.sample(responses, sample_size)
        sampled.append({"annotator": result["annotator"], "responses": responses})
    return sampled


class QualityAnalyzer:
    """标注质量分析器。"""

    def __init__(self, client: LLMClient | None = None, **kwargs):
        if client is None:
            client = LLMClient(**kwargs)
        self.client = client

    def analyze(
        self,
        schema: dict,
        result_files: list[str],
        output_path: str | None = None,
        sample_size: int = 20,
    ) -> QualityReport:
        """分析标注质量。

        Args:
            schema: 标注规范
            result_files: 标注结果文件路径列表
            output_path: 报告输出路径（可选）
            sample_size: 每个标注员抽样数量

        Returns:
            QualityReport
        """
        annotation_type = _detect_annotation_type(schema)
        project_name = schema.get("project_name", "未命名项目")
        annotation_spec = _build_annotation_spec(schema, annotation_type)

        results_list = _load_results(result_files)
        total_usage = LLMUsage()
        all_issues: list[QualityIssue] = []
        disagreement_analysis = None

        # 1) 单标注员质量检查
        sampled = _sample_results(results_list, sample_size)
        results_json = json.dumps(sampled, ensure_ascii=False, indent=2)

        user_content = QUALITY_USER.format(
            project_name=project_name,
            annotation_type=annotation_type,
            annotation_spec=annotation_spec,
            results_json=results_json,
        )
        messages = [
            {"role": "system", "content": QUALITY_SYSTEM},
            {"role": "user", "content": user_content},
        ]

        parsed, resp = self.client.chat_json(messages)
        if not resp.success:
            return QualityReport(success=False, error=f"质量分析 LLM 调用失败: {resp.error}")

        total_usage.prompt_tokens += resp.usage.prompt_tokens
        total_usage.completion_tokens += resp.usage.completion_tokens
        total_usage.total_tokens += resp.usage.total_tokens

        if isinstance(parsed, dict):
            for issue_data in parsed.get("issues", []):
                all_issues.append(QualityIssue(
                    task_id=issue_data.get("task_id", ""),
                    issue_type=issue_data.get("issue_type", "suspicious"),
                    severity=issue_data.get("severity", "medium"),
                    description=issue_data.get("description", ""),
                    suggestion=issue_data.get("suggestion", ""),
                ))
            summary = parsed.get("summary", "")
        else:
            summary = ""

        # 2) 多标注员分歧分析
        if len(results_list) >= 2:
            disagreements = _find_disagreements(results_list)
            if disagreements:
                disagreements_json = json.dumps(disagreements, ensure_ascii=False, indent=2)
                user_content_d = DISAGREEMENT_USER.format(
                    project_name=project_name,
                    annotation_type=annotation_type,
                    annotation_spec=annotation_spec,
                    disagreements_json=disagreements_json,
                )
                messages_d = [
                    {"role": "system", "content": DISAGREEMENT_SYSTEM},
                    {"role": "user", "content": user_content_d},
                ]

                parsed_d, resp_d = self.client.chat_json(messages_d)
                total_usage.prompt_tokens += resp_d.usage.prompt_tokens
                total_usage.completion_tokens += resp_d.usage.completion_tokens
                total_usage.total_tokens += resp_d.usage.total_tokens

                if resp_d.success and isinstance(parsed_d, dict):
                    disagreement_analysis = parsed_d

        report = QualityReport(
            success=True,
            issues=all_issues,
            disagreement_analysis=disagreement_analysis,
            summary=summary,
            total_usage=total_usage,
        )

        if output_path:
            report_data = {
                "summary": summary,
                "issues": [
                    {
                        "task_id": i.task_id,
                        "issue_type": i.issue_type,
                        "severity": i.severity,
                        "description": i.description,
                        "suggestion": i.suggestion,
                    }
                    for i in all_issues
                ],
                "disagreement_analysis": disagreement_analysis,
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            report.output_path = output_path

        return report
