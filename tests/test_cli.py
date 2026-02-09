"""Tests for CLI commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from datalabel.cli import main


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self):
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.2.1" in result.output

    def test_create_command(self, sample_schema, sample_tasks):
        """Test create command."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "annotator.html"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))

            result = runner.invoke(
                main,
                ["create", str(schema_path), str(tasks_path), "-o", str(output_path)],
            )

            assert result.exit_code == 0
            assert "创建成功" in result.output
            assert output_path.exists()

    def test_create_with_title(self, sample_schema, sample_tasks):
        """Test create command with custom title."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "annotator.html"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))

            result = runner.invoke(
                main,
                [
                    "create",
                    str(schema_path),
                    str(tasks_path),
                    "-o",
                    str(output_path),
                    "-t",
                    "自定义标题",
                ],
            )

            assert result.exit_code == 0
            content = output_path.read_text()
            assert "自定义标题" in content

    def test_merge_command(
        self, annotator1_results, annotator2_results, annotator_results_factory
    ):
        """Test merge command."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [annotator1_results, annotator2_results])
            output_path = Path(tmpdir) / "merged.json"

            result = runner.invoke(
                main,
                ["merge", *files, "-o", str(output_path)],
            )

            assert result.exit_code == 0
            assert "合并成功" in result.output
            assert output_path.exists()

    def test_merge_requires_two_files(self, annotator1_results, annotator_results_factory):
        """Test merge command fails with less than 2 files."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [annotator1_results])
            output_path = Path(tmpdir) / "merged.json"

            result = runner.invoke(
                main,
                ["merge", *files, "-o", str(output_path)],
            )

            assert result.exit_code != 0

    def test_iaa_command(
        self, annotator1_results, annotator2_results, annotator_results_factory
    ):
        """Test iaa command."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [annotator1_results, annotator2_results])

            result = runner.invoke(main, ["iaa", *files])

            assert result.exit_code == 0
            assert "一致性" in result.output
            assert "一致率" in result.output

    def test_iaa_requires_two_files(self, annotator1_results, annotator_results_factory):
        """Test iaa command fails with less than 2 files."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [annotator1_results])

            result = runner.invoke(main, ["iaa", *files])

            assert result.exit_code != 0

    def test_export_json(self, annotator1_results):
        """Test export command with JSON format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "results.json"
            input_path.write_text(json.dumps(annotator1_results, ensure_ascii=False))
            output_path = Path(tmpdir) / "exported.json"

            result = runner.invoke(
                main, ["export", str(input_path), "-o", str(output_path), "-f", "json"]
            )

            assert result.exit_code == 0
            assert "导出成功" in result.output
            data = json.loads(output_path.read_text())
            assert isinstance(data, list)

    def test_export_jsonl(self, annotator1_results):
        """Test export command with JSONL format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "results.json"
            input_path.write_text(json.dumps(annotator1_results, ensure_ascii=False))
            output_path = Path(tmpdir) / "exported.jsonl"

            result = runner.invoke(
                main, ["export", str(input_path), "-o", str(output_path), "-f", "jsonl"]
            )

            assert result.exit_code == 0
            lines = output_path.read_text().strip().split("\n")
            assert len(lines) == len(annotator1_results["responses"])
            for line in lines:
                json.loads(line)  # Should not raise

    def test_export_csv(self, annotator1_results):
        """Test export command with CSV format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "results.json"
            input_path.write_text(json.dumps(annotator1_results, ensure_ascii=False))
            output_path = Path(tmpdir) / "exported.csv"

            result = runner.invoke(
                main, ["export", str(input_path), "-o", str(output_path), "-f", "csv"]
            )

            assert result.exit_code == 0
            content = output_path.read_text()
            assert "task_id" in content
            lines = content.strip().split("\n")
            assert len(lines) == len(annotator1_results["responses"]) + 1  # header + rows

    def test_import_tasks_json(self, sample_tasks):
        """Test import-tasks from JSON."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "tasks.json"
            input_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))
            output_path = Path(tmpdir) / "imported.json"

            result = runner.invoke(
                main, ["import-tasks", str(input_path), "-o", str(output_path)]
            )

            assert result.exit_code == 0
            assert "导入成功" in result.output
            data = json.loads(output_path.read_text())
            assert len(data) == len(sample_tasks)

    def test_import_tasks_jsonl(self, sample_tasks):
        """Test import-tasks from JSONL."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "tasks.jsonl"
            lines = [json.dumps(t, ensure_ascii=False) for t in sample_tasks]
            input_path.write_text("\n".join(lines))
            output_path = Path(tmpdir) / "imported.json"

            result = runner.invoke(
                main, ["import-tasks", str(input_path), "-o", str(output_path)]
            )

            assert result.exit_code == 0
            data = json.loads(output_path.read_text())
            assert len(data) == len(sample_tasks)

    def test_import_tasks_csv(self):
        """Test import-tasks from CSV."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "tasks.csv"
            input_path.write_text("id,text,label\nT1,hello,pos\nT2,world,neg\n")
            output_path = Path(tmpdir) / "imported.json"

            result = runner.invoke(
                main, ["import-tasks", str(input_path), "-o", str(output_path)]
            )

            assert result.exit_code == 0
            data = json.loads(output_path.read_text())
            assert len(data) == 2
            assert data[0]["id"] == "T1"
            assert data[0]["text"] == "hello"


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_schema_success(self, sample_schema):
        """Test validate with a valid schema."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))

            result = runner.invoke(main, ["validate", str(schema_path)])

            assert result.exit_code == 0
            assert "验证通过" in result.output

    def test_validate_schema_errors(self):
        """Test validate with invalid schema (missing fields)."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            schema_path.write_text(json.dumps({"fields": "not_a_list"}, ensure_ascii=False))

            result = runner.invoke(main, ["validate", str(schema_path)])

            assert result.exit_code != 0
            assert "验证失败" in result.output

    def test_validate_schema_warnings(self):
        """Test validate with schema that produces warnings."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Schema with fields but missing project_name -> warning
            schema = {"fields": [{"name": "text", "type": "text"}]}
            schema_path = Path(tmpdir) / "schema.json"
            schema_path.write_text(json.dumps(schema, ensure_ascii=False))

            result = runner.invoke(main, ["validate", str(schema_path)])

            assert result.exit_code == 0
            assert "警告" in result.output

    def test_validate_with_tasks_success(self, sample_schema, sample_tasks):
        """Test validate with valid schema and tasks."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))

            result = runner.invoke(
                main, ["validate", str(schema_path), "-t", str(tasks_path)]
            )

            assert result.exit_code == 0
            assert "任务数据验证通过" in result.output

    def test_validate_with_tasks_errors(self, sample_schema):
        """Test validate with invalid tasks (non-dict item)."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(["not_a_dict"], ensure_ascii=False))

            result = runner.invoke(
                main, ["validate", str(schema_path), "-t", str(tasks_path)]
            )

            assert result.exit_code != 0

    def test_validate_with_tasks_wrapped(self, sample_schema, sample_tasks):
        """Test validate with tasks wrapped in {"samples": [...]}."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(
                json.dumps({"samples": sample_tasks}, ensure_ascii=False)
            )

            result = runner.invoke(
                main, ["validate", str(schema_path), "-t", str(tasks_path)]
            )

            assert result.exit_code == 0
            assert "任务数据验证通过" in result.output


class TestGenerateCommand:
    """Tests for generate (DataRecipe) command."""

    def test_generate_success(self, sample_schema, sample_tasks):
        """Test generate from DataRecipe directory."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Build DataRecipe directory structure
            schema_path = Path(tmpdir) / "DATA_SCHEMA.json"
            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))

            samples_dir = Path(tmpdir) / "09_样例数据"
            samples_dir.mkdir()
            (samples_dir / "samples.json").write_text(
                json.dumps({"samples": sample_tasks}, ensure_ascii=False)
            )

            output_path = Path(tmpdir) / "out.html"
            result = runner.invoke(
                main, ["generate", tmpdir, "-o", str(output_path)]
            )

            assert result.exit_code == 0
            assert "生成成功" in result.output
            assert output_path.exists()

    def test_generate_failure(self):
        """Test generate with missing schema."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(main, ["generate", tmpdir])

            assert result.exit_code == 1
            assert "生成失败" in result.output


class TestCreateEdgeCases:
    """Tests for create command edge cases."""

    def test_create_with_wrapped_tasks(self, sample_schema, sample_tasks):
        """Test create with tasks wrapped in {"tasks": [...]}."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "annotator.html"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(
                json.dumps({"tasks": sample_tasks}, ensure_ascii=False)
            )

            result = runner.invoke(
                main,
                ["create", str(schema_path), str(tasks_path), "-o", str(output_path)],
            )

            assert result.exit_code == 0
            assert "创建成功" in result.output

    def test_create_with_guidelines(self, sample_schema, sample_tasks):
        """Test create with guidelines file."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "annotator.html"
            guidelines_path = Path(tmpdir) / "guidelines.md"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))
            guidelines_path.write_text("# 标注指南\n\n请仔细标注。")

            result = runner.invoke(
                main,
                [
                    "create",
                    str(schema_path),
                    str(tasks_path),
                    "-o",
                    str(output_path),
                    "-g",
                    str(guidelines_path),
                ],
            )

            assert result.exit_code == 0
            assert "创建成功" in result.output

    def test_create_invalid_schema(self, sample_tasks):
        """Test create with invalid schema → failure."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "annotator.html"

            schema_path.write_text(json.dumps({"fields": "not_a_list"}, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))

            result = runner.invoke(
                main,
                ["create", str(schema_path), str(tasks_path), "-o", str(output_path)],
            )

            assert result.exit_code == 1
            assert "创建失败" in result.output


