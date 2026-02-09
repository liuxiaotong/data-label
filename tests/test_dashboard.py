"""DashboardGenerator 单元测试."""

import json
from pathlib import Path

import pytest

from datalabel.dashboard import DashboardGenerator, DashboardResult


@pytest.fixture
def dashboard_gen():
    return DashboardGenerator()


@pytest.fixture
def scoring_results_pair(tmp_path):
    """两个标注员的评分结果文件."""
    ann1 = {
        "metadata": {"annotator": "ann1", "total_tasks": 3},
        "responses": [
            {"task_id": "T1", "score": 3, "annotated_at": "2025-01-15T10:00:00"},
            {"task_id": "T2", "score": 2, "annotated_at": "2025-01-15T11:00:00"},
            {"task_id": "T3", "score": 3, "annotated_at": "2025-01-16T09:00:00"},
        ],
    }
    ann2 = {
        "metadata": {"annotator": "ann2", "total_tasks": 3},
        "responses": [
            {"task_id": "T1", "score": 3, "annotated_at": "2025-01-15T14:00:00"},
            {"task_id": "T2", "score": 1, "annotated_at": "2025-01-15T15:00:00"},
            {"task_id": "T3", "score": 3, "annotated_at": "2025-01-16T10:00:00"},
        ],
    }
    f1 = tmp_path / "ann1.json"
    f2 = tmp_path / "ann2.json"
    f1.write_text(json.dumps(ann1, ensure_ascii=False), encoding="utf-8")
    f2.write_text(json.dumps(ann2, ensure_ascii=False), encoding="utf-8")
    return [str(f1), str(f2)]


@pytest.fixture
def choice_results_pair(tmp_path):
    """两个标注员的单选结果文件."""
    ann1 = {
        "metadata": {"annotator": "ann1"},
        "responses": [
            {"task_id": "T1", "choice": "A"},
            {"task_id": "T2", "choice": "B"},
        ],
    }
    ann2 = {
        "metadata": {"annotator": "ann2"},
        "responses": [
            {"task_id": "T1", "choice": "A"},
            {"task_id": "T2", "choice": "A"},
        ],
    }
    f1 = tmp_path / "ann1.json"
    f2 = tmp_path / "ann2.json"
    f1.write_text(json.dumps(ann1, ensure_ascii=False), encoding="utf-8")
    f2.write_text(json.dumps(ann2, ensure_ascii=False), encoding="utf-8")
    return [str(f1), str(f2)]


class TestDashboardResult:
    def test_defaults(self):
        r = DashboardResult()
        assert r.success is True
        assert r.error == ""
        assert r.output_path == ""
        assert r.annotator_count == 0
        assert r.total_tasks == 0
        assert r.overall_completion == 0.0


class TestDashboardGenerate:
    def test_basic_scoring(self, dashboard_gen, scoring_results_pair, tmp_path):
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=scoring_results_pair,
            output_path=output,
        )
        assert result.success
        assert result.annotator_count == 2
        assert result.total_tasks == 3
        assert result.overall_completion == 1.0
        assert Path(output).exists()
        content = Path(output).read_text(encoding="utf-8")
        assert "标注进度仪表盘" in content
        assert "ann1" in content
        assert "ann2" in content

    def test_custom_title(self, dashboard_gen, scoring_results_pair, tmp_path):
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=scoring_results_pair,
            output_path=output,
            title="我的仪表盘",
        )
        assert result.success
        content = Path(output).read_text(encoding="utf-8")
        assert "我的仪表盘" in content

    def test_single_annotator(self, dashboard_gen, tmp_path):
        ann1 = {
            "metadata": {"annotator": "solo"},
            "responses": [
                {"task_id": "T1", "score": 3},
                {"task_id": "T2", "score": 2},
            ],
        }
        f1 = tmp_path / "solo.json"
        f1.write_text(json.dumps(ann1, ensure_ascii=False), encoding="utf-8")
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=[str(f1)],
            output_path=output,
        )
        assert result.success
        assert result.annotator_count == 1
        content = Path(output).read_text(encoding="utf-8")
        assert "至少 2 位标注员" in content

    def test_choice_type(self, dashboard_gen, choice_results_pair, tmp_path):
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=choice_results_pair,
            output_path=output,
        )
        assert result.success
        content = Path(output).read_text(encoding="utf-8")
        # Distribution chart should be present
        assert "<svg" in content

    def test_empty_results(self, dashboard_gen):
        result = dashboard_gen.generate(
            result_files=[],
            output_path="/tmp/nope.html",
        )
        assert not result.success
        assert "没有可用" in result.error

    def test_corrupted_file(self, dashboard_gen, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{bad json", encoding="utf-8")
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=[str(f)],
            output_path=output,
        )
        assert not result.success

    def test_with_schema(self, dashboard_gen, scoring_results_pair, tmp_path, sample_schema):
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=scoring_results_pair,
            output_path=output,
            schema=sample_schema,
        )
        assert result.success

    def test_time_analysis_present(self, dashboard_gen, scoring_results_pair, tmp_path):
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=scoring_results_pair,
            output_path=output,
        )
        assert result.success
        content = Path(output).read_text(encoding="utf-8")
        assert "标注时间分布" in content

    def test_conflicts_shown(self, dashboard_gen, scoring_results_pair, tmp_path):
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=scoring_results_pair,
            output_path=output,
        )
        assert result.success
        content = Path(output).read_text(encoding="utf-8")
        # T2 has score 2 vs 1 → conflict
        assert "标注分歧" in content
        assert "T2" in content


