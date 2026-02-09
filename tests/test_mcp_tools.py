"""MCP 工具 handler 单元测试."""

import json
from pathlib import Path

from datalabel.mcp_server._tools import (
    TOOL_HANDLERS,
    TOOLS,
    handle_calculate_iaa,
    handle_create_annotator,
    handle_export_results,
    handle_generate_annotator,
    handle_generate_dashboard,
    handle_import_tasks,
    handle_merge_annotations,
    handle_validate_schema,
)


class TestToolDefinitions:
    """测试工具定义的完整性."""

    def test_tool_count(self):
        assert len(TOOLS) == 11

    def test_handler_count(self):
        assert len(TOOL_HANDLERS) == 11

    def test_all_tools_have_handlers(self):
        tool_names = {t.name for t in TOOLS}
        handler_names = set(TOOL_HANDLERS.keys())
        assert tool_names == handler_names

    def test_all_tools_have_input_schema(self):
        for tool in TOOLS:
            assert tool.inputSchema is not None
            assert tool.inputSchema["type"] == "object"

    def test_all_tools_have_description(self):
        for tool in TOOLS:
            assert tool.description


class TestValidateSchema:
    """测试 validate_schema handler."""

    def test_valid_scoring_schema(self, sample_schema):
        result = handle_validate_schema({"schema": sample_schema})
        assert len(result) == 1
        assert "验证通过" in result[0].text

    def test_invalid_schema_missing_fields(self):
        result = handle_validate_schema({"schema": {}})
        assert "验证失败" in result[0].text or "警告" in result[0].text

    def test_valid_schema_with_tasks(self, sample_schema, sample_tasks):
        result = handle_validate_schema({
            "schema": sample_schema,
            "tasks": sample_tasks,
        })
        assert "Schema 验证通过" in result[0].text
        assert "任务数据验证通过" in result[0].text

    def test_schema_with_annotation_config(self):
        schema = {
            "project_name": "测试",
            "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
            "annotation_config": {
                "type": "single_choice",
                "options": [
                    {"value": "a", "label": "A"},
                    {"value": "b", "label": "B"},
                ],
            },
        }
        result = handle_validate_schema({"schema": schema})
        assert "验证通过" in result[0].text


class TestCreateAnnotator:
    """测试 create_annotator handler."""

    def test_success(self, sample_schema, sample_tasks, tmp_path):
        output = str(tmp_path / "annotator.html")
        result = handle_create_annotator({
            "schema": sample_schema,
            "tasks": sample_tasks,
            "output_path": output,
        })
        assert "已创建" in result[0].text
        assert Path(output).exists()

    def test_with_guidelines(self, sample_schema, sample_tasks, tmp_path):
        output = str(tmp_path / "annotator.html")
        result = handle_create_annotator({
            "schema": sample_schema,
            "tasks": sample_tasks,
            "output_path": output,
            "guidelines": "# 标注指南\n请认真标注",
            "title": "测试标注",
        })
        assert "已创建" in result[0].text


class TestMergeAnnotations:
    """测试 merge_annotations handler."""

    def test_success(
        self,
        annotator1_results,
        annotator2_results,
        annotator_results_factory,
        tmp_path,
    ):
        files = annotator_results_factory(
            tmp_path, [annotator1_results, annotator2_results]
        )
        output = str(tmp_path / "merged.json")
        result = handle_merge_annotations({
            "result_files": files,
            "output_path": output,
        })
        assert "已合并" in result[0].text
        assert Path(output).exists()


class TestCalculateIAA:
    """测试 calculate_iaa handler."""

    def test_success(
        self,
        annotator1_results,
        annotator2_results,
        annotator_results_factory,
        tmp_path,
    ):
        files = annotator_results_factory(
            tmp_path, [annotator1_results, annotator2_results]
        )
        result = handle_calculate_iaa({"result_files": files})
        assert "一致性" in result[0].text or "IAA" in result[0].text


