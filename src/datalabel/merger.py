"""Merge annotation results from multiple annotators."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict


@dataclass
class MergeResult:
    """Result of merging annotation results."""

    success: bool = True
    error: str = ""
    output_path: str = ""
    total_tasks: int = 0
    annotator_count: int = 0
    agreement_rate: float = 0.0
    conflicts: List[Dict[str, Any]] = field(default_factory=list)


class ResultMerger:
    """Merge annotation results from multiple annotators.

    Supports:
    - Majority voting for scores
    - Conflict detection
    - Inter-annotator agreement calculation
    """

    def merge(
        self,
        result_files: List[str],
        output_path: str,
        strategy: str = "majority",
    ) -> MergeResult:
        """Merge multiple annotation result files.

        Args:
            result_files: List of paths to annotation result JSON files
            output_path: Output path for merged results
            strategy: Merge strategy ('majority', 'average', 'strict')

        Returns:
            MergeResult with merge status and statistics
        """
        result = MergeResult()

        try:
            # Load all results
            all_results = []
            for file_path in result_files:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_results.append(
                        {
                            "file": file_path,
                            "metadata": data.get("metadata", {}),
                            "responses": {r["task_id"]: r for r in data.get("responses", [])},
                        }
                    )

            result.annotator_count = len(all_results)

            # Collect all task IDs
            all_task_ids = set()
            for ar in all_results:
                all_task_ids.update(ar["responses"].keys())

            result.total_tasks = len(all_task_ids)

            # Merge by task
            merged_responses = []
            conflicts = []
            agreements = 0
            total_compared = 0

            for task_id in sorted(all_task_ids):
                task_responses = []
                for ar in all_results:
                    if task_id in ar["responses"]:
                        task_responses.append(ar["responses"][task_id])

                if len(task_responses) == 0:
                    continue

                # Calculate agreement
                if len(task_responses) > 1:
                    values = self._extract_annotation_values(task_responses)
                    total_compared += 1
                    if self._values_agree(values):
                        agreements += 1
                    else:
                        conflicts.append(
                            {
                                "task_id": task_id,
                                "values": values,
                                "annotators": [
                                    ar["file"] for ar in all_results if task_id in ar["responses"]
                                ],
                            }
                        )

                # Merge based on strategy
                merged = self._merge_responses(task_responses, strategy)
                merged["task_id"] = task_id
                merged["annotation_count"] = len(task_responses)
                merged_responses.append(merged)

            # Calculate agreement rate
            if total_compared > 0:
                result.agreement_rate = agreements / total_compared

            result.conflicts = conflicts

            # Build output
            output_data = {
                "metadata": {
                    "merged_at": datetime.now().isoformat(),
                    "strategy": strategy,
                    "annotator_count": result.annotator_count,
                    "total_tasks": result.total_tasks,
                    "agreement_rate": result.agreement_rate,
                    "conflict_count": len(conflicts),
                    "source_files": result_files,
                    "tool": "DataLabel",
                    "version": "0.1.0",
                },
                "responses": merged_responses,
                "conflicts": conflicts,
            }

            # Write output
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            result.output_path = str(output_path)

        except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
            result.success = False
            result.error = str(e)

        return result

    def _merge_responses(
        self,
        responses: List[Dict[str, Any]],
        strategy: str,
    ) -> Dict[str, Any]:
        """Merge multiple responses for a single task.

        Auto-detects annotation type from response keys:
        - score: numeric scoring
        - choice: single choice
        - choices: multi choice
        - text: free text
        - ranking: ordered ranking
        """
        if len(responses) == 1:
            return responses[0].copy()

        comments = [r.get("comment", "") for r in responses if r.get("comment")]
        base = {
            "comment": " | ".join(comments) if comments else "",
            "merged_at": datetime.now().isoformat(),
        }

        # Detect annotation type from response keys
        first = responses[0]
        if "score" in first:
            base.update(self._merge_score_responses(responses, strategy))
        elif "choice" in first:
            base.update(self._merge_choice_responses(responses, strategy))
        elif "choices" in first:
            base.update(self._merge_multi_choice_responses(responses, strategy))
        elif "text" in first:
            base.update(self._merge_text_responses(responses, strategy))
        elif "ranking" in first:
            base.update(self._merge_ranking_responses(responses, strategy))
        else:
            # Fallback: try score
            base.update(self._merge_score_responses(responses, strategy))

        return base

    def _merge_score_responses(
        self, responses: List[Dict[str, Any]], strategy: str
    ) -> Dict[str, Any]:
        """Merge numeric score responses."""
        scores = [r["score"] for r in responses]

        if strategy == "majority":
            score_counts = defaultdict(int)
            for s in scores:
                score_counts[s] += 1
            merged_score = max(score_counts.keys(), key=lambda x: score_counts[x])
        elif strategy == "average":
            merged_score = sum(scores) / len(scores)
        elif strategy == "strict":
            merged_score = scores[0] if len(set(scores)) == 1 else None
        else:
            merged_score = scores[0]

        return {"score": merged_score, "individual_scores": scores}

    def _merge_choice_responses(
        self, responses: List[Dict[str, Any]], strategy: str
    ) -> Dict[str, Any]:
        """Merge single choice responses."""
        choices = [r["choice"] for r in responses]

        if strategy == "majority":
            counts = defaultdict(int)
            for c in choices:
                counts[c] += 1
            merged = max(counts.keys(), key=lambda x: counts[x])
        elif strategy == "strict":
            merged = choices[0] if len(set(choices)) == 1 else None
        else:
            merged = choices[0]

        return {"choice": merged, "individual_choices": choices}

    def _merge_multi_choice_responses(
        self, responses: List[Dict[str, Any]], strategy: str
    ) -> Dict[str, Any]:
        """Merge multi-choice responses."""
        all_choices = [set(r["choices"]) for r in responses]

        if strategy == "strict":
            # Intersection: only items all agree on
            merged = set.intersection(*all_choices) if all_choices else set()
        elif strategy == "majority":
            # Items selected by majority of annotators
            item_counts = defaultdict(int)
            for choices in all_choices:
                for item in choices:
                    item_counts[item] += 1
            threshold = len(responses) / 2
            merged = {item for item, count in item_counts.items() if count > threshold}
        else:
            merged = all_choices[0] if all_choices else set()

        return {
            "choices": sorted(merged),
            "individual_choices": [sorted(c) for c in all_choices],
        }

    def _merge_text_responses(
        self, responses: List[Dict[str, Any]], strategy: str
    ) -> Dict[str, Any]:
        """Merge text responses (collect all, no automatic merge)."""
        texts = [r["text"] for r in responses]
        return {"text": texts[0], "individual_texts": texts}

    def _merge_ranking_responses(
        self, responses: List[Dict[str, Any]], strategy: str
    ) -> Dict[str, Any]:
        """Merge ranking responses using Borda count."""
        rankings = [r["ranking"] for r in responses]

        if strategy == "strict":
            if all(r == rankings[0] for r in rankings):
                return {"ranking": rankings[0], "individual_rankings": rankings}
            return {"ranking": None, "individual_rankings": rankings}

        # Borda count: lower rank = more points
        scores = defaultdict(int)
        for ranking in rankings:
            n = len(ranking)
            for pos, item in enumerate(ranking):
                scores[item] += n - pos

        merged = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return {"ranking": merged, "individual_rankings": rankings}

    def calculate_iaa(
        self,
        result_files: List[str],
    ) -> Dict[str, Any]:
        """Calculate Inter-Annotator Agreement (IAA) metrics.

        Args:
            result_files: List of paths to annotation result JSON files

        Returns:
            Dictionary with IAA metrics
        """
        # Load all results
        all_results = []
        for file_path in result_files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_results.append(
                    {
                        "file": file_path,
                        "responses": {r["task_id"]: r for r in data.get("responses", [])},
                    }
                )

        if len(all_results) < 2:
            return {"error": "Need at least 2 annotators to calculate IAA"}

        # Find common tasks
        common_tasks = set(all_results[0]["responses"].keys())
        for ar in all_results[1:]:
            common_tasks &= set(ar["responses"].keys())

        if not common_tasks:
            return {"error": "No common tasks found between annotators"}

        # Calculate agreement metrics
        exact_agreements = 0
        total = len(common_tasks)

        for task_id in common_tasks:
            responses = [ar["responses"][task_id] for ar in all_results]
            values = self._extract_annotation_values(responses)
            if self._values_agree(values):
                exact_agreements += 1

        # Simple agreement rate
        agreement_rate = exact_agreements / total if total > 0 else 0

        # Pairwise agreement matrix
        n_annotators = len(all_results)
        pairwise_agreement = []
        for i in range(n_annotators):
            row = []
            for j in range(n_annotators):
                if i == j:
                    row.append(1.0)
                else:
                    pair_agreements = 0
                    for task_id in common_tasks:
                        ri = all_results[i]["responses"][task_id]
                        rj = all_results[j]["responses"][task_id]
                        vi = self._extract_annotation_values([ri])
                        vj = self._extract_annotation_values([rj])
                        if vi == vj:
                            pair_agreements += 1
                    row.append(pair_agreements / total if total > 0 else 0)
            pairwise_agreement.append(row)

        # Collect per-annotator values for advanced metrics
        all_values = []  # [task_values_list] where each is [val_ann1, val_ann2, ...]
        for task_id in sorted(common_tasks):
            task_vals = []
            for ar in all_results:
                vals = self._extract_annotation_values([ar["responses"][task_id]])
                task_vals.append(vals[0])
            all_values.append(task_vals)

        # Compute advanced metrics
        metrics = {
            "annotator_count": n_annotators,
            "common_tasks": len(common_tasks),
            "exact_agreement_rate": agreement_rate,
            "pairwise_agreement": pairwise_agreement,
            "files": [ar["file"] for ar in all_results],
        }

        # Pairwise Cohen's Kappa
        pairwise_kappa = []
        for i in range(n_annotators):
            row = []
            for j in range(n_annotators):
                if i == j:
                    row.append(1.0)
                else:
                    r1 = [v[i] for v in all_values]
                    r2 = [v[j] for v in all_values]
                    row.append(self._cohens_kappa(r1, r2))
            pairwise_kappa.append(row)
        metrics["cohens_kappa"] = pairwise_kappa

        # Fleiss' Kappa
        metrics["fleiss_kappa"] = self._fleiss_kappa(all_values)

        # Krippendorff's Alpha
        metrics["krippendorff_alpha"] = self._krippendorff_alpha(all_values)

        return metrics

    @staticmethod
    def _cohens_kappa(ratings1: list, ratings2: list) -> float:
        """Calculate Cohen's Kappa for two raters.

        kappa = (p_o - p_e) / (1 - p_e)
        """
        n = len(ratings1)
        if n == 0:
            return 0.0

        categories = sorted(set(str(v) for v in ratings1) | set(str(v) for v in ratings2))
        r1_str = [str(v) for v in ratings1]
        r2_str = [str(v) for v in ratings2]

        # Observed agreement
        p_o = sum(1 for a, b in zip(r1_str, r2_str) if a == b) / n

        # Expected agreement by chance
        p_e = 0.0
        for cat in categories:
            p1 = sum(1 for v in r1_str if v == cat) / n
            p2 = sum(1 for v in r2_str if v == cat) / n
            p_e += p1 * p2

        if p_e >= 1.0:
            return 1.0
        return (p_o - p_e) / (1 - p_e)

    @staticmethod
    def _fleiss_kappa(all_values: list) -> float:
        """Calculate Fleiss' Kappa for N raters.

        all_values: list of [val_ann1, val_ann2, ...] per subject
        """
        if not all_values:
            return 0.0

        n_raters = len(all_values[0])
        n_subjects = len(all_values)

        if n_raters < 2 or n_subjects == 0:
            return 0.0

        # Collect all categories
        categories = sorted(set(str(v) for row in all_values for v in row))
        k = len(categories)
        cat_index = {c: i for i, c in enumerate(categories)}

        # Build ratings matrix: n_subjects x k (count of raters per category)
        matrix = []
        for row in all_values:
            counts = [0] * k
            for v in row:
                counts[cat_index[str(v)]] += 1
            matrix.append(counts)

        # P_i for each subject
        p_values = []
        for counts in matrix:
            p_i = (sum(c * c for c in counts) - n_raters) / (n_raters * (n_raters - 1))
            p_values.append(p_i)

        p_bar = sum(p_values) / n_subjects

        # p_j for each category
        p_j = []
        for j in range(k):
            total_j = sum(matrix[i][j] for i in range(n_subjects))
            p_j.append(total_j / (n_subjects * n_raters))

        p_e_bar = sum(pj * pj for pj in p_j)

        if p_e_bar >= 1.0:
            return 1.0
        return (p_bar - p_e_bar) / (1 - p_e_bar)

    @staticmethod
    def _krippendorff_alpha(all_values: list) -> float:
        """Calculate Krippendorff's Alpha (nominal metric).

        all_values: list of [val_ann1, val_ann2, ...] per subject
        """
        if not all_values:
            return 0.0

        n_raters = len(all_values[0])
        n_subjects = len(all_values)

        if n_raters < 2 or n_subjects == 0:
            return 0.0

        # Convert to string for consistent comparison
        str_values = [[str(v) for v in row] for row in all_values]

        # Calculate observed disagreement (D_o)
        d_o = 0.0
        total_pairs = 0
        for row in str_values:
            n_u = len(row)
            for i in range(n_u):
                for j in range(i + 1, n_u):
                    total_pairs += 1
                    if row[i] != row[j]:
                        d_o += 1

        if total_pairs == 0:
            return 1.0
        d_o /= total_pairs

        # Calculate expected disagreement (D_e)
        # Count overall category frequencies
        all_flat = [v for row in str_values for v in row]
        n_total = len(all_flat)
        cat_counts = defaultdict(int)
        for v in all_flat:
            cat_counts[v] += 1

        d_e = 0.0
        categories = list(cat_counts.keys())
        for i in range(len(categories)):
            for j in range(i + 1, len(categories)):
                n_c = cat_counts[categories[i]]
                n_k = cat_counts[categories[j]]
                d_e += n_c * n_k

        d_e = d_e * 2 / (n_total * (n_total - 1)) if n_total > 1 else 0.0

        if d_e == 0.0:
            return 1.0
        return 1.0 - d_o / d_e

    @staticmethod
    def _extract_annotation_values(responses: List[Dict[str, Any]]) -> list:
        """Extract the annotation value from each response for comparison."""
        values = []
        for r in responses:
            if "score" in r:
                values.append(r["score"])
            elif "choice" in r:
                values.append(r["choice"])
            elif "choices" in r:
                values.append(tuple(sorted(r["choices"])))
            elif "text" in r:
                values.append(r["text"])
            elif "ranking" in r:
                values.append(tuple(r["ranking"]))
            else:
                values.append(r.get("score"))
        return values

    @staticmethod
    def _values_agree(values: list) -> bool:
        """Check if all annotation values are identical."""
        return len(set(str(v) for v in values)) == 1 if values else False