class TestDashboardDistribution:
    def test_multi_choice(self, dashboard_gen, tmp_path):
        ann = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "T1", "choices": ["A", "B"]},
                {"task_id": "T2", "choices": ["B", "C"]},
            ],
        }
        f = tmp_path / "ann.json"
        f.write_text(json.dumps(ann, ensure_ascii=False), encoding="utf-8")
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=[str(f)],
            output_path=output,
        )
        assert result.success
        content = Path(output).read_text(encoding="utf-8")
        assert "<svg" in content

    def test_text_type_no_chart(self, dashboard_gen, tmp_path):
        ann = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "T1", "text": "hello"},
                {"task_id": "T2", "text": "world"},
            ],
        }
        f = tmp_path / "ann.json"
        f.write_text(json.dumps(ann, ensure_ascii=False), encoding="utf-8")
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=[str(f)],
            output_path=output,
        )
        assert result.success
        content = Path(output).read_text(encoding="utf-8")
        assert "文本标注不支持分布图" in content

    def test_ranking_type(self, dashboard_gen, tmp_path):
        ann = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "T1", "ranking": ["A", "B", "C"]},
                {"task_id": "T2", "ranking": ["B", "A", "C"]},
            ],
        }
        f = tmp_path / "ann.json"
        f.write_text(json.dumps(ann, ensure_ascii=False), encoding="utf-8")
        output = str(tmp_path / "dashboard.html")
        result = dashboard_gen.generate(
            result_files=[str(f)],
            output_path=output,
        )
        assert result.success


class TestKappaColor:
    def test_high_kappa(self):
        color = DashboardGenerator._kappa_color_filter(0.9)
        assert "hsl(" in color

    def test_low_kappa(self):
        color = DashboardGenerator._kappa_color_filter(-0.5)
        assert "hsl(" in color

    def test_invalid_value(self):
        color = DashboardGenerator._kappa_color_filter("bad")
        assert "hsl(0, 0%, 70%)" == color

    def test_none_value(self):
        color = DashboardGenerator._kappa_color_filter(None)
        assert "hsl(0, 0%, 70%)" == color


class TestExtractValue:
    def test_score(self):
        assert DashboardGenerator._extract_value({"score": 3}) == 3

    def test_choice(self):
        assert DashboardGenerator._extract_value({"choice": "A"}) == "A"

    def test_choices(self):
        assert DashboardGenerator._extract_value({"choices": ["B", "A"]}) == ("A", "B")

    def test_text(self):
        assert DashboardGenerator._extract_value({"text": "hi"}) == "hi"

    def test_ranking(self):
        assert DashboardGenerator._extract_value({"ranking": [1, 2, 3]}) == (1, 2, 3)

    def test_unknown(self):
        assert DashboardGenerator._extract_value({"foo": "bar"}) is None
