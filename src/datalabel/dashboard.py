"""Generate standalone HTML annotation dashboard."""

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, PackageLoader, select_autoescape

from datalabel.merger import ResultMerger


@dataclass
class DashboardResult:
    """Result of dashboard generation."""

    success: bool = True
    error: str = ""
    output_path: str = ""
    annotator_count: int = 0
    total_tasks: int = 0
    overall_completion: float = 0.0


class DashboardGenerator:
    """Generate standalone HTML annotation progress dashboard."""

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader("datalabel", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.env.filters["kappa_color"] = self._kappa_color_filter
        self._merger = ResultMerger()

    def generate(
        self,
        result_files: List[str],
        output_path: str,
        schema: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
    ) -> DashboardResult:
        """Generate an HTML dashboard from annotation result files."""
        result = DashboardResult()

        try:
            # Load all results
            all_results = self._load_results(result_files)
            if not all_results:
                result.success = False
                result.error = "没有可用的标注结果"
                return result

            result.annotator_count = len(all_results)

            # Collect all task IDs
            all_task_ids = set()
            for r in all_results:
                all_task_ids.update(r["responses"].keys())
            result.total_tasks = len(all_task_ids)

            # Compute IAA (requires 2+ annotators)
            iaa_metrics = {}
            if len(all_results) >= 2:
                iaa_metrics = self._merger.calculate_iaa(result_files)

            # Compute all dashboard data
            overview = self._compute_overview(all_results, all_task_ids, iaa_metrics)
            result.overall_completion = overview["overall_completion"]

            per_annotator = self._compute_per_annotator(all_results, all_task_ids)
            distribution = self._compute_distribution(all_results)
            conflicts = self._compute_conflicts(all_results, all_task_ids)
            time_analysis = self._compute_time_analysis(all_results)

            # Heatmap data
            heatmap = self._compute_heatmap(all_results, iaa_metrics)

            # Prepare SVG chart data
            dist_bars = self._prepare_distribution_bars(distribution)

            # Render template
            template_data = {
                "title": title or "标注进度仪表盘",
                "generated_at": datetime.now().isoformat(),
                "overview": overview,
                "per_annotator": per_annotator,
                "distribution": distribution,
                "dist_bars": dist_bars,
                "heatmap": heatmap,
                "conflicts": conflicts,
                "time_analysis": time_analysis,
                "schema": schema,
            }

            template = self.env.get_template("dashboard.html")
            html_content = template.render(**template_data)

            # Write output
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content, encoding="utf-8")
            result.output_path = str(output_path)

        except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
            result.success = False
            result.error = str(e)

        return result

    def _load_results(self, result_files: List[str]) -> List[Dict[str, Any]]:
        """Load annotation result files."""
        all_results = []
        for file_path in result_files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            annotator = metadata.get("annotator", Path(file_path).stem)
            total_tasks = metadata.get("total_tasks", 0)
            completed_tasks = metadata.get("completed_tasks", 0)

            responses = {}
            for r in data.get("responses", []):
                tid = r.get("task_id", "")
                if tid:
                    responses[tid] = r

            if not completed_tasks:
                completed_tasks = len(responses)

            all_results.append({
                "file": file_path,
                "annotator": annotator,
                "metadata": metadata,
                "responses": responses,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
            })
        return all_results

    def _compute_overview(
        self,
        all_results: List[Dict],
        all_task_ids: set,
        iaa_metrics: Dict,
    ) -> Dict[str, Any]:
        """Compute overview statistics."""
        total = len(all_task_ids)
        annotator_count = len(all_results)

        # Average completion
        if total > 0:
            completions = [len(r["responses"]) / total for r in all_results]
            overall_completion = sum(completions) / len(completions)
        else:
            overall_completion = 0.0

        agreement_rate = iaa_metrics.get("exact_agreement_rate", 0.0)

        return {
            "total_tasks": total,
            "annotator_count": annotator_count,
            "overall_completion": overall_completion,
            "agreement_rate": agreement_rate,
        }

    def _compute_per_annotator(
        self,
        all_results: List[Dict],
        all_task_ids: set,
    ) -> List[Dict[str, Any]]:
        """Compute per-annotator progress."""
        total = len(all_task_ids)
        annotators = []
        for r in all_results:
            completed = len(r["responses"])
            percentage = (completed / total * 100) if total > 0 else 0
            annotators.append({
                "name": r["annotator"],
                "completed": completed,
                "total": total,
                "percentage": round(percentage, 1),
            })
        return annotators

    def _compute_distribution(
        self,
        all_results: List[Dict],
    ) -> Dict[str, Any]:
        """Compute annotation value distribution."""
        # Detect annotation type from first response
        ann_type = "unknown"
        for r in all_results:
            for resp in r["responses"].values():
                if "score" in resp:
                    ann_type = "scoring"
                elif "choice" in resp:
                    ann_type = "single_choice"
                elif "choices" in resp:
                    ann_type = "multi_choice"
                elif "text" in resp:
                    ann_type = "text"
                elif "ranking" in resp:
                    ann_type = "ranking"
                break
            if ann_type != "unknown":
                break

        aggregate: Dict[str, int] = defaultdict(int)
        per_annotator: Dict[str, Dict[str, int]] = {}

        for r in all_results:
            ann_name = r["annotator"]
            per_annotator[ann_name] = defaultdict(int)
            for resp in r["responses"].values():
                if ann_type == "scoring":
                    val = str(resp.get("score", ""))
                    if val:
                        aggregate[val] += 1
                        per_annotator[ann_name][val] += 1
                elif ann_type == "single_choice":
                    val = str(resp.get("choice", ""))
                    if val:
                        aggregate[val] += 1
                        per_annotator[ann_name][val] += 1
                elif ann_type == "multi_choice":
                    for c in resp.get("choices", []):
                        aggregate[str(c)] += 1
                        per_annotator[ann_name][str(c)] += 1
                elif ann_type == "ranking":
                    # Count first-place items
                    ranking = resp.get("ranking", [])
                    if ranking:
                        val = str(ranking[0])
                        aggregate[val] += 1
                        per_annotator[ann_name][val] += 1

        labels = sorted(aggregate.keys())

        return {
            "type": ann_type,
            "aggregate": dict(aggregate),
            "per_annotator": {k: dict(v) for k, v in per_annotator.items()},
            "labels": labels,
        }

    def _compute_conflicts(
        self,
        all_results: List[Dict],
        all_task_ids: set,
    ) -> List[Dict[str, Any]]:
        """Find tasks where annotators disagree."""
        if len(all_results) < 2:
            return []

        conflicts = []
        for tid in sorted(all_task_ids):
            values = {}
            for r in all_results:
                if tid in r["responses"]:
                    resp = r["responses"][tid]
                    val = self._extract_value(resp)
                    values[r["annotator"]] = val

            if len(values) >= 2:
                unique_vals = set(str(v) for v in values.values())
                if len(unique_vals) > 1:
                    conflicts.append({"task_id": tid, "annotations": values})

        return conflicts

    def _compute_time_analysis(
        self,
        all_results: List[Dict],
    ) -> Dict[str, Any]:
        """Compute time-based statistics if timestamps available."""
        per_day: Dict[str, int] = defaultdict(int)
        per_annotator_daily: Dict[str, Dict[str, int]] = {}
        has_timestamps = False

        for r in all_results:
            ann_name = r["annotator"]
            per_annotator_daily[ann_name] = defaultdict(int)
            for resp in r["responses"].values():
                ts = resp.get("annotated_at", "")
                if ts:
                    has_timestamps = True
                    day = ts[:10]  # "2025-01-15"
                    per_day[day] += 1
                    per_annotator_daily[ann_name][day] += 1

        if not has_timestamps:
            return {"available": False}

        days = sorted(per_day.keys())
        max_count = max(per_day.values()) if per_day else 1

        # Prepare SVG bars for time chart
        bar_width = 30
        gap = 5
        chart_height = 150
        bars = []
        for i, day in enumerate(days):
            count = per_day[day]
            h = (count / max_count * (chart_height - 20)) if max_count > 0 else 0
            bars.append({
                "x": i * (bar_width + gap),
                "y": chart_height - h - 10,
                "width": bar_width,
                "height": h,
                "label": day[5:],  # "01-15"
                "count": count,
            })

        chart_width = len(days) * (bar_width + gap) + 10

        return {
            "available": True,
            "per_day": dict(per_day),
            "per_annotator_daily": {k: dict(v) for k, v in per_annotator_daily.items()},
            "bars": bars,
            "chart_width": max(chart_width, 200),
            "chart_height": chart_height,
        }

    def _compute_heatmap(
        self,
        all_results: List[Dict],
        iaa_metrics: Dict,
    ) -> Dict[str, Any]:
        """Prepare heatmap data from IAA metrics."""
        annotators = [r["annotator"] for r in all_results]

        if "error" in iaa_metrics or not iaa_metrics:
            return {
                "available": len(all_results) >= 2,
                "annotators": annotators,
                "matrix": [],
                "fleiss_kappa": None,
                "krippendorff_alpha": None,
            }

        # Use pairwise agreement if kappa not available
        kappa = iaa_metrics.get("cohens_kappa", [])
        agreement = iaa_metrics.get("pairwise_agreement", [])
        matrix = kappa if kappa else agreement

        return {
            "available": len(matrix) > 0,
            "annotators": annotators,
            "matrix": matrix,
            "fleiss_kappa": iaa_metrics.get("fleiss_kappa"),
            "krippendorff_alpha": iaa_metrics.get("krippendorff_alpha"),
        }

    def _prepare_distribution_bars(
        self,
        distribution: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Pre-compute SVG bar geometry for distribution chart."""
        labels = distribution["labels"]
        aggregate = distribution["aggregate"]
        if not labels or distribution["type"] == "text":
            return []

        max_count = max(aggregate.values()) if aggregate else 1
        bar_width = 40
        gap = 10
        chart_height = 160

        bars = []
        for i, label in enumerate(labels):
            count = aggregate.get(label, 0)
            h = (count / max_count * (chart_height - 30)) if max_count > 0 else 0
            bars.append({
                "x": i * (bar_width + gap) + 10,
                "y": chart_height - h - 20,
                "width": bar_width,
                "height": h,
                "label": label,
                "count": count,
            })

        return bars

    @staticmethod
    def _extract_value(resp: Dict[str, Any]) -> Any:
        """Extract annotation value from a response."""
        if "score" in resp:
            return resp["score"]
        if "choice" in resp:
            return resp["choice"]
        if "choices" in resp:
            return tuple(sorted(resp["choices"]))
        if "text" in resp:
            return resp["text"]
        if "ranking" in resp:
            return tuple(resp["ranking"])
        return None

    @staticmethod
    def _kappa_color_filter(value: Any) -> str:
        """Map kappa value to HSL color for heatmap cells."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return "hsl(0, 0%, 70%)"
        v = max(-1.0, min(1.0, v))
        # Map [-1, 1] → hue [0, 120] (red → green)
        hue = int(60 * (v + 1))
        return f"hsl({hue}, 70%, 42%)"
