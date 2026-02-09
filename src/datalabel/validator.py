"""Schema and data validation for DataLabel."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    """Result of validation."""

    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


VALID_ANNOTATION_TYPES = {"scoring", "single_choice", "multi_choice", "text", "ranking"}


class SchemaValidator:
    """Validate schema and task data."""

    def validate_schema(self, schema: Dict[str, Any]) -> ValidationResult:
        """Validate a schema definition."""
        result = ValidationResult()

        if not isinstance(schema, dict):
            result.valid = False
            result.errors.append("Schema 必须是一个字典/对象")
            return result

        # project_name
        if "project_name" not in schema:
            result.warnings.append("建议添加 project_name 字段")

        # fields
        fields = schema.get("fields", [])
        if not fields:
            result.warnings.append("Schema 没有定义 fields 字段")
        else:
            if not isinstance(fields, list):
                result.valid = False
                result.errors.append("fields 必须是列表")
            else:
                for i, f in enumerate(fields):
                    if not isinstance(f, dict):
                        result.valid = False
                        result.errors.append(f"fields[{i}] 必须是字典")
                        continue
                    if "name" not in f:
                        result.valid = False
                        result.errors.append(f"fields[{i}] 缺少 name 字段")

        # annotation_config vs scoring_rubric
        has_annotation = "annotation_config" in schema
        has_scoring = "scoring_rubric" in schema

        if not has_annotation and not has_scoring:
            result.warnings.append("建议添加 scoring_rubric 或 annotation_config")

        if has_annotation:
            self._validate_annotation_config(schema["annotation_config"], result)

        if has_scoring:
            self._validate_scoring_rubric(schema["scoring_rubric"], result)

        return result

    def validate_tasks(
        self, tasks: List[Dict[str, Any]], schema: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate task data."""
        result = ValidationResult()

        if not isinstance(tasks, list):
            result.valid = False
            result.errors.append("任务数据必须是列表")
            return result

        if not tasks:
            result.warnings.append("任务列表为空")
            return result

        seen_ids = set()
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                result.valid = False
                result.errors.append(f"tasks[{i}] 必须是字典")
                continue

            task_id = task.get("id")
            if task_id:
                if task_id in seen_ids:
                    result.valid = False
                    result.errors.append(f"重复的任务 ID: {task_id}")
                seen_ids.add(task_id)

        return result

    def _validate_annotation_config(
        self, config: Any, result: ValidationResult
    ) -> None:
        """Validate annotation_config."""
        if not isinstance(config, dict):
            result.valid = False
            result.errors.append("annotation_config 必须是字典")
            return

        ann_type = config.get("type")
        if not ann_type:
            result.valid = False
            result.errors.append("annotation_config 缺少 type 字段")
            return

        if ann_type not in VALID_ANNOTATION_TYPES:
            result.valid = False
            result.errors.append(
                f"annotation_config.type '{ann_type}' 无效，"
                f"支持的类型: {', '.join(sorted(VALID_ANNOTATION_TYPES))}"
            )
            return

        # Types that require options
        if ann_type in ("single_choice", "multi_choice", "ranking"):
            options = config.get("options")
            if not options:
                result.valid = False
                result.errors.append(
                    f"annotation_config.type='{ann_type}' 需要 options 字段"
                )
            elif not isinstance(options, list) or len(options) < 2:
                result.valid = False
                result.errors.append(
                    "annotation_config.options 至少需要 2 个选项"
                )

    def _validate_scoring_rubric(
        self, rubric: Any, result: ValidationResult
    ) -> None:
        """Validate scoring_rubric."""
        if not isinstance(rubric, list):
            result.valid = False
            result.errors.append("scoring_rubric 必须是列表")
            return

        for i, item in enumerate(rubric):
            if not isinstance(item, dict):
                result.valid = False
                result.errors.append(f"scoring_rubric[{i}] 必须是字典")
                continue
            if "score" not in item:
                result.valid = False
                result.errors.append(f"scoring_rubric[{i}] 缺少 score 字段")
