"""标注指南生成测试 — 全部 mock LLM 调用。"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from datalabel.llm.client import LLMClient, LLMResponse, LLMUsage
from datalabel.llm.guidelines import GuidelinesGenerator


SAMPLE_SCHEMA = {
    "project_name": "测试项目",
    "fields": [{"name": "text", "display_name": "文本", "type": "text"}],
    "scoring_rubric": [
        {"score": 1, "label": "优秀", "description": "好"},
        {"score": 0, "label": "差", "description": "差"},
    ],
}

SAMPLE_TASKS = [
    {"id": "T1", "data": {"text": "示例文本1"}},
    {"id": "T2", "data": {"text": "示例文本2"}},
]

MOCK_GUIDELINES = """\
# 标注指南

## 1. 项目概述
本项目旨在评估文本质量。

## 2. 评判标准
- 1 分: 优秀
- 0 分: 差
"""


def _mock_client(content: str) -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.chat.return_value = LLMResponse(
        content=content,
        usage=LLMUsage(prompt_tokens=100, completion_tokens=500, total_tokens=600),
    )
    return client


class TestGuidelinesGenerator:
    def test_basic_generation(self):
        client = _mock_client(MOCK_GUIDELINES)
        gen = GuidelinesGenerator(client=client)

        result = gen.generate(SAMPLE_SCHEMA, tasks=SAMPLE_TASKS)

        assert result.success
        assert "标注指南" in result.content
        assert result.total_usage.total_tokens == 600
        # Verify chat was called with system + user messages
        call_args = client.chat.call_args[0][0]
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"

    def test_chinese_language(self):
        client = _mock_client(MOCK_GUIDELINES)
        gen = GuidelinesGenerator(client=client)

        gen.generate(SAMPLE_SCHEMA, language="zh")

        call_args = client.chat.call_args[0][0]
        # Chinese system prompt should contain 标注指南
        assert "标注指南" in call_args[0]["content"]

    def test_english_language(self):
        client = _mock_client("# Annotation Guidelines\n...")
        gen = GuidelinesGenerator(client=client)

        gen.generate(SAMPLE_SCHEMA, language="en")

        call_args = client.chat.call_args[0][0]
        assert "annotation" in call_args[0]["content"].lower()

    def test_no_tasks(self):
        client = _mock_client(MOCK_GUIDELINES)
        gen = GuidelinesGenerator(client=client)

        result = gen.generate(SAMPLE_SCHEMA)

        assert result.success
        call_args = client.chat.call_args[0][0]
        assert "无样例" in call_args[1]["content"]

    def test_output_file(self):
        client = _mock_client(MOCK_GUIDELINES)
        gen = GuidelinesGenerator(client=client)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "guide.md")
            result = gen.generate(SAMPLE_SCHEMA, output_path=out)

            assert result.output_path == out
            content = Path(out).read_text()
            assert "标注指南" in content

    def test_sample_count_limit(self):
        """Only uses up to sample_count tasks."""
        many_tasks = [{"id": f"T{i}", "data": {"text": f"text{i}"}} for i in range(20)]
        client = _mock_client(MOCK_GUIDELINES)
        gen = GuidelinesGenerator(client=client)

        gen.generate(SAMPLE_SCHEMA, tasks=many_tasks, sample_count=3)

        call_args = client.chat.call_args[0][0]
        user_content = call_args[1]["content"]
        # Should contain T0, T1, T2 but not T3+
        assert "T0" in user_content
        assert "T2" in user_content
        assert "T3" not in user_content

    def test_llm_error(self):
        client = MagicMock(spec=LLMClient)
        client.chat.return_value = LLMResponse(success=False, error="timeout")
        gen = GuidelinesGenerator(client=client)

        result = gen.generate(SAMPLE_SCHEMA)

        assert not result.success
        assert "timeout" in result.error
