"""Shared test fixtures for DataLabel."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_schema():
    """Sample schema for testing."""
    return {
        "project_name": "测试项目",
        "fields": [
            {"name": "instruction", "display_name": "指令", "type": "text"},
            {"name": "response", "display_name": "回复", "type": "text"},
        ],
        "scoring_rubric": [
            {"score": 1, "label": "差", "description": "质量差"},
            {"score": 2, "label": "中", "description": "质量中等"},
            {"score": 3, "label": "好", "description": "质量好"},
        ],
    }


@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    return [
        {
            "id": "TASK_001",
            "data": {
                "instruction": "什么是机器学习？",
                "response": "机器学习是人工智能的一个分支...",
            },
        },
        {
            "id": "TASK_002",
            "data": {
                "instruction": "解释深度学习",
                "response": "深度学习是机器学习的一种方法...",
            },
        },
    ]


@pytest.fixture
def annotator1_results():
    """Results from annotator 1."""
    return {
        "metadata": {"annotator": "ann1"},
        "responses": [
            {"task_id": "TASK_001", "score": 3, "comment": "好"},
            {"task_id": "TASK_002", "score": 2, "comment": "一般"},
            {"task_id": "TASK_003", "score": 3, "comment": "不错"},
        ],
    }


@pytest.fixture
def annotator2_results():
    """Results from annotator 2."""
    return {
        "metadata": {"annotator": "ann2"},
        "responses": [
            {"task_id": "TASK_001", "score": 3, "comment": "很好"},
            {"task_id": "TASK_002", "score": 1, "comment": "差"},
            {"task_id": "TASK_003", "score": 3, "comment": "好"},
        ],
    }


@pytest.fixture
def annotator3_results():
    """Results from annotator 3."""
    return {
        "metadata": {"annotator": "ann3"},
        "responses": [
            {"task_id": "TASK_001", "score": 3, "comment": "优秀"},
            {"task_id": "TASK_002", "score": 2, "comment": "中等"},
            {"task_id": "TASK_003", "score": 2, "comment": "还行"},
        ],
    }


@pytest.fixture
def annotator_results_factory():
    """Factory to create annotator result files in a temp directory."""

    def _create(tmpdir, results_list):
        files = []
        for i, results in enumerate(results_list):
            path = Path(tmpdir) / f"ann{i + 1}.json"
            path.write_text(json.dumps(results, ensure_ascii=False))
            files.append(str(path))
        return files

    return _create