class TestDashboardCommand:
    """Tests for dashboard command."""

    def test_dashboard_success(
        self, annotator1_results, annotator2_results, annotator_results_factory
    ):
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(
                tmpdir, [annotator1_results, annotator2_results]
            )
            output_path = Path(tmpdir) / "dashboard.html"

            result = runner.invoke(
                main, ["dashboard", *files, "-o", str(output_path)]
            )

            assert result.exit_code == 0
            assert "仪表盘已生成" in result.output
            assert "标注员数: 2" in result.output
            assert output_path.exists()

    def test_dashboard_with_title(
        self, annotator1_results, annotator2_results, annotator_results_factory
    ):
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(
                tmpdir, [annotator1_results, annotator2_results]
            )
            output_path = Path(tmpdir) / "dashboard.html"

            result = runner.invoke(
                main,
                ["dashboard", *files, "-o", str(output_path), "-t", "测试仪表盘"],
            )

            assert result.exit_code == 0
            content = output_path.read_text(encoding="utf-8")
            assert "测试仪表盘" in content

    def test_dashboard_corrupted_file(self):
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "bad.json"
            f1.write_text("{invalid")
            output_path = Path(tmpdir) / "dashboard.html"

            result = runner.invoke(
                main, ["dashboard", str(f1), "-o", str(output_path)]
            )

            assert result.exit_code == 1
            assert "生成失败" in result.output


