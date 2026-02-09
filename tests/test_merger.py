"""Tests for ResultMerger."""

import json
import tempfile
from pathlib import Path

from datalabel import ResultMerger


class TestResultMerger:
    """Tests for ResultMerger class."""

    def test_merge_majority(
        self, annotator1_results, annotator2_results, annotator3_results, annotator_results_factory
    ):
        """Test majority voting merge."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(
                tmpdir, [annotator1_results, annotator2_results, annotator3_results]
            )
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

    def test_merge_average(
        self, annotator1_results, annotator2_results, annotator3_results, annotator_results_factory
    ):
        """Test average merge."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(
                tmpdir, [annotator1_results, annotator2_results, annotator3_results]
            )
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
            assert abs(responses["TASK_002"]["score"] - 5 / 3) < 0.01

    def test_merge_strict(
        self, annotator1_results, annotator2_results, annotator3_results, annotator_results_factory
    ):
        """Test strict merge (only if all agree)."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(
                tmpdir, [annotator1_results, annotator2_results, annotator3_results]
            )
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

    def test_agreement_rate(
        self, annotator1_results, annotator2_results, annotator3_results, annotator_results_factory
    ):
        """Test agreement rate calculation."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(
                tmpdir, [annotator1_results, annotator2_results, annotator3_results]
            )
            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(
                result_files=files,
                output_path=str(output_path),
            )

            # Only TASK_001 has full agreement (3, 3, 3)
            # TASK_002: 2, 1, 2 - no full agreement
            # TASK_003: 3, 3, 2 - no full agreement
            assert result.agreement_rate == 1 / 3

    def test_calculate_iaa(self, annotator1_results, annotator2_results, annotator_results_factory):
        """Test IAA calculation."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [annotator1_results, annotator2_results])

            metrics = merger.calculate_iaa(files)

            assert metrics["annotator_count"] == 2
            assert metrics["common_tasks"] == 3
            # TASK_001: 3, 3 - agree
            # TASK_002: 2, 1 - disagree
            # TASK_003: 3, 3 - agree
            assert metrics["exact_agreement_rate"] == 2 / 3

    def test_calculate_iaa_insufficient_annotators(
        self, annotator1_results, annotator_results_factory
    ):
        """Test IAA with only one annotator."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [annotator1_results])

            metrics = merger.calculate_iaa(files)

            assert "error" in metrics

    def test_merge_no_common_tasks(self, annotator_results_factory):
        """Test merge when annotators labeled different tasks."""
        merger = ResultMerger()

        ann1 = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "TASK_A", "score": 3, "comment": ""},
            ],
        }
        ann2 = {
            "metadata": {"annotator": "ann2"},
            "responses": [
                {"task_id": "TASK_B", "score": 2, "comment": ""},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(
                result_files=files,
                output_path=str(output_path),
            )

            # Should still succeed - merge all unique tasks
            assert result.success

    def test_calculate_iaa_no_common_tasks(self, annotator_results_factory):
        """Test IAA when annotators have no common tasks."""
        merger = ResultMerger()

        ann1 = {
            "metadata": {"annotator": "ann1"},
            "responses": [{"task_id": "TASK_A", "score": 3, "comment": ""}],
        }
        ann2 = {
            "metadata": {"annotator": "ann2"},
            "responses": [{"task_id": "TASK_B", "score": 2, "comment": ""}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])

            metrics = merger.calculate_iaa(files)

            assert "error" in metrics

    def test_iaa_advanced_metrics(self, annotator1_results, annotator2_results, annotator_results_factory):
        """Test that IAA returns Cohen's Kappa, Fleiss' Kappa, and Krippendorff's Alpha."""
        merger = ResultMerger()

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [annotator1_results, annotator2_results])
            metrics = merger.calculate_iaa(files)

            assert "cohens_kappa" in metrics
            assert "fleiss_kappa" in metrics
            assert "krippendorff_alpha" in metrics

            # Cohen's Kappa should be a matrix
            assert len(metrics["cohens_kappa"]) == 2
            assert len(metrics["cohens_kappa"][0]) == 2
            assert metrics["cohens_kappa"][0][0] == 1.0  # self-agreement
            assert metrics["cohens_kappa"][1][1] == 1.0

            # Fleiss' Kappa should be a float
            assert isinstance(metrics["fleiss_kappa"], float)

            # Krippendorff's Alpha should be a float
            assert isinstance(metrics["krippendorff_alpha"], float)

    def test_iaa_perfect_agreement(self, annotator_results_factory):
        """Test IAA metrics with perfect agreement."""
        merger = ResultMerger()

        ann1 = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "T1", "score": 3, "comment": ""},
                {"task_id": "T2", "score": 2, "comment": ""},
            ],
        }
        ann2 = {
            "metadata": {"annotator": "ann2"},
            "responses": [
                {"task_id": "T1", "score": 3, "comment": ""},
                {"task_id": "T2", "score": 2, "comment": ""},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            metrics = merger.calculate_iaa(files)

            assert metrics["exact_agreement_rate"] == 1.0
            assert metrics["cohens_kappa"][0][1] == 1.0
            assert metrics["fleiss_kappa"] == 1.0
            assert metrics["krippendorff_alpha"] == 1.0

    def test_merge_choice_majority(self, annotator_results_factory):
        """Test majority merge for single_choice annotations."""
        merger = ResultMerger()

        ann1 = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "T1", "choice": "pos", "comment": ""},
                {"task_id": "T2", "choice": "neg", "comment": ""},
            ],
        }
        ann2 = {
            "metadata": {"annotator": "ann2"},
            "responses": [
                {"task_id": "T1", "choice": "pos", "comment": ""},
                {"task_id": "T2", "choice": "pos", "comment": ""},
            ],
        }
        ann3 = {
            "metadata": {"annotator": "ann3"},
            "responses": [
                {"task_id": "T1", "choice": "neg", "comment": ""},
                {"task_id": "T2", "choice": "pos", "comment": ""},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2, ann3])
            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(result_files=files, output_path=str(output_path), strategy="majority")
            assert result.success

            merged = json.loads(output_path.read_text())
            responses = {r["task_id"]: r for r in merged["responses"]}

            assert responses["T1"]["choice"] == "pos"  # 2 pos vs 1 neg
            assert responses["T2"]["choice"] == "pos"  # 2 pos vs 1 neg

    def test_merge_multi_choice(self, annotator_results_factory):
        """Test majority merge for multi_choice annotations."""
        merger = ResultMerger()

        ann1 = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "T1", "choices": ["a", "b"], "comment": ""},
            ],
        }
        ann2 = {
            "metadata": {"annotator": "ann2"},
            "responses": [
                {"task_id": "T1", "choices": ["a", "c"], "comment": ""},
            ],
        }
        ann3 = {
            "metadata": {"annotator": "ann3"},
            "responses": [
                {"task_id": "T1", "choices": ["a", "b"], "comment": ""},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2, ann3])
            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(result_files=files, output_path=str(output_path), strategy="majority")
            assert result.success

            merged = json.loads(output_path.read_text())
            r = merged["responses"][0]
            # "a" selected by 3/3, "b" by 2/3, "c" by 1/3
            assert "a" in r["choices"]
            assert "b" in r["choices"]
            assert "c" not in r["choices"]

    def test_merge_ranking_borda(self, annotator_results_factory):
        """Test ranking merge using Borda count."""
        merger = ResultMerger()

        ann1 = {
            "metadata": {"annotator": "ann1"},
            "responses": [
                {"task_id": "T1", "ranking": ["a", "b", "c"], "comment": ""},
            ],
        }
        ann2 = {
            "metadata": {"annotator": "ann2"},
            "responses": [
                {"task_id": "T1", "ranking": ["a", "c", "b"], "comment": ""},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(result_files=files, output_path=str(output_path))
            assert result.success

            merged = json.loads(output_path.read_text())
            r = merged["responses"][0]
            # Borda: a=3+3=6, b=2+1=3, c=1+2=3
            assert r["ranking"][0] == "a"

    def test_merge_text_responses(self, annotator_results_factory):
        """Test text annotation merge collects all texts."""
        merger = ResultMerger()

        ann1 = {
            "metadata": {"annotator": "ann1"},
            "responses": [{"task_id": "T1", "text": "翻译A", "comment": ""}],
        }
        ann2 = {
            "metadata": {"annotator": "ann2"},
            "responses": [{"task_id": "T1", "text": "翻译B", "comment": ""}],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"

            result = merger.merge(result_files=files, output_path=str(output_path))
            assert result.success

            merged = json.loads(output_path.read_text())
            r = merged["responses"][0]
            assert "individual_texts" in r
            assert len(r["individual_texts"]) == 2


class TestIAAEdgeCases:
    """Tests for IAA metric edge cases."""

    def test_cohens_kappa_empty(self):
        """Empty ratings list returns 0.0."""
        assert ResultMerger._cohens_kappa([], []) == 0.0

    def test_cohens_kappa_single_category(self):
        """All same category -> p_e >= 1.0, returns 1.0."""
        assert ResultMerger._cohens_kappa(["a", "a", "a"], ["a", "a", "a"]) == 1.0

    def test_fleiss_kappa_empty(self):
        """Empty values list returns 0.0."""
        assert ResultMerger._fleiss_kappa([]) == 0.0

    def test_fleiss_kappa_single_rater(self):
        """Single rater (n_raters < 2) returns 0.0."""
        assert ResultMerger._fleiss_kappa([["a"], ["b"], ["a"]]) == 0.0

    def test_fleiss_kappa_perfect_expected(self):
        """All same category across all raters -> p_e_bar >= 1.0, returns 1.0."""
        assert ResultMerger._fleiss_kappa([["a", "a"], ["a", "a"], ["a", "a"]]) == 1.0

    def test_krippendorff_alpha_empty(self):
        """Empty values list returns 0.0."""
        assert ResultMerger._krippendorff_alpha([]) == 0.0

    def test_krippendorff_alpha_single_rater(self):
        """Single rater (n_raters < 2) returns 0.0."""
        assert ResultMerger._krippendorff_alpha([["a"], ["b"]]) == 0.0

    def test_krippendorff_alpha_uniform(self):
        """All same category -> d_e == 0.0, returns 1.0."""
        assert ResultMerger._krippendorff_alpha([["a", "a"], ["a", "a"]]) == 1.0


class TestMergerStrategyEdgeCases:
    """Test merger strategy edge cases and fallback paths."""

    def test_merge_choice_strict_agree(self, annotator_results_factory):
        """Single choice strict, all agree → lines 221-222."""
        merger = ResultMerger()
        ann1 = {"metadata": {}, "responses": [{"task_id": "T1", "choice": "pos", "comment": ""}]}
        ann2 = {"metadata": {}, "responses": [{"task_id": "T1", "choice": "pos", "comment": ""}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"
            result = merger.merge(result_files=files, output_path=str(output_path), strategy="strict")
            assert result.success
            merged = json.loads(output_path.read_text())
            assert merged["responses"][0]["choice"] == "pos"

    def test_merge_choice_strict_disagree(self, annotator_results_factory):
        """Single choice strict, disagree → None."""
        merger = ResultMerger()
        ann1 = {"metadata": {}, "responses": [{"task_id": "T1", "choice": "pos", "comment": ""}]}
        ann2 = {"metadata": {}, "responses": [{"task_id": "T1", "choice": "neg", "comment": ""}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"
            result = merger.merge(result_files=files, output_path=str(output_path), strategy="strict")
            assert result.success
            merged = json.loads(output_path.read_text())
            assert merged["responses"][0]["choice"] is None

    def test_merge_multi_choice_strict(self, annotator_results_factory):
        """Multi-choice strict → intersection → line 236."""
        merger = ResultMerger()
        ann1 = {"metadata": {}, "responses": [{"task_id": "T1", "choices": ["a", "b"], "comment": ""}]}
        ann2 = {"metadata": {}, "responses": [{"task_id": "T1", "choices": ["a", "c"], "comment": ""}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"
            result = merger.merge(result_files=files, output_path=str(output_path), strategy="strict")
            assert result.success
            merged = json.loads(output_path.read_text())
            assert merged["responses"][0]["choices"] == ["a"]  # intersection

    def test_merge_ranking_strict_agree(self, annotator_results_factory):
        """Ranking strict, all agree → lines 267-268."""
        merger = ResultMerger()
        ann1 = {"metadata": {}, "responses": [{"task_id": "T1", "ranking": ["a", "b"], "comment": ""}]}
        ann2 = {"metadata": {}, "responses": [{"task_id": "T1", "ranking": ["a", "b"], "comment": ""}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"
            result = merger.merge(result_files=files, output_path=str(output_path), strategy="strict")
            assert result.success
            merged = json.loads(output_path.read_text())
            assert merged["responses"][0]["ranking"] == ["a", "b"]

    def test_merge_ranking_strict_disagree(self, annotator_results_factory):
        """Ranking strict, disagree → None → line 269."""
        merger = ResultMerger()
        ann1 = {"metadata": {}, "responses": [{"task_id": "T1", "ranking": ["a", "b"], "comment": ""}]}
        ann2 = {"metadata": {}, "responses": [{"task_id": "T1", "ranking": ["b", "a"], "comment": ""}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"
            result = merger.merge(result_files=files, output_path=str(output_path), strategy="strict")
            assert result.success
            merged = json.loads(output_path.read_text())
            assert merged["responses"][0]["ranking"] is None

    def test_merge_unknown_type_fallback(self, annotator_results_factory):
        """Responses without known keys → fallback to score merge → line 186.

        Fallback hits _merge_score_responses which KeyErrors → caught by exception handler.
        """
        merger = ResultMerger()
        ann1 = {"metadata": {}, "responses": [{"task_id": "T1", "custom_field": "x", "comment": ""}]}
        ann2 = {"metadata": {}, "responses": [{"task_id": "T1", "custom_field": "y", "comment": ""}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"
            result = merger.merge(result_files=files, output_path=str(output_path))
            # Fallback path reaches line 186 then fails on KeyError → caught
            assert not result.success

    def test_merge_score_unknown_strategy(self, annotator_results_factory):
        """Score with unknown strategy → fallback → line 206."""
        merger = ResultMerger()
        ann1 = {"metadata": {}, "responses": [{"task_id": "T1", "score": 3, "comment": ""}]}
        ann2 = {"metadata": {}, "responses": [{"task_id": "T1", "score": 2, "comment": ""}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            files = annotator_results_factory(tmpdir, [ann1, ann2])
            output_path = Path(tmpdir) / "merged.json"
            # Use unknown strategy name - falls through to else branch
            result = merger.merge(result_files=files, output_path=str(output_path), strategy="unknown")
            assert result.success
            merged = json.loads(output_path.read_text())
            # Fallback: takes first score
            assert merged["responses"][0]["score"] == 3

    def test_extract_values_unknown_type(self):
        """Response with no known annotation key → fallback → line 536."""
        values = ResultMerger._extract_annotation_values(
            [{"custom": "x"}, {"custom": "y"}]
        )
        assert values == [None, None]

    def test_merge_exception_handling(self, annotator_results_factory):
        """Merge with corrupted file → exception → lines 143-145."""
        merger = ResultMerger()
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "a1.json"
            f2 = Path(tmpdir) / "a2.json"
            f1.write_text("{invalid json", encoding="utf-8")
            f2.write_text("{invalid json", encoding="utf-8")
            output_path = Path(tmpdir) / "merged.json"
            result = merger.merge(
                result_files=[str(f1), str(f2)],
                output_path=str(output_path),
            )
            assert not result.success
            assert result.error
