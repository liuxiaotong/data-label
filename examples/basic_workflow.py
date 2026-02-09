#!/usr/bin/env python3
"""Basic DataLabel workflow: define schema, generate HTML, merge results.

Usage:
    python examples/basic_workflow.py

This script demonstrates the core DataLabel workflow:
1. Define a schema with scoring rubric
2. Prepare task data
3. Generate a standalone HTML annotation interface
4. Merge results from multiple annotators
5. Calculate inter-annotator agreement
"""

import json
import tempfile
from pathlib import Path

from datalabel import AnnotatorGenerator, ResultMerger


def main():
    # 1. Define schema
    schema = {
        "project_name": "LLM 回答质量评估",
        "fields": [
            {"name": "instruction", "display_name": "用户指令", "type": "text"},
            {"name": "response", "display_name": "模型回答", "type": "text"},
        ],
        "scoring_rubric": [
            {"score": 1, "label": "优秀", "description": "回答完整准确"},
            {"score": 0.5, "label": "一般", "description": "回答基本正确但有遗漏"},
            {"score": 0, "label": "差", "description": "回答错误或离题"},
        ],
    }

    # 2. Prepare tasks
    tasks = [
        {
            "id": "TASK_001",
            "data": {
                "instruction": "什么是机器学习？",
                "response": "机器学习是AI的一个分支，使计算机从数据中学习。",
            },
        },
        {
            "id": "TASK_002",
            "data": {
                "instruction": "解释深度学习",
                "response": "深度学习使用多层神经网络学习层次化表示。",
            },
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 3. Generate annotation interface
        generator = AnnotatorGenerator()
        result = generator.generate(
            schema=schema,
            tasks=tasks,
            output_path=str(tmpdir / "annotator.html"),
        )
        print(f"Generated: {result.output_path} ({result.task_count} tasks)")

        # 4. Simulate annotation results
        results_1 = {
            "responses": [
                {"task_id": "TASK_001", "score": 1, "comment": "准确"},
                {"task_id": "TASK_002", "score": 0.5, "comment": ""},
            ]
        }
        results_2 = {
            "responses": [
                {"task_id": "TASK_001", "score": 1, "comment": ""},
                {"task_id": "TASK_002", "score": 1, "comment": "不错"},
            ]
        }

        f1 = tmpdir / "results_1.json"
        f2 = tmpdir / "results_2.json"
        f1.write_text(json.dumps(results_1, ensure_ascii=False))
        f2.write_text(json.dumps(results_2, ensure_ascii=False))

        # 5. Merge results
        merger = ResultMerger()
        merge_result = merger.merge(
            result_files=[str(f1), str(f2)],
            output_path=str(tmpdir / "merged.json"),
            strategy="majority",
        )
        print(f"Merged: {merge_result.total_tasks} tasks, agreement: {merge_result.agreement_rate:.0%}")

        # 6. Calculate IAA
        iaa = merger.calculate_iaa([str(f1), str(f2)])
        print(f"IAA: exact agreement = {iaa['exact_agreement_rate']:.0%}")
        if "cohens_kappa" in iaa:
            print(f"     Cohen's Kappa = {iaa['cohens_kappa'][0][1]:.3f}")

    print("\nDone! In a real workflow, open the HTML file in a browser to annotate.")


if __name__ == "__main__":
    main()
