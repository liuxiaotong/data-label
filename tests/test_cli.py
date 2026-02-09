"""Tests for CLI commands."""

import json
import tempfile
from pathlib import Path

from click.testing import CliRunner

from datalabel.cli import main


class TestCLI:
    """Tests for CLI commands."""

    def test_version(self):
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.2.0" in result.output

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
