"""Generate standalone HTML annotation interfaces."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, PackageLoader, select_autoescape

from datalabel.validator import SchemaValidator

try:
    import markdown

    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False


@dataclass
class GeneratorResult:
    """Result of annotation interface generation."""

    success: bool = True
    error: str = ""
    output_path: str = ""
    task_count: int = 0


THEMES: Dict[str, Dict[str, str]] = {
    "default": {},
    "knowlyr": {
        "primary": "#0d6b5e",
        "primary_light": "#0f8c7a",
        "primary_dark_mode": "#10b981",
        "primary_light_dark_mode": "#34d399",
        "font_family": '-apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
        "card_border": "1px solid var(--border)",
        "card_shadow": "none",
        "card_radius": "8px",
        "btn_radius": "100px",
        "header_bg": "rgba(255,255,255,0.88)",
        "header_backdrop": "blur(12px)",
        "brand_name": "蚁聚社区",
        "brand_color": "#0d6b5e",
    },
}


class AnnotatorGenerator:
    """Generate standalone HTML annotation interfaces.

    Produces a single HTML file that can be opened directly in a browser,
    with all data, styles, and logic embedded.
    """

    def __init__(self):
        self.env = Environment(
            loader=PackageLoader("datalabel", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def generate(
        self,
        schema: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        output_path: str,
        guidelines: Optional[str] = None,
        title: Optional[str] = None,
        page_size: int = 50,
        theme: str = "default",
    ) -> GeneratorResult:
        """Generate an HTML annotation interface.

        Args:
            schema: Data schema defining fields and scoring rubric
            tasks: List of tasks to annotate
            output_path: Output path for the HTML file
            guidelines: Optional markdown guidelines for annotators
            title: Optional title for the interface

        Returns:
            GeneratorResult with generation status
        """
        result = GeneratorResult()

        try:
            # Validate inputs
            validator = SchemaValidator()
            schema_validation = validator.validate_schema(schema)
            if not schema_validation.valid:
                result.success = False
                result.error = "Schema 验证失败:\n" + "\n".join(schema_validation.errors)
                return result

            task_validation = validator.validate_tasks(tasks, schema)
            if not task_validation.valid:
                result.success = False
                result.error = "任务数据验证失败:\n" + "\n".join(task_validation.errors)
                return result

            # Prepare template data
            template_data = self._prepare_template_data(
                schema=schema,
                tasks=tasks,
                guidelines=guidelines,
                title=title,
                page_size=page_size,
                theme=theme,
            )

            # Render template
            template = self.env.get_template("annotator.html")
            html_content = template.render(**template_data)

            # Write output
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html_content, encoding="utf-8")

            result.output_path = str(output_path)
            result.task_count = len(tasks)

        except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
            result.success = False
            result.error = str(e)

        return result

    def generate_from_datarecipe(
        self,
        analysis_dir: str,
        output_path: Optional[str] = None,
        theme: str = "default",
    ) -> GeneratorResult:
        """Generate from DataRecipe analysis output.

        Args:
            analysis_dir: Path to DataRecipe analysis output directory
            output_path: Output path (defaults to analysis_dir/10_标注工具/annotator.html)

        Returns:
            GeneratorResult with generation status
        """
        analysis_dir = Path(analysis_dir)

        # Load schema
        schema_path = analysis_dir / "04_复刻指南" / "DATA_SCHEMA.json"
        if not schema_path.exists():
            schema_path = analysis_dir / "DATA_SCHEMA.json"

        if not schema_path.exists():
            return GeneratorResult(success=False, error=f"Schema not found: {schema_path}")

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return GeneratorResult(success=False, error=f"Schema 读取失败: {e}")

        # Load samples/tasks
        samples_path = analysis_dir / "09_样例数据" / "samples.json"
        if not samples_path.exists():
            samples_path = analysis_dir / "samples.json"

        tasks = []
        if samples_path.exists():
            try:
                with open(samples_path, "r", encoding="utf-8") as f:
                    samples_data = json.load(f)
                    tasks = samples_data.get("samples", [])
            except (json.JSONDecodeError, OSError) as e:
                return GeneratorResult(success=False, error=f"任务数据读取失败: {e}")

        # Load guidelines
        guidelines = None
        guidelines_path = analysis_dir / "03_标注规范" / "ANNOTATION_SPEC.md"
        if guidelines_path.exists():
            guidelines = guidelines_path.read_text(encoding="utf-8")

        # Get title from schema or directory name
        title = schema.get("project_name", analysis_dir.name)

        # Set output path
        if output_path is None:
            output_dir = analysis_dir / "10_标注工具"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "annotator.html"

        return self.generate(
            schema=schema,
            tasks=tasks,
            output_path=str(output_path),
            guidelines=guidelines,
            title=title,
            theme=theme,
        )

    def _prepare_template_data(
        self,
        schema: Dict[str, Any],
        tasks: List[Dict[str, Any]],
        guidelines: Optional[str],
        title: Optional[str],
        page_size: int = 50,
        theme: str = "default",
    ) -> Dict[str, Any]:
        """Prepare data for template rendering."""

        # Convert guidelines markdown to HTML
        guidelines_html = ""
        if guidelines:
            if HAS_MARKDOWN:
                guidelines_html = markdown.markdown(
                    guidelines, extensions=["tables", "fenced_code"]
                )
            else:
                guidelines_html = f"<pre>{guidelines}</pre>"

        # Extract fields for display
        fields = schema.get("fields", [])
        display_fields = [f for f in fields if f.get("name") not in ["id", "metadata"]]

        # Extract scoring rubric
        scoring_rubric = schema.get("scoring_rubric", [])

        # Extract annotation config
        annotation_config = schema.get("annotation_config", {})
        if annotation_config:
            annotation_type = annotation_config.get("type", "scoring")
        elif scoring_rubric:
            annotation_type = "scoring"
        else:
            annotation_type = "scoring"

        # Prepare task data (use the 'data' field if present)
        prepared_tasks = []
        for i, task in enumerate(tasks):
            task_data = task.get("data", task)
            prepared_tasks.append(
                {
                    "id": task.get("id", f"TASK_{i + 1:03d}"),
                    "data": task_data,
                    "task_type": task.get("task_type", "default"),
                }
            )

        theme_vars = THEMES.get(theme, {})

        return {
            "title": title or schema.get("project_name", "DataLabel 标注"),
            "schema": schema,
            "fields": display_fields,
            "scoring_rubric": scoring_rubric,
            "annotation_type": annotation_type,
            "annotation_config": annotation_config,
            "annotation_config_json": json.dumps(annotation_config, ensure_ascii=False),
            "tasks": prepared_tasks,
            "tasks_json": json.dumps(prepared_tasks, ensure_ascii=False),
            "schema_json": json.dumps(schema, ensure_ascii=False),
            "guidelines_html": guidelines_html,
            "generated_at": datetime.now().isoformat(),
            "total_tasks": len(tasks),
            "page_size": page_size,
            "theme": theme,
            "theme_vars": theme_vars,
        }
