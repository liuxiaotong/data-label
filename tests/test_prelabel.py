"""自动预标注测试 — 全部 mock LLM 调用。"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from datalabel.llm.client import LLMClient, LLMResponse, LLMUsage
from datalabel.llm.prelabel import (
    PreLabeler,
    _build_annotation_spec,
    _build_output_fields,
    _detect_annotation_type,
)


SAMPLE_SCHEMA = {
    "project_name": "测试项目",
    "fields": [
        {"name": "instruction", "display_name": "指令", "type": "text"},
        {"name": "response", "display_name": "回答", "type": "text"},
    ],
    "scoring_rubric": [
        {"score": 1, "label": "优秀", "description": "好"},
        {"score": 0.5, "label": "一般", "description": "中"},
        {"score": 0, "label": "差", "description": "差"},
    ],
}

SAMPLE_TASKS = [
    {"id": "T1", "data": {"instruction": "问题1", "response": "回答1"}},
    {"id": "T2", "data": {"instruction": "问题2", "response": "回答2"}},
    {"id": "T3", "data": {"instruction": "问题3", "response": "回答3"}},
]

CHOICE_SCHEMA = {
    "project_name": "分类项目",
    "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
    "annotation_config": {
        "type": "single_choice",
        "options": [
            {"value": "pos", "label": "正面"},
            {"value": "neg", "label": "负面"},
        ],
    },
}


class TestDetectAnnotationType:
    def test_scoring_from_rubric(self):
        assert _detect_annotation_type(SAMPLE_SCHEMA) == "scoring"

    def test_from_annotation_config(self):
        assert _detect_annotation_type(CHOICE_SCHEMA) == "single_choice"

    def test_default_scoring(self):
        assert _detect_annotation_type({"fields": []}) == "scoring"


class TestBuildAnnotationSpec:
    def test_scoring_spec(self):
        spec = _build_annotation_spec(SAMPLE_SCHEMA, "scoring")
        assert "1 分" in spec
        assert "优秀" in spec

    def test_single_choice_spec(self):
        spec = _build_annotation_spec(CHOICE_SCHEMA, "single_choice")
        assert "单选" in spec
        assert "pos" in spec

    def test_multi_choice_spec(self):
        schema = {
            "annotation_config": {
                "type": "multi_choice",
                "options": [{"value": "a", "label": "A"}],
            }
        }
        spec = _build_annotation_spec(schema, "multi_choice")
        assert "多选" in spec

    def test_text_spec(self):
        schema = {
            "annotation_config": {
                "type": "text",
                "placeholder": "请输入...",
            }
        }
        spec = _build_annotation_spec(schema, "text")
        assert "请输入" in spec

    def test_ranking_spec(self):
        schema = {
            "annotation_config": {
                "type": "ranking",
                "options": [{"value": "r1", "label": "结果1"}],
            }
        }
        spec = _build_annotation_spec(schema, "ranking")
        assert "排序" in spec


class TestBuildOutputFields:
    def test_scoring(self):
        assert "score" in _build_output_fields("scoring")

    def test_single_choice(self):
        assert "choice" in _build_output_fields("single_choice")

    def test_multi_choice(self):
        assert "choices" in _build_output_fields("multi_choice")

    def test_text(self):
        assert "text" in _build_output_fields("text")

    def test_ranking(self):
        assert "ranking" in _build_output_fields("ranking")


def _mock_client_returning(responses: list[list[dict]]) -> LLMClient:
    """Create a mock LLM client that returns given batch responses sequentially."""
    client = MagicMock(spec=LLMClient)
    side_effects = []
    for batch_resp in responses:
        side_effects.append((
            batch_resp,
            LLMResponse(
                content=json.dumps(batch_resp),
                usage=LLMUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            ),
        ))
    client.chat_json.side_effect = side_effects
    return client


class TestPreLabeler:
    def test_basic_prelabel(self):
        mock_resp = [
            {"task_id": "T1", "score": 1, "comment": "好"},
            {"task_id": "T2", "score": 0.5, "comment": "中"},
            {"task_id": "T3", "score": 0, "comment": "差"},
        ]
        client = _mock_client_returning([mock_resp])
        labeler = PreLabeler(client=client)

        result = labeler.prelabel(SAMPLE_SCHEMA, SAMPLE_TASKS, batch_size=10)

        assert result.success
        assert result.total_tasks == 3
        assert result.labeled_tasks == 3
        assert result.responses[0]["source"] == "llm_prelabel"
        assert result.total_usage.total_tokens == 30

    def test_batching(self):
        """Tasks split into batches correctly."""
        batch1 = [
            {"task_id": "T1", "score": 1, "comment": ""},
            {"task_id": "T2", "score": 0.5, "comment": ""},
        ]
        batch2 = [
            {"task_id": "T3", "score": 0, "comment": ""},
        ]
        client = _mock_client_returning([batch1, batch2])
        labeler = PreLabeler(client=client)

        result = labeler.prelabel(SAMPLE_SCHEMA, SAMPLE_TASKS, batch_size=2)

        assert result.success
        assert result.labeled_tasks == 3
        assert client.chat_json.call_count == 2
        # Token usage accumulated
        assert result.total_usage.total_tokens == 60

    def test_output_file(self):
        mock_resp = [{"task_id": "T1", "score": 1, "comment": ""}]
        client = _mock_client_returning([mock_resp])
        labeler = PreLabeler(client=client)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "pre.json")
            result = labeler.prelabel(SAMPLE_SCHEMA, SAMPLE_TASKS[:1], output_path=out)

            assert result.output_path == out
            data = json.loads(Path(out).read_text())
            assert "responses" in data
            assert data["responses"][0]["task_id"] == "T1"

    def test_llm_error(self):
        client = MagicMock(spec=LLMClient)
        client.chat_json.return_value = (
            None,
            LLMResponse(success=False, error="API 超时"),
        )
        labeler = PreLabeler(client=client)

        result = labeler.prelabel(SAMPLE_SCHEMA, SAMPLE_TASKS)

        assert not result.success
        assert "API 超时" in result.error

    def test_non_list_response_handled(self):
        """LLM returns a dict instead of list — should not crash."""
        client = MagicMock(spec=LLMClient)
        client.chat_json.return_value = (
            {"error": "bad format"},
            LLMResponse(
                content='{"error": "bad format"}',
                usage=LLMUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
            ),
        )
        labeler = PreLabeler(client=client)

        result = labeler.prelabel(SAMPLE_SCHEMA, SAMPLE_TASKS[:1], batch_size=5)

        assert result.success  # No crash, just 0 labeled
        assert result.labeled_tasks == 0
