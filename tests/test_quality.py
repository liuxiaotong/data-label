"""标注质量分析测试 — 全部 mock LLM 调用。"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from datalabel.llm.client import LLMClient, LLMResponse, LLMUsage
from datalabel.llm.quality import (
    QualityAnalyzer,
    _find_disagreements,
    _load_results,
)


SAMPLE_SCHEMA = {
    "project_name": "测试项目",
    "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
    "scoring_rubric": [
        {"score": 1, "label": "优秀", "description": "好"},
        {"score": 0, "label": "差", "description": "差"},
    ],
}


def _write_result_file(tmpdir: Path, name: str, responses: list[dict], annotator: str) -> str:
    """Helper: write a result file."""
    path = tmpdir / name
    data = {
        "metadata": {"annotator": annotator},
        "responses": responses,
    }
    path.write_text(json.dumps(data, ensure_ascii=False))
    return str(path)


class TestLoadResults:
    def test_load_single_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path = _write_result_file(
                tmpdir, "r1.json",
                [{"task_id": "T1", "score": 1}],
                "ann1",
            )
            results = _load_results([path])
            assert len(results) == 1
            assert results[0]["annotator"] == "ann1"
            assert results[0]["responses"][0]["_annotator"] == "ann1"


class TestFindDisagreements:
    def test_no_disagreement(self):
        results = [
            {"annotator": "a1", "responses": [{"task_id": "T1", "score": 1}]},
            {"annotator": "a2", "responses": [{"task_id": "T1", "score": 1}]},
        ]
        assert _find_disagreements(results) == []

    def test_found_disagreement(self):
        results = [
            {"annotator": "a1", "responses": [{"task_id": "T1", "score": 1}]},
            {"annotator": "a2", "responses": [{"task_id": "T1", "score": 0}]},
        ]
        disag = _find_disagreements(results)
        assert len(disag) == 1
        assert disag[0]["task_id"] == "T1"

    def test_single_annotator_no_disagreement(self):
        results = [
            {"annotator": "a1", "responses": [{"task_id": "T1", "score": 1}]},
        ]
        assert _find_disagreements(results) == []


def _mock_quality_client(
    quality_response: dict,
    disagreement_response: dict | None = None,
) -> LLMClient:
    """Create mock client for quality analysis."""
    client = MagicMock(spec=LLMClient)
    responses = [
        (
            quality_response,
            LLMResponse(
                content=json.dumps(quality_response),
                usage=LLMUsage(prompt_tokens=50, completion_tokens=100, total_tokens=150),
            ),
        )
    ]
    if disagreement_response is not None:
        responses.append((
            disagreement_response,
            LLMResponse(
                content=json.dumps(disagreement_response),
                usage=LLMUsage(prompt_tokens=30, completion_tokens=60, total_tokens=90),
            ),
        ))
    client.chat_json.side_effect = responses
    return client


class TestQualityAnalyzer:
    def test_single_annotator_analysis(self):
        quality_resp = {
            "issues": [
                {
                    "task_id": "T1",
                    "issue_type": "suspicious",
                    "severity": "high",
                    "description": "标注与内容不匹配",
                    "suggestion": "重新审核",
                }
            ],
            "summary": "发现 1 个可疑标注",
        }
        client = _mock_quality_client(quality_resp)
        analyzer = QualityAnalyzer(client=client)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            f1 = _write_result_file(
                tmpdir, "r1.json",
                [{"task_id": "T1", "score": 1}],
                "ann1",
            )
            report = analyzer.analyze(SAMPLE_SCHEMA, [f1])

        assert report.success
        assert len(report.issues) == 1
        assert report.issues[0].task_id == "T1"
        assert report.issues[0].issue_type == "suspicious"
        assert report.summary == "发现 1 个可疑标注"
        assert report.disagreement_analysis is None

    def test_multi_annotator_with_disagreement(self):
        quality_resp = {"issues": [], "summary": "整体质量良好"}
        disagree_resp = {
            "analyses": [{"task_id": "T1", "root_cause": "标准模糊"}],
            "common_patterns": "评分标准理解不一致",
            "guideline_suggestions": "细化标准",
        }
        client = _mock_quality_client(quality_resp, disagree_resp)
        analyzer = QualityAnalyzer(client=client)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            f1 = _write_result_file(
                tmpdir, "r1.json",
                [{"task_id": "T1", "score": 1}],
                "ann1",
            )
            f2 = _write_result_file(
                tmpdir, "r2.json",
                [{"task_id": "T1", "score": 0}],
                "ann2",
            )
            report = analyzer.analyze(SAMPLE_SCHEMA, [f1, f2])

        assert report.success
        assert report.disagreement_analysis is not None
        assert "analyses" in report.disagreement_analysis
        # Two LLM calls: quality + disagreement
        assert client.chat_json.call_count == 2
        assert report.total_usage.total_tokens == 240  # 150 + 90

    def test_output_file(self):
        quality_resp = {"issues": [], "summary": "OK"}
        client = _mock_quality_client(quality_resp)
        analyzer = QualityAnalyzer(client=client)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            f1 = _write_result_file(
                tmpdir, "r1.json",
                [{"task_id": "T1", "score": 1}],
                "ann1",
            )
            out = str(tmpdir / "report.json")
            report = analyzer.analyze(SAMPLE_SCHEMA, [f1], output_path=out)

            assert report.output_path == out
            data = json.loads(Path(out).read_text())
            assert "summary" in data
            assert "issues" in data

    def test_llm_error(self):
        client = MagicMock(spec=LLMClient)
        client.chat_json.return_value = (
            None,
            LLMResponse(success=False, error="API error"),
        )
        analyzer = QualityAnalyzer(client=client)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            f1 = _write_result_file(
                tmpdir, "r1.json",
                [{"task_id": "T1", "score": 1}],
                "ann1",
            )
            report = analyzer.analyze(SAMPLE_SCHEMA, [f1])

        assert not report.success
        assert "API error" in report.error
