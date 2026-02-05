"""Tests for ResultMerger."""

import json
import tempfile
from pathlib import Path

import pytest

from datalabel import ResultMerger


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


class TestResultMerger:
    """Tests for ResultMerger class."""

    def test_merge_majority(self, annotator1_results, annotator2_results, annotator3_results):
        """Test majority voting merge."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write result files
            files = []
            for i, results in enumerate([annotator1_results, annotator2_results, annotator3_results]):
                path = Path(tmpdir) / f"ann{i+1}.json"
                path.write_text(json.dumps(results))
                files.append(str(path))

            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(
                result_files=files,
                output_path=str(output_path),
                strategy="majority",
            )

            assert result.success
            assert result.annotator_count == 3
            assert result.total_tasks == 3

            # Load and verify merged results
            merged = json.loads(output_path.read_text())
            responses = {r["task_id"]: r for r in merged["responses"]}

            # TASK_001: all agree on 3
            assert responses["TASK_001"]["score"] == 3

            # TASK_002: 2, 1, 2 -> majority is 2
            assert responses["TASK_002"]["score"] == 2

            # TASK_003: 3, 3, 2 -> majority is 3
            assert responses["TASK_003"]["score"] == 3

    def test_merge_average(self, annotator1_results, annotator2_results, annotator3_results):
        """Test average merge."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i, results in enumerate([annotator1_results, annotator2_results, annotator3_results]):
                path = Path(tmpdir) / f"ann{i+1}.json"
                path.write_text(json.dumps(results))
                files.append(str(path))

            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(
                result_files=files,
                output_path=str(output_path),
                strategy="average",
            )

            assert result.success

            merged = json.loads(output_path.read_text())
            responses = {r["task_id"]: r for r in merged["responses"]}

            # TASK_002: (2 + 1 + 2) / 3 = 1.67
            assert abs(responses["TASK_002"]["score"] - 5/3) < 0.01

    def test_merge_strict(self, annotator1_results, annotator2_results, annotator3_results):
        """Test strict merge (only if all agree)."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i, results in enumerate([annotator1_results, annotator2_results, annotator3_results]):
                path = Path(tmpdir) / f"ann{i+1}.json"
                path.write_text(json.dumps(results))
                files.append(str(path))

            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(
                result_files=files,
                output_path=str(output_path),
                strategy="strict",
            )

            assert result.success

            merged = json.loads(output_path.read_text())
            responses = {r["task_id"]: r for r in merged["responses"]}

            # TASK_001: all agree on 3
            assert responses["TASK_001"]["score"] == 3

            # TASK_002: disagreement -> None
            assert responses["TASK_002"]["score"] is None

    def test_agreement_rate(self, annotator1_results, annotator2_results, annotator3_results):
        """Test agreement rate calculation."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i, results in enumerate([annotator1_results, annotator2_results, annotator3_results]):
                path = Path(tmpdir) / f"ann{i+1}.json"
                path.write_text(json.dumps(results))
                files.append(str(path))

            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(
                result_files=files,
                output_path=str(output_path),
            )

            # Only TASK_001 has full agreement (3, 3, 3)
            # TASK_002: 2, 1, 2 - no full agreement
            # TASK_003: 3, 3, 2 - no full agreement
            assert result.agreement_rate == 1/3

    def test_calculate_iaa(self, annotator1_results, annotator2_results):
        """Test IAA calculation."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i, results in enumerate([annotator1_results, annotator2_results]):
                path = Path(tmpdir) / f"ann{i+1}.json"
                path.write_text(json.dumps(results))
                files.append(str(path))

            metrics = merger.calculate_iaa(files)

            assert metrics["annotator_count"] == 2
            assert metrics["common_tasks"] == 3
            # TASK_001: 3, 3 - agree
            # TASK_002: 2, 1 - disagree
            # TASK_003: 3, 3 - agree
            assert metrics["exact_agreement_rate"] == 2/3

    def test_calculate_iaa_insufficient_annotators(self, annotator1_results):
        """Test IAA with only one annotator."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "ann1.json"
            path.write_text(json.dumps(annotator1_results))

            metrics = merger.calculate_iaa([str(path)])

            assert "error" in metrics