class TestMergeIAAErrors:
    """Tests for merge/iaa error paths."""

    def test_merge_failure(self):
        """Test merge with corrupted result files."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a1.json"
            f2 = Path(tmpdir) / "a2.json"
            f1.write_text("{invalid json")
            f2.write_text("{invalid json")
            output_path = Path(tmpdir) / "merged.json"

            result = runner.invoke(
                main, ["merge", str(f1), str(f2), "-o", str(output_path)]
            )

            assert result.exit_code == 1
            assert "合并失败" in result.output

    def test_iaa_error(self):
        """Test iaa with corrupted result files."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a1.json"
            f2 = Path(tmpdir) / "a2.json"
            # Files without responses key → calculate_iaa returns error
            f1.write_text(json.dumps({"responses": []}, ensure_ascii=False))
            f2.write_text(json.dumps({"responses": []}, ensure_ascii=False))

            result = runner.invoke(main, ["iaa", str(f1), str(f2)])

            assert result.exit_code == 1
            assert "计算失败" in result.output


class TestExportErrors:
    """Tests for export error paths."""

    def test_export_unrecognized_format(self):
        """Test export with unrecognized result file format."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "results.json"
            input_path.write_text(json.dumps({"some_key": "value"}, ensure_ascii=False))
            output_path = Path(tmpdir) / "exported.json"

            result = runner.invoke(
                main, ["export", str(input_path), "-o", str(output_path), "-f", "json"]
            )

            assert result.exit_code == 1
            assert "无法识别" in result.output


class TestValidateTaskWarnings:
    """Tests for validate task warnings path."""

    def test_validate_with_empty_tasks(self, sample_schema):
        """Test validate with empty tasks list → task warnings."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps([], ensure_ascii=False))

            result = runner.invoke(
                main, ["validate", str(schema_path), "-t", str(tasks_path)]
            )

            assert result.exit_code == 0
            assert "警告" in result.output


