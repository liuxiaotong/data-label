"""Tests for AnnotatorGenerator."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from datalabel import AnnotatorGenerator


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

    def test_generate_scoring_rubric_renders(self, sample_schema, sample_tasks):
        """Test that scoring rubric text appears in generated HTML."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"

            result = generator.generate(
                schema=sample_schema,
                tasks=sample_tasks,
                output_path=str(output_path),
            )

            assert result.success
            content = output_path.read_text()
            # Verify rubric descriptions render (was bug: rubric.criteria vs rubric.description)
            assert "质量差" in content
            assert "质量中等" in content
            assert "质量好" in content

    def test_generate_without_scoring_rubric(self, sample_tasks):
        """Test generation with schema missing scoring_rubric uses defaults."""
        generator = AnnotatorGenerator()
        schema = {
            "project_name": "无评分标准项目",
            "fields": [
                {"name": "instruction", "display_name": "指令", "type": "text"},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"

            result = generator.generate(
                schema=schema,
                tasks=sample_tasks,
                output_path=str(output_path),
            )

            assert result.success
            content = output_path.read_text()
            # Default buttons should render
            assert "正确" in content
            assert "部分正确" in content
            assert "错误" in content

    def test_generate_tasks_without_ids(self, sample_schema):
        """Test generation with tasks that have no IDs (auto-generated)."""
        generator = AnnotatorGenerator()
        tasks = [
            {"data": {"instruction": "问题1", "response": "回答1"}},
            {"data": {"instruction": "问题2", "response": "回答2"}},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"

            result = generator.generate(
                schema=sample_schema,
                tasks=tasks,
                output_path=str(output_path),
            )

            assert result.success
            assert result.task_count == 2

    def test_generate_single_choice(self, sample_tasks):
        """Test generation with single_choice annotation type."""
        generator = AnnotatorGenerator()
        schema = {
            "project_name": "分类项目",
            "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
            "annotation_config": {
                "type": "single_choice",
                "options": [
                    {"value": "pos", "label": "正面"},
                    {"value": "neg", "label": "负面"},
                    {"value": "neu", "label": "中性"},
                ],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "single_choice" in content
            assert "choice-btn" in content

    def test_generate_multi_choice(self, sample_tasks):
        """Test generation with multi_choice annotation type."""
        generator = AnnotatorGenerator()
        schema = {
            "project_name": "多标签项目",
            "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
            "annotation_config": {
                "type": "multi_choice",
                "options": [
                    {"value": "tag1", "label": "标签1"},
                    {"value": "tag2", "label": "标签2"},
                ],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "multi_choice" in content

    def test_generate_text_annotation(self, sample_tasks):
        """Test generation with text annotation type."""
        generator = AnnotatorGenerator()
        schema = {
            "project_name": "翻译项目",
            "fields": [{"name": "source", "display_name": "原文", "type": "text"}],
            "annotation_config": {
                "type": "text",
                "placeholder": "请输入翻译...",
                "max_length": 500,
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "text" in content
            assert "annotationText" in content

    def test_generate_ranking(self, sample_tasks):
        """Test generation with ranking annotation type."""
        generator = AnnotatorGenerator()
        schema = {
            "project_name": "排序项目",
            "fields": [{"name": "query", "display_name": "查询", "type": "text"}],
            "annotation_config": {
                "type": "ranking",
                "options": [
                    {"value": "a", "label": "结果A"},
                    {"value": "b", "label": "结果B"},
                    {"value": "c", "label": "结果C"},
                ],
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "ranking" in content
            assert "ranking-item" in content

    def test_generate_with_page_size(self, sample_schema, sample_tasks):
        """Test generation with custom page_size."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=sample_schema,
                tasks=sample_tasks,
                output_path=str(output_path),
                page_size=10,
            )

            assert result.success
            content = output_path.read_text()
            assert "pageSize = 10" in content
            assert "task-sidebar" in content
            assert "sidebarSearch" in content

    def test_generate_backward_compatible(self, sample_schema, sample_tasks):
        """Test that schemas without annotation_config still work (scoring mode)."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=sample_schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "scoring" in content
            assert "score-btn" in content

    def test_generate_has_dark_mode(self, sample_schema, sample_tasks):
        """Test that generated HTML includes dark mode support."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=sample_schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert 'data-theme="dark"' in content
            assert "themeToggle" in content
            assert "toggleTheme" in content

    def test_generate_has_stats_panel(self, sample_schema, sample_tasks):
        """Test that generated HTML includes statistics panel."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=sample_schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "statsPanel" in content
            assert "statsCompleted" in content
            assert "updateStats" in content

    def test_generate_has_undo(self, sample_schema, sample_tasks):
        """Test that generated HTML includes undo functionality."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=sample_schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "undoBtn" in content
            assert "undoAnnotation" in content
            assert "undoHistory" in content

    def test_generate_has_shortcut_modal(self, sample_schema, sample_tasks):
        """Test that generated HTML includes shortcut help modal."""
        generator = AnnotatorGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "annotator.html"
            result = generator.generate(
                schema=sample_schema, tasks=sample_tasks, output_path=str(output_path)
            )

            assert result.success
            content = output_path.read_text()
            assert "shortcutModal" in content
            assert "toggleShortcutModal" in content


class TestGenerateFromDatarecipeErrors:
    """generate_from_datarecipe 错误路径测试."""

    def test_missing_schema_file(self):
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = generator.generate_from_datarecipe(tmpdir)
            assert not result.success
            assert "not found" in result.error.lower() or "Schema" in result.error

    def test_corrupted_schema_json(self):
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "DATA_SCHEMA.json"
            schema_path.write_text("{invalid json", encoding="utf-8")
            result = generator.generate_from_datarecipe(tmpdir)
            assert not result.success
            assert "读取失败" in result.error

    def test_corrupted_samples_json(self, sample_schema):
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Valid schema
            schema_path = Path(tmpdir) / "DATA_SCHEMA.json"
            schema_path.write_text(
                json.dumps(sample_schema, ensure_ascii=False), encoding="utf-8"
            )
            # Corrupted samples
            samples_dir = Path(tmpdir) / "09_样例数据"
            samples_dir.mkdir()
            (samples_dir / "samples.json").write_text(
                "{bad json!", encoding="utf-8"
            )
            result = generator.generate_from_datarecipe(tmpdir)
            assert not result.success
            assert "读取失败" in result.error

    def test_nonexistent_directory(self):
        generator = AnnotatorGenerator()
        result = generator.generate_from_datarecipe("/nonexistent/path")
        assert not result.success

    def test_valid_schema_no_samples(self, sample_schema):
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "DATA_SCHEMA.json"
            schema_path.write_text(
                json.dumps(sample_schema, ensure_ascii=False), encoding="utf-8"
            )
            result = generator.generate_from_datarecipe(tmpdir)
            assert result.success
            assert result.task_count == 0


class TestGeneratorValidationErrors:
    """Test generator validation error paths."""

    def test_generate_invalid_schema(self):
        """Test schema validation failure → lines 72-74."""
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.html"
            result = generator.generate(
                schema={"fields": "not_a_list"},
                tasks=[],
                output_path=str(output_path),
            )
            assert not result.success
            assert "Schema 验证失败" in result.error

    def test_generate_invalid_tasks(self, sample_schema):
        """Test task validation failure → lines 78-80."""
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.html"
            result = generator.generate(
                schema=sample_schema,
                tasks=["not_a_dict"],
                output_path=str(output_path),
            )
            assert not result.success
            assert "任务数据验证失败" in result.error

    def test_generate_os_error(self, sample_schema, sample_tasks):
        """Test OS error during write → lines 103-105."""
        generator = AnnotatorGenerator()
        # /dev/null/impossible is not a valid path on any OS
        result = generator.generate(
            schema=sample_schema,
            tasks=sample_tasks,
            output_path="/dev/null/impossible/path/annotator.html",
        )
        assert not result.success
        assert result.error  # should have an error message

    def test_generate_from_datarecipe_with_guidelines(self, sample_schema, sample_tasks):
        """Test datarecipe with guidelines file → line 157."""
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            # Schema
            schema_path = Path(tmpdir) / "DATA_SCHEMA.json"
            schema_path.write_text(
                json.dumps(sample_schema, ensure_ascii=False), encoding="utf-8"
            )
            # Samples
            samples_dir = Path(tmpdir) / "09_样例数据"
            samples_dir.mkdir()
            (samples_dir / "samples.json").write_text(
                json.dumps({"samples": sample_tasks}, ensure_ascii=False), encoding="utf-8"
            )
            # Guidelines
            guidelines_dir = Path(tmpdir) / "03_标注规范"
            guidelines_dir.mkdir()
            (guidelines_dir / "ANNOTATION_SPEC.md").write_text(
                "# 标注规范\n请认真标注。", encoding="utf-8"
            )

            result = generator.generate_from_datarecipe(tmpdir)
            assert result.success
            assert result.task_count == 2

    def test_generate_no_markdown_fallback(self, sample_schema, sample_tasks):
        """Test fallback when markdown module is not available → line 194."""
        generator = AnnotatorGenerator()
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "out.html"

            with patch("datalabel.generator.HAS_MARKDOWN", False):
                result = generator.generate(
                    schema=sample_schema,
                    tasks=sample_tasks,
                    output_path=str(output_path),
                    guidelines="# 标注指南\n请仔细阅读。",
                )

            assert result.success
            content = output_path.read_text()
            assert "<pre>" in content
            assert "标注指南" in content
