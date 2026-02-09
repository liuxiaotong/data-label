#!/usr/bin/env python3
"""Pipeline: DataRecipe analysis output -> DataLabel annotation interface.

Usage:
    python examples/pipeline_datarecipe_to_label.py

This example simulates a DataRecipe analysis output directory structure
and generates a DataLabel annotation interface from it.

Expected DataRecipe directory structure:
    analysis_output/
    ├── 03_标注规范/
    │   └── ANNOTATION_SPEC.md
    ├── 04_复刻指南/
    │   └── DATA_SCHEMA.json
    └── 09_样例数据/
        └── samples.json
"""

import json
import tempfile
from pathlib import Path

from datalabel import AnnotatorGenerator


def create_mock_datarecipe_output(base_dir: Path) -> Path:
    """Create a mock DataRecipe analysis output directory."""
    analysis_dir = base_dir / "analysis_output"

    # Schema
    schema_dir = analysis_dir / "04_复刻指南"
    schema_dir.mkdir(parents=True)
    schema = {
        "project_name": "DataRecipe 数据集标注",
        "fields": [
            {"name": "instruction", "display_name": "指令", "type": "text"},
            {"name": "response", "display_name": "回答", "type": "text"},
        ],
        "scoring_rubric": [
            {"score": 1, "description": "高质量"},
            {"score": 0.5, "description": "中等质量"},
            {"score": 0, "description": "低质量"},
        ],
    }
    (schema_dir / "DATA_SCHEMA.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2)
    )

    # Samples
    samples_dir = analysis_dir / "09_样例数据"
    samples_dir.mkdir(parents=True)
    samples = {
        "samples": [
            {
                "id": "S001",
                "data": {
                    "instruction": "请解释量子计算的基本原理",
                    "response": "量子计算利用量子力学原理进行信息处理...",
                },
            },
            {
                "id": "S002",
                "data": {
                    "instruction": "什么是区块链技术？",
                    "response": "区块链是一种去中心化的分布式账本技术...",
                },
            },
        ]
    }
    (samples_dir / "samples.json").write_text(
        json.dumps(samples, ensure_ascii=False, indent=2)
    )

    # Guidelines
    guidelines_dir = analysis_dir / "03_标注规范"
    guidelines_dir.mkdir(parents=True)
    (guidelines_dir / "ANNOTATION_SPEC.md").write_text(
        "# 标注规范\n\n## 评分标准\n\n- **1 分**: 回答准确、完整\n- **0.5 分**: 部分正确\n- **0 分**: 错误\n"
    )

    return analysis_dir


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create mock DataRecipe output
        analysis_dir = create_mock_datarecipe_output(tmpdir)
        print(f"Mock DataRecipe output: {analysis_dir}")

        # Generate annotation interface
        generator = AnnotatorGenerator()
        result = generator.generate_from_datarecipe(str(analysis_dir))

        if result.success:
            print(f"Generated: {result.output_path}")
            print(f"Tasks: {result.task_count}")
            print("\nOpen the HTML file in a browser to start annotating!")
        else:
            print(f"Error: {result.error}")


if __name__ == "__main__":
    main()
