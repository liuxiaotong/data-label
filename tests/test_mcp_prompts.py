"""MCP Prompt 单元测试."""

import pytest

from datalabel.mcp_server._prompts import PROMPTS, get_prompt_messages


class TestPromptDefinitions:
    """测试 Prompt 定义."""

    def test_prompt_count(self):
        assert len(PROMPTS) == 3

    def test_prompt_names(self):
        names = {p.name for p in PROMPTS}
        assert names == {
            "create-annotation-schema",
            "review-annotations",
            "annotation-workflow",
        }

    def test_all_prompts_have_description(self):
        for p in PROMPTS:
            assert p.description

    def test_all_prompts_have_arguments(self):
        for p in PROMPTS:
            assert p.arguments


class TestCreateAnnotationSchemaPrompt:
    """测试 create-annotation-schema prompt."""

    def test_basic(self):
        messages = get_prompt_messages(
            "create-annotation-schema",
            {"task_description": "情感分析任务"},
        )
        assert len(messages) >= 1
        assert messages[0].role == "user"
        assert "情感分析" in messages[0].content.text

    def test_with_annotation_type(self):
        messages = get_prompt_messages(
            "create-annotation-schema",
            {
                "task_description": "文本分类",
                "annotation_type": "single_choice",
            },
        )
        text = messages[0].content.text
        assert "single_choice" in text

    def test_with_known_type_includes_example(self):
        messages = get_prompt_messages(
            "create-annotation-schema",
            {
                "task_description": "评分",
                "annotation_type": "scoring",
            },
        )
        text = messages[0].content.text
        assert "scoring_rubric" in text

    def test_without_type_includes_all_types(self):
        messages = get_prompt_messages(
            "create-annotation-schema",
            {"task_description": "标注任务"},
        )
        text = messages[0].content.text
        assert "scoring" in text
        assert "single_choice" in text


class TestReviewAnnotationsPrompt:
    """测试 review-annotations prompt."""

    def test_basic(self):
        messages = get_prompt_messages(
            "review-annotations",
            {
                "schema": '{"project_name": "test"}',
                "results": '[{"task_id": "T1", "score": 3}]',
            },
        )
        assert len(messages) >= 1
        text = messages[0].content.text
        assert "质量" in text
        assert "一致性" in text

    def test_includes_data(self):
        messages = get_prompt_messages(
            "review-annotations",
            {
                "schema": '{"type": "scoring"}',
                "results": '[{"score": 1}]',
            },
        )
        text = messages[0].content.text
        assert "scoring" in text


class TestAnnotationWorkflowPrompt:
    """测试 annotation-workflow prompt."""

    def test_basic(self):
        messages = get_prompt_messages(
            "annotation-workflow",
            {"project_description": "LLM 输出质量标注"},
        )
        assert len(messages) >= 1
        text = messages[0].content.text
        assert "LLM 输出质量标注" in text
        assert "validate_schema" in text
        assert "create_annotator" in text

    def test_with_data_sample(self):
        messages = get_prompt_messages(
            "annotation-workflow",
            {
                "project_description": "测试项目",
                "data_sample": '{"id": "T1", "text": "hello"}',
            },
        )
        text = messages[0].content.text
        assert "hello" in text

    def test_workflow_steps(self):
        messages = get_prompt_messages(
            "annotation-workflow",
            {"project_description": "测试"},
        )
        text = messages[0].content.text
        assert "步骤 1" in text
        assert "步骤 5" in text


class TestUnknownPrompt:
    """测试未知 prompt."""

    def test_unknown_prompt_raises(self):
        with pytest.raises(ValueError, match="未知"):
            get_prompt_messages("nonexistent", {})