class TestLLMCommands:
    """Tests for LLM CLI commands with mocking."""

    def test_prelabel_success(self, sample_schema, sample_tasks):
        """Test prelabel command success."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "prelabeled.json"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))

            from datalabel.llm import LLMUsage, PreLabelResult

            mock_result = PreLabelResult(
                success=True,
                total_tasks=2,
                labeled_tasks=2,
                total_usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
                output_path=str(output_path),
            )

            with patch("datalabel.llm.PreLabeler") as MockLabeler, \
                 patch("datalabel.llm.LLMClient"), \
                 patch("datalabel.llm.LLMConfig"):
                MockLabeler.return_value.prelabel.return_value = mock_result

                result = runner.invoke(
                    main,
                    ["prelabel", str(schema_path), str(tasks_path), "-o", str(output_path)],
                )

            assert result.exit_code == 0
            assert "预标注完成" in result.output
            assert "2/2" in result.output

    def test_prelabel_failure(self, sample_schema, sample_tasks):
        """Test prelabel command failure."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "prelabeled.json"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))

            from datalabel.llm import PreLabelResult

            mock_result = PreLabelResult(success=False, error="API 调用失败")

            with patch("datalabel.llm.PreLabeler") as MockLabeler, \
                 patch("datalabel.llm.LLMClient"), \
                 patch("datalabel.llm.LLMConfig"):
                MockLabeler.return_value.prelabel.return_value = mock_result

                result = runner.invoke(
                    main,
                    ["prelabel", str(schema_path), str(tasks_path), "-o", str(output_path)],
                )

            assert result.exit_code == 1
            assert "预标注失败" in result.output

    def test_quality_success(self, sample_schema, annotator1_results, annotator2_results):
        """Test quality command success."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            f1 = Path(tmpdir) / "a1.json"
            f2 = Path(tmpdir) / "a2.json"
            output_path = Path(tmpdir) / "report.json"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            f1.write_text(json.dumps(annotator1_results, ensure_ascii=False))
            f2.write_text(json.dumps(annotator2_results, ensure_ascii=False))

            from datalabel.llm import LLMUsage
            from datalabel.llm.quality import QualityIssue, QualityReport

            mock_report = QualityReport(
                success=True,
                summary="总体质量良好",
                issues=[
                    QualityIssue(
                        task_id="TASK_002",
                        issue_type="suspicious",
                        severity="medium",
                        description="标注分歧较大",
                    )
                ],
                disagreement_analysis={"common_patterns": "分数偏差较大"},
                total_usage=LLMUsage(total_tokens=200),
                output_path=str(output_path),
            )

            with patch("datalabel.llm.QualityAnalyzer") as MockAnalyzer, \
                 patch("datalabel.llm.LLMClient"), \
                 patch("datalabel.llm.LLMConfig"):
                MockAnalyzer.return_value.analyze.return_value = mock_report

                result = runner.invoke(
                    main,
                    [
                        "quality",
                        str(schema_path),
                        str(f1),
                        str(f2),
                        "-o",
                        str(output_path),
                    ],
                )

            assert result.exit_code == 0
            assert "质量分析报告" in result.output
            assert "1 个问题" in result.output
            assert "分歧分析" in result.output

    def test_quality_failure(self, sample_schema, annotator1_results, annotator2_results):
        """Test quality command failure."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            f1 = Path(tmpdir) / "a1.json"
            f2 = Path(tmpdir) / "a2.json"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            f1.write_text(json.dumps(annotator1_results, ensure_ascii=False))
            f2.write_text(json.dumps(annotator2_results, ensure_ascii=False))

            from datalabel.llm.quality import QualityReport

            mock_report = QualityReport(success=False, error="API 错误")

            with patch("datalabel.llm.QualityAnalyzer") as MockAnalyzer, \
                 patch("datalabel.llm.LLMClient"), \
                 patch("datalabel.llm.LLMConfig"):
                MockAnalyzer.return_value.analyze.return_value = mock_report

                result = runner.invoke(
                    main,
                    ["quality", str(schema_path), str(f1), str(f2)],
                )

            assert result.exit_code == 1
            assert "分析失败" in result.output

    def test_gen_guidelines_success(self, sample_schema, sample_tasks):
        """Test gen-guidelines command success."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            tasks_path = Path(tmpdir) / "tasks.json"
            output_path = Path(tmpdir) / "guidelines.md"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))
            tasks_path.write_text(json.dumps(sample_tasks, ensure_ascii=False))

            from datalabel.llm import LLMUsage
            from datalabel.llm.guidelines import GuidelinesResult

            mock_result = GuidelinesResult(
                success=True,
                content="# 标注指南",
                total_usage=LLMUsage(total_tokens=300),
                output_path=str(output_path),
            )

            with patch("datalabel.llm.GuidelinesGenerator") as MockGen, \
                 patch("datalabel.llm.LLMClient"), \
                 patch("datalabel.llm.LLMConfig"):
                MockGen.return_value.generate.return_value = mock_result

                result = runner.invoke(
                    main,
                    [
                        "gen-guidelines",
                        str(schema_path),
                        "-t",
                        str(tasks_path),
                        "-o",
                        str(output_path),
                    ],
                )

            assert result.exit_code == 0
            assert "指南生成成功" in result.output

    def test_gen_guidelines_failure(self, sample_schema):
        """Test gen-guidelines command failure."""
        runner = CliRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            schema_path = Path(tmpdir) / "schema.json"
            output_path = Path(tmpdir) / "guidelines.md"

            schema_path.write_text(json.dumps(sample_schema, ensure_ascii=False))

            from datalabel.llm.guidelines import GuidelinesResult

            mock_result = GuidelinesResult(success=False, error="API 错误")

            with patch("datalabel.llm.GuidelinesGenerator") as MockGen, \
                 patch("datalabel.llm.LLMClient"), \
                 patch("datalabel.llm.LLMConfig"):
                MockGen.return_value.generate.return_value = mock_result

                result = runner.invoke(
                    main,
                    ["gen-guidelines", str(schema_path), "-o", str(output_path)],
                )

            assert result.exit_code == 1
            assert "生成失败" in result.output
