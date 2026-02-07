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
                    scores = [r["score"] for r in task_responses]
                    total_compared += 1
                    if len(set(scores)) == 1:
                        agreements += 1
                    else:
                        conflicts.append(
                            {
                                "task_id": task_id,
                                "scores": scores,
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

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _merge_responses(
        self,
        responses: List[Dict[str, Any]],
        strategy: str,
    ) -> Dict[str, Any]:
        """Merge multiple responses for a single task."""

        if len(responses) == 1:
            return responses[0].copy()

        scores = [r["score"] for r in responses]
        comments = [r.get("comment", "") for r in responses if r.get("comment")]

        if strategy == "majority":
            # Use most common score
            score_counts = defaultdict(int)
            for s in scores:
                score_counts[s] += 1
            merged_score = max(score_counts.keys(), key=lambda x: score_counts[x])

        elif strategy == "average":
            # Use average score
            merged_score = sum(scores) / len(scores)

        elif strategy == "strict":
            # Only use score if all agree
            if len(set(scores)) == 1:
                merged_score = scores[0]
            else:
                merged_score = None  # Needs review

        else:
            merged_score = scores[0]

        return {
            "score": merged_score,
            "individual_scores": scores,
            "comment": " | ".join(comments) if comments else "",
            "merged_at": datetime.now().isoformat(),
        }

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

        score_pairs = []  # For correlation calculation

        for task_id in common_tasks:
            scores = [ar["responses"][task_id]["score"] for ar in all_results]
            score_pairs.append(scores)

            if len(set(scores)) == 1:
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
                    agreements = sum(
                        1
                        for task_id in common_tasks
                        if all_results[i]["responses"][task_id]["score"]
                        == all_results[j]["responses"][task_id]["score"]
                    )
                    row.append(agreements / total if total > 0 else 0)
            pairwise_agreement.append(row)

        return {
            "annotator_count": n_annotators,
            "common_tasks": len(common_tasks),
            "exact_agreement_rate": agreement_rate,
            "pairwise_agreement": pairwise_agreement,
            "files": [ar["file"] for ar in all_results],
        }
