#!/usr/bin/env python3
"""Demonstrate all annotation types supported by DataLabel.

Usage:
    python examples/multi_type_annotation.py

Generates HTML interfaces for each annotation type:
- scoring: Numeric score with rubric
- single_choice: Select one option
- multi_choice: Select multiple options
- text: Free-form text input
- ranking: Drag-and-drop ordering
"""

import tempfile
from pathlib import Path

from datalabel import AnnotatorGenerator

TASKS = [
    {"id": "T1", "data": {"text": "这是一个示例文本，用于演示不同标注类型。"}},
    {"id": "T2", "data": {"text": "另一个示例，展示多种标注方式的灵活性。"}},
]

SCHEMAS = {
    "scoring": {
        "project_name": "评分标注示例",
        "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
        "scoring_rubric": [
            {"score": 1, "description": "优秀"},
            {"score": 0.5, "description": "一般"},
            {"score": 0, "description": "差"},
        ],
    },
    "single_choice": {
        "project_name": "单选标注示例",
        "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
        "annotation_config": {
            "type": "single_choice",
            "options": [
                {"value": "pos", "label": "正面"},
                {"value": "neg", "label": "负面"},
                {"value": "neu", "label": "中性"},
            ],
        },
    },
    "multi_choice": {
        "project_name": "多选标注示例",
        "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
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
    "text": {
        "project_name": "文本标注示例",
        "fields": [{"name": "text", "display_name": "原文", "type": "text"}],
        "annotation_config": {
            "type": "text",
            "placeholder": "请输入改写后的文本...",
            "max_length": 500,
        },
    },
    "ranking": {
        "project_name": "排序标注示例",
        "fields": [{"name": "text", "display_name": "查询", "type": "text"}],
        "annotation_config": {
            "type": "ranking",
            "options": [
                {"value": "result_a", "label": "结果 A"},
                {"value": "result_b", "label": "结果 B"},
                {"value": "result_c", "label": "结果 C"},
            ],
        },
    },
}


def main():
    generator = AnnotatorGenerator()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        for name, schema in SCHEMAS.items():
            output = tmpdir / f"{name}_annotator.html"
            result = generator.generate(
                schema=schema,
                tasks=TASKS,
                output_path=str(output),
            )

            if result.success:
                print(f"[{name:>13}] Generated: {output.name}")
            else:
                print(f"[{name:>13}] Failed: {result.error}")

    print(f"\nGenerated {len(SCHEMAS)} annotation interfaces.")
    print("In a real workflow, these HTML files can be opened directly in any browser.")


if __name__ == "__main__":
    main()
