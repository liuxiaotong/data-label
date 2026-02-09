"""io.py 单元测试."""

import json

import pytest

from datalabel.io import export_responses, extract_responses, import_tasks_from_file


class TestExportResponses:
    """测试 export_responses."""

    def test_export_json(self, tmp_path):
        responses = [{"task_id": "T1", "score": 3}, {"task_id": "T2", "score": 1}]
        output = tmp_path / "out.json"
        count = export_responses(responses, output, "json")
        assert count == 2
        data = json.loads(output.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["task_id"] == "T1"

    def test_export_jsonl(self, tmp_path):
        responses = [{"task_id": "T1", "score": 3}]
        output = tmp_path / "out.jsonl"
        count = export_responses(responses, output, "jsonl")
        assert count == 1
        lines = output.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        assert json.loads(lines[0])["task_id"] == "T1"

    def test_export_csv(self, tmp_path):
        responses = [
            {"task_id": "T1", "score": 3, "comment": "好"},
            {"task_id": "T2", "score": 1, "comment": "差"},
        ]
        output = tmp_path / "out.csv"
        count = export_responses(responses, output, "csv")
        assert count == 2
        content = output.read_text(encoding="utf-8")
        assert "task_id" in content
        assert "T1" in content

    def test_export_csv_with_list_values(self, tmp_path):
        responses = [{"task_id": "T1", "choices": ["a", "b"]}]
        output = tmp_path / "out.csv"
        export_responses(responses, output, "csv")
        content = output.read_text(encoding="utf-8")
        assert "choices" in content
        assert "T1" in content

    def test_export_csv_empty(self, tmp_path):
        output = tmp_path / "out.csv"
        count = export_responses([], output, "csv")
        assert count == 0
        assert output.read_text(encoding="utf-8") == ""

    def test_export_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "sub" / "dir" / "out.json"
        export_responses([{"a": 1}], output, "json")
        assert output.exists()

    def test_export_invalid_format(self, tmp_path):
        with pytest.raises(ValueError, match="不支持"):
            export_responses([], tmp_path / "out.txt", "xml")

    def test_export_chinese_content(self, tmp_path):
        responses = [{"task_id": "T1", "comment": "中文评价"}]
        output = tmp_path / "out.json"
        export_responses(responses, output, "json")
        content = output.read_text(encoding="utf-8")
        assert "中文评价" in content


class TestImportTasksFromFile:
    """测试 import_tasks_from_file."""

    def test_import_json_list(self, tmp_path):
        path = tmp_path / "tasks.json"
        path.write_text(
            json.dumps([{"id": "T1"}, {"id": "T2"}], ensure_ascii=False),
            encoding="utf-8",
        )
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 2

    def test_import_json_wrapped_tasks(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text(
            json.dumps({"tasks": [{"id": "T1"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 1

    def test_import_json_wrapped_samples(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text(
            json.dumps({"samples": [{"id": "S1"}, {"id": "S2"}]}, ensure_ascii=False),
            encoding="utf-8",
        )
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 2

    def test_import_jsonl(self, tmp_path):
        path = tmp_path / "tasks.jsonl"
        lines = ['{"id": "T1"}', '{"id": "T2"}', ""]
        path.write_text("\n".join(lines), encoding="utf-8")
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 2

    def test_import_csv(self, tmp_path):
        path = tmp_path / "tasks.csv"
        path.write_text("id,text\nT1,hello\nT2,world\n", encoding="utf-8")
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 2
        assert tasks[0]["id"] == "T1"

    def test_import_csv_with_json_values(self, tmp_path):
        path = tmp_path / "tasks.csv"
        path.write_text('id,data\nT1,"{""key"": ""val""}"\n', encoding="utf-8")
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 1

    def test_auto_detect_jsonl(self, tmp_path):
        path = tmp_path / "data.jsonl"
        path.write_text('{"id": "T1"}\n', encoding="utf-8")
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 1

    def test_auto_detect_csv(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("id\nT1\n", encoding="utf-8")
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 1

    def test_explicit_format_overrides_extension(self, tmp_path):
        path = tmp_path / "data.txt"
        path.write_text('{"id": "T1"}\n', encoding="utf-8")
        tasks = import_tasks_from_file(path, fmt="jsonl")
        assert len(tasks) == 1

    def test_import_csv_malformed_json_fallback(self, tmp_path):
        """CSV value starting with { but not valid JSON keeps raw string."""
        path = tmp_path / "tasks.csv"
        path.write_text("id,data\nT1,{invalid json}\n", encoding="utf-8")
        tasks = import_tasks_from_file(path)
        assert len(tasks) == 1
        assert tasks[0]["data"] == "{invalid json}"

    def test_invalid_format(self, tmp_path):
        path = tmp_path / "data.txt"
        path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="不支持"):
            import_tasks_from_file(path, fmt="xml")


class TestExtractResponses:
    """测试 extract_responses."""

    def test_list_input(self):
        data = [{"task_id": "T1"}]
        assert extract_responses(data) == [{"task_id": "T1"}]

    def test_dict_with_responses(self):
        data = {"metadata": {}, "responses": [{"task_id": "T1"}]}
        assert extract_responses(data) == [{"task_id": "T1"}]

    def test_unrecognized_format(self):
        assert extract_responses({"some_key": "value"}) is None

    def test_string_input(self):
        assert extract_responses("not valid") is None

    def test_empty_list(self):
        assert extract_responses([]) == []

    def test_empty_responses(self):
        assert extract_responses({"responses": []}) == []