class TestExportResults:
    """测试 export_results handler."""

    def _create_result_file(self, tmp_path, data):
        path = tmp_path / "results.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def test_export_json(self, tmp_path):
        data = {
            "metadata": {"annotator": "test"},
            "responses": [
                {"task_id": "T1", "score": 3, "comment": "好"},
                {"task_id": "T2", "score": 1, "comment": "差"},
            ],
        }
        result_file = self._create_result_file(tmp_path, data)
        output = str(tmp_path / "export.json")
        result = handle_export_results({
            "result_file": result_file,
            "output_path": output,
            "format": "json",
        })
        assert "导出成功" in result[0].text
        assert "2 条" in result[0].text
        exported = json.loads(Path(output).read_text(encoding="utf-8"))
        assert len(exported) == 2

    def test_export_jsonl(self, tmp_path):
        data = {"responses": [{"task_id": "T1", "score": 3}]}
        result_file = self._create_result_file(tmp_path, data)
        output = str(tmp_path / "export.jsonl")
        result = handle_export_results({
            "result_file": result_file,
            "output_path": output,
            "format": "jsonl",
        })
        assert "导出成功" in result[0].text
        lines = Path(output).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1

    def test_export_csv(self, tmp_path):
        data = {
            "responses": [
                {"task_id": "T1", "score": 3, "comment": "好"},
                {"task_id": "T2", "score": 1, "comment": "差"},
            ]
        }
        result_file = self._create_result_file(tmp_path, data)
        output = str(tmp_path / "export.csv")
        result = handle_export_results({
            "result_file": result_file,
            "output_path": output,
            "format": "csv",
        })
        assert "导出成功" in result[0].text
        content = Path(output).read_text(encoding="utf-8")
        assert "task_id" in content

    def test_export_list_format(self, tmp_path):
        """结果文件是 list 格式而非 dict."""
        data = [{"task_id": "T1", "score": 3}]
        result_file = self._create_result_file(tmp_path, data)
        output = str(tmp_path / "export.json")
        result = handle_export_results({
            "result_file": result_file,
            "output_path": output,
            "format": "json",
        })
        assert "导出成功" in result[0].text

    def test_export_invalid_format(self, tmp_path):
        """无法识别的格式."""
        data = {"some_key": "value"}
        result_file = self._create_result_file(tmp_path, data)
        output = str(tmp_path / "export.json")
        result = handle_export_results({
            "result_file": result_file,
            "output_path": output,
        })
        assert "失败" in result[0].text


class TestImportTasks:
    """测试 import_tasks handler."""

    def test_import_json_list(self, tmp_path):
        tasks = [
            {"id": "T1", "data": {"text": "hello"}},
            {"id": "T2", "data": {"text": "world"}},
        ]
        input_file = tmp_path / "tasks.json"
        input_file.write_text(
            json.dumps(tasks, ensure_ascii=False), encoding="utf-8"
        )
        output = str(tmp_path / "output.json")
        result = handle_import_tasks({
            "input_file": str(input_file),
            "output_path": output,
        })
        assert "导入成功" in result[0].text
        assert "2 条" in result[0].text

    def test_import_json_wrapped(self, tmp_path):
        data = {"tasks": [{"id": "T1", "data": {"text": "hi"}}]}
        input_file = tmp_path / "tasks.json"
        input_file.write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        output = str(tmp_path / "output.json")
        result = handle_import_tasks({
            "input_file": str(input_file),
            "output_path": output,
        })
        assert "1 条" in result[0].text

    def test_import_jsonl(self, tmp_path):
        input_file = tmp_path / "tasks.jsonl"
        lines = [
            json.dumps({"id": "T1", "data": {"text": "a"}}, ensure_ascii=False),
            json.dumps({"id": "T2", "data": {"text": "b"}}, ensure_ascii=False),
        ]
        input_file.write_text("\n".join(lines), encoding="utf-8")
        output = str(tmp_path / "output.json")
        result = handle_import_tasks({
            "input_file": str(input_file),
            "output_path": output,
        })
        assert "2 条" in result[0].text

    def test_import_csv(self, tmp_path):
        input_file = tmp_path / "tasks.csv"
        input_file.write_text(
            "id,text\nT1,hello\nT2,world\n", encoding="utf-8"
        )
        output = str(tmp_path / "output.json")
        result = handle_import_tasks({
            "input_file": str(input_file),
            "output_path": output,
        })
        assert "2 条" in result[0].text
        imported = json.loads(Path(output).read_text(encoding="utf-8"))
        assert imported[0]["id"] == "T1"

    def test_import_auto_detect_format(self, tmp_path):
        """自动检测 CSV 格式."""
        input_file = tmp_path / "data.csv"
        input_file.write_text("id,text\nT1,hi\n", encoding="utf-8")
        output = str(tmp_path / "output.json")
        result = handle_import_tasks({
            "input_file": str(input_file),
            "output_path": output,
        })
        assert "1 条" in result[0].text


