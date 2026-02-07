"""Tests for AnnotatorGenerator."""

import tempfile
from pathlib import Path

import pytest

from datalabel import AnnotatorGenerator


@pytest.fixture
def sample_schema():
    """Sample schema for testing."""
    return {
        "project_name": "测试项目",
        "fields": [
            {"name": "instruction", "display_name": "指令", "type": "text"},
            {"name": "response", "display_name": "回复", "type": "text"},
        ],
        "scoring_rubric": [
            {"score": 1, "label": "差", "description": "质量差"},
            {"score": 2, "label": "中", "description": "质量中等"},
            {"score": 3, "label": "好", "description": "质量好"},
        ],
    }


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            "id": "TASK_001",
            "data": {
                "instruction": "什么是机器学习？",
                "response": "机器学习是人工智能的一个分支...",
            },
        },
        {
            "id": "TASK_002",
            "data": {
                "instruction": "解释深度学习",
                "response": "深度学习是机器学习的一种方法...",
            },
        },
    ]


class TestAnnotatorGenerator:
    """Tests for AnnotatorGenerator class."""

    def test_generate_basic(self, sample_schema, sample_tasks):
        """Test basic generation."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"

            result = generator.generate(
                schema=sample_schema,
                tasks=sample_tasks,
                output_path=str(output_path),
            )

            assert result.success
            assert result.task_count == 2
            assert output_path.exists()

            # Check HTML content
            content = output_path.read_text()
            assert "测试项目" in content
            assert "TASK_001" in content
            assert "什么是机器学习" in content

    def test_generate_with_title(self, sample_schema, sample_tasks):
        """Test generation with custom title."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"

            result = generator.generate(
                schema=sample_schema,
                tasks=sample_tasks,
                output_path=str(output_path),
                title="自定义标题",
            )

            assert result.success
            content = output_path.read_text()
            assert "自定义标题" in content

    def test_generate_with_guidelines(self, sample_schema, sample_tasks):
        """Test generation with guidelines."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"

            result = generator.generate(
                schema=sample_schema,
                tasks=sample_tasks,
                output_path=str(output_path),
                guidelines="# 标注指南\n\n请仔细阅读每个任务。",
            )

            assert result.success
            content = output_path.read_text()
            assert "标注指南" in content

    def test_generate_empty_tasks(self, sample_schema):
        """Test generation with empty tasks."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"

            result = generator.generate(
                schema=sample_schema,
                tasks=[],
                output_path=str(output_path),
            )

            assert result.success
            assert result.task_count == 0

    def test_generate_creates_parent_dirs(self, sample_schema, sample_tasks):
        """Test that generation creates parent directories."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "deep" / "annotator.html"

            result = generator.generate(
                schema=sample_schema,
                tasks=sample_tasks,
                output_path=str(output_path),
            )

            assert result.success
            assert output_path.exists()