class TestGenerateAnnotator:
    """测试 generate_annotator handler."""

    def test_success(self, sample_schema, sample_tasks, tmp_path):
        """DataRecipe 目录成功 → lines 286-302."""
        # Build DataRecipe structure
        schema_path = tmp_path / "DATA_SCHEMA.json"
        schema_path.write_text(
            json.dumps(sample_schema, ensure_ascii=False), encoding="utf-8"
        )
        samples_dir = tmp_path / "09_样例数据"
        samples_dir.mkdir()
        (samples_dir / "samples.json").write_text(
            json.dumps({"samples": sample_tasks}, ensure_ascii=False), encoding="utf-8"
        )
        output = str(tmp_path / "annotator.html")
        result = handle_generate_annotator({
            "analysis_dir": str(tmp_path),
            "output_path": output,
        })
        assert "已生成" in result[0].text
        assert Path(output).exists()

    def test_failure(self, tmp_path):
        """无效目录 → line 302."""
        result = handle_generate_annotator({
            "analysis_dir": str(tmp_path),
        })
        assert "失败" in result[0].text


class TestGenerateDashboard:
    """测试 generate_dashboard handler."""

    def test_success(
        self,
        annotator1_results,
        annotator2_results,
        annotator_results_factory,
        tmp_path,
    ):
        files = annotator_results_factory(
            tmp_path, [annotator1_results, annotator2_results]
        )
        output = str(tmp_path / "dashboard.html")
        result = handle_generate_dashboard({
            "result_files": files,
            "output_path": output,
        })
        assert "仪表盘已生成" in result[0].text
        assert Path(output).exists()

    def test_failure(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{bad", encoding="utf-8")
        output = str(tmp_path / "dashboard.html")
        result = handle_generate_dashboard({
            "result_files": [str(f)],
            "output_path": output,
        })
        assert "失败" in result[0].text


class TestHandlerErrorPaths:
    """测试 handler 错误分支."""

    def test_create_annotator_failure(self, tmp_path):
        """无效 schema → line 326."""
        result = handle_create_annotator({
            "schema": {"fields": "not_a_list"},
            "tasks": [],
            "output_path": str(tmp_path / "out.html"),
        })
        assert "失败" in result[0].text

    def test_merge_annotations_failure(self, tmp_path):
        """损坏文件 → line 350."""
        f1 = tmp_path / "a1.json"
        f2 = tmp_path / "a2.json"
        f1.write_text("{bad", encoding="utf-8")
        f2.write_text("{bad", encoding="utf-8")
        result = handle_merge_annotations({
            "result_files": [str(f1), str(f2)],
            "output_path": str(tmp_path / "merged.json"),
        })
        assert "失败" in result[0].text

    def test_calculate_iaa_error(self, tmp_path):
        """空 responses → error → line 357."""
        f1 = tmp_path / "a1.json"
        f2 = tmp_path / "a2.json"
        f1.write_text(json.dumps({"responses": []}), encoding="utf-8")
        f2.write_text(json.dumps({"responses": []}), encoding="utf-8")
        result = handle_calculate_iaa({
            "result_files": [str(f1), str(f2)],
        })
        assert "失败" in result[0].text

    def test_validate_schema_invalid_tasks(self, sample_schema):
        """tasks 含非字典 → lines 392-394."""
        result = handle_validate_schema({
            "schema": sample_schema,
            "tasks": ["not_a_dict"],
        })
        assert "任务数据验证失败" in result[0].text

    def test_validate_schema_task_warnings(self, sample_schema):
        """空 tasks → task warnings → lines 396-398."""
        result = handle_validate_schema({
            "schema": sample_schema,
            "tasks": [],
        })
        assert "警告" in result[0].text
