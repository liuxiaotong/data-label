"""DataLabel CLI - 命令行界面."""

import csv
import io
import json
import sys
from pathlib import Path
from typing import Optional

import click

from datalabel import __version__
from datalabel.generator import AnnotatorGenerator
from datalabel.merger import ResultMerger


@click.group()
@click.version_option(version=__version__, prog_name="datalabel")
def main():
    """DataLabel - 轻量级数据标注工具

    生成独立的 HTML 标注界面，无需服务器，浏览器直接打开即可使用。
    """
    pass


@main.command()
@click.argument("analysis_dir", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="输出文件路径 (默认: analysis_dir/10_标注工具/annotator.html)",
)
def generate(analysis_dir: str, output: Optional[str]):
    """从 DataRecipe 分析结果生成标注界面

    ANALYSIS_DIR: DataRecipe 分析输出目录的路径
    """
    click.echo(f"正在从 {analysis_dir} 生成标注界面...")

    generator = AnnotatorGenerator()
    result = generator.generate_from_datarecipe(
        analysis_dir=analysis_dir,
        output_path=output,
    )

    if result.success:
        click.echo(f"✓ 生成成功: {result.output_path}")
        click.echo(f"  任务数量: {result.task_count}")
        click.echo("\n在浏览器中打开此文件即可开始标注")
    else:
        click.echo(f"✗ 生成失败: {result.error}", err=True)
        sys.exit(1)


@main.command()
@click.argument("schema_file", type=click.Path(exists=True))
@click.argument("tasks_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), required=True, help="输出 HTML 文件路径")
@click.option(
    "-g", "--guidelines", type=click.Path(exists=True), help="标注指南文件路径 (Markdown 格式)"
)
@click.option("-t", "--title", type=str, help="标注界面标题")
@click.option("--page-size", type=int, default=50, help="任务列表每页显示数 (默认: 50)")
def create(
    schema_file: str,
    tasks_file: str,
    output: str,
    guidelines: Optional[str],
    title: Optional[str],
    page_size: int,
):
    """从 Schema 和任务文件创建标注界面

    SCHEMA_FILE: 数据 Schema JSON 文件
    TASKS_FILE: 待标注任务 JSON 文件
    """
    # 加载 Schema
    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # 加载任务
    with open(tasks_file, "r", encoding="utf-8") as f:
        tasks_data = json.load(f)

    # 支持两种格式: 直接列表或 {"samples": [...]}
    if isinstance(tasks_data, list):
        tasks = tasks_data
    else:
        tasks = tasks_data.get("samples", tasks_data.get("tasks", []))

    # 加载指南
    guidelines_content = None
    if guidelines:
        guidelines_content = Path(guidelines).read_text(encoding="utf-8")

    click.echo("正在创建标注界面...")
    click.echo(f"  Schema: {schema_file}")
    click.echo(f"  任务数: {len(tasks)}")

    generator = AnnotatorGenerator()
    result = generator.generate(
        schema=schema,
        tasks=tasks,
        output_path=output,
        guidelines=guidelines_content,
        title=title,
        page_size=page_size,
    )

    if result.success:
        click.echo(f"✓ 创建成功: {result.output_path}")
        click.echo("\n在浏览器中打开此文件即可开始标注")
    else:
        click.echo(f"✗ 创建失败: {result.error}", err=True)
        sys.exit(1)


@main.command()
@click.argument("result_files", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("-o", "--output", type=click.Path(), required=True, help="合并结果输出路径")
@click.option(
    "-s",
    "--strategy",
    type=click.Choice(["majority", "average", "strict"]),
    default="majority",
    help="合并策略 (默认: majority)",
)
def merge(result_files: tuple, output: str, strategy: str):
    """合并多个标注员的标注结果

    RESULT_FILES: 标注结果 JSON 文件列表
    """
    if len(result_files) < 2:
        click.echo("错误: 至少需要 2 个标注结果文件", err=True)
        sys.exit(1)

    click.echo(f"正在合并 {len(result_files)} 个标注结果...")
    click.echo(f"  策略: {strategy}")

    merger = ResultMerger()
    result = merger.merge(
        result_files=list(result_files),
        output_path=output,
        strategy=strategy,
    )

    if result.success:
        click.echo(f"✓ 合并成功: {result.output_path}")
        click.echo(f"  任务总数: {result.total_tasks}")
        click.echo(f"  标注员数: {result.annotator_count}")
        click.echo(f"  一致率: {result.agreement_rate:.1%}")
        if result.conflicts:
            click.echo(f"  冲突数: {len(result.conflicts)}")
    else:
        click.echo(f"✗ 合并失败: {result.error}", err=True)
        sys.exit(1)


@main.command()
@click.argument("result_files", nargs=-1, type=click.Path(exists=True), required=True)
def iaa(result_files: tuple):
    """计算标注员间一致性 (Inter-Annotator Agreement)

    RESULT_FILES: 标注结果 JSON 文件列表
    """
    if len(result_files) < 2:
        click.echo("错误: 至少需要 2 个标注结果文件", err=True)
        sys.exit(1)

    click.echo(f"正在计算 {len(result_files)} 个标注结果的 IAA...")

    merger = ResultMerger()
    metrics = merger.calculate_iaa(list(result_files))

    if "error" in metrics:
        click.echo(f"✗ 计算失败: {metrics['error']}", err=True)
        sys.exit(1)

    click.echo("\n标注员间一致性 (IAA) 指标:")
    click.echo(f"  标注员数: {metrics['annotator_count']}")
    click.echo(f"  共同任务: {metrics['common_tasks']}")
    click.echo(f"  完全一致率: {metrics['exact_agreement_rate']:.1%}")

    if "fleiss_kappa" in metrics:
        click.echo(f"  Fleiss' Kappa: {metrics['fleiss_kappa']:.3f}")
    if "krippendorff_alpha" in metrics:
        click.echo(f"  Krippendorff's Alpha: {metrics['krippendorff_alpha']:.3f}")

    click.echo("\n两两一致矩阵 (Agreement / Cohen's Kappa):")
    files = [Path(f).name for f in metrics["files"]]
    kappa = metrics.get("cohens_kappa", [])

    # 打印表头
    header = "          " + "  ".join(f"{f[:8]:>8}" for f in files)
    click.echo(header)

    # 打印矩阵
    for i, row in enumerate(metrics["pairwise_agreement"]):
        parts = []
        for j, v in enumerate(row):
            if i == j:
                parts.append(f"{'---':>8}")
            else:
                k = kappa[i][j] if kappa else 0
                parts.append(f"{v:.0%}/κ{k:.2f}")
        row_str = f"{files[i][:8]:>8}  " + "  ".join(parts)
        click.echo(row_str)


@main.command()
@click.argument("schema_file", type=click.Path(exists=True))
@click.option("-t", "--tasks", "tasks_file", type=click.Path(exists=True), help="任务文件路径")
def validate(schema_file: str, tasks_file: Optional[str]):
    """验证 Schema 和任务数据格式

    SCHEMA_FILE: 数据 Schema JSON 文件
    """
    from datalabel.validator import SchemaValidator

    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    validator = SchemaValidator()
    result = validator.validate_schema(schema)

    if result.errors:
        click.echo("✗ Schema 验证失败:", err=True)
        for err in result.errors:
            click.echo(f"  - {err}", err=True)
    elif result.warnings:
        click.echo("⚠ Schema 验证通过 (有警告):")
        for warn in result.warnings:
            click.echo(f"  - {warn}")
    else:
        click.echo("✓ Schema 验证通过")

    if tasks_file:
        with open(tasks_file, "r", encoding="utf-8") as f:
            tasks_data = json.load(f)

        if isinstance(tasks_data, list):
            tasks = tasks_data
        else:
            tasks = tasks_data.get("samples", tasks_data.get("tasks", []))

        task_result = validator.validate_tasks(tasks, schema)
        if task_result.errors:
            click.echo("✗ 任务数据验证失败:", err=True)
            for err in task_result.errors:
                click.echo(f"  - {err}", err=True)
        elif task_result.warnings:
            click.echo(f"⚠ 任务数据验证通过 ({len(tasks)} 条, 有警告):")
            for warn in task_result.warnings:
                click.echo(f"  - {warn}")
        else:
            click.echo(f"✓ 任务数据验证通过 ({len(tasks)} 条)")

        if task_result.errors or result.errors:
            sys.exit(1)
    elif result.errors:
        sys.exit(1)


@main.command(name="export")
@click.argument("result_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), required=True, help="输出文件路径")
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["json", "jsonl", "csv"]),
    default="json",
    help="输出格式 (默认: json)",
)
def export_results(result_file: str, output: str, fmt: str):
    """转换标注结果文件格式

    RESULT_FILE: 标注结果 JSON 文件
    """
    with open(result_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract responses
    if isinstance(data, list):
        responses = data
    elif isinstance(data, dict) and "responses" in data:
        responses = data["responses"]
    else:
        click.echo("错误: 无法识别的结果文件格式", err=True)
        sys.exit(1)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(responses, f, ensure_ascii=False, indent=2)
    elif fmt == "jsonl":
        with open(output_path, "w", encoding="utf-8") as f:
            for r in responses:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    elif fmt == "csv":
        if not responses:
            output_path.write_text("", encoding="utf-8")
        else:
            keys = list(dict.fromkeys(k for r in responses for k in r.keys()))
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            for r in responses:
                row = {}
                for k in keys:
                    v = r.get(k)
                    row[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                writer.writerow(row)
            output_path.write_text(buf.getvalue(), encoding="utf-8")

    click.echo(f"✓ 导出成功: {output_path} ({fmt}, {len(responses)} 条)")


@main.command(name="import-tasks")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), required=True, help="输出 JSON 文件路径")
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["json", "jsonl", "csv"]),
    default=None,
    help="输入格式 (默认: 自动检测)",
)
def import_tasks(input_file: str, output: str, fmt: Optional[str]):
    """导入任务数据并转换为 DataLabel JSON 格式

    INPUT_FILE: 输入文件路径 (JSON/JSONL/CSV)
    """
    input_path = Path(input_file)

    # Auto-detect format
    if fmt is None:
        suffix = input_path.suffix.lower()
        if suffix == ".jsonl":
            fmt = "jsonl"
        elif suffix == ".csv":
            fmt = "csv"
        else:
            fmt = "json"

    tasks = []

    if fmt == "json":
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            tasks = data
        elif isinstance(data, dict):
            tasks = data.get("samples", data.get("tasks", []))
    elif fmt == "jsonl":
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    tasks.append(json.loads(line))
    elif fmt == "csv":
        with open(input_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                task = {}
                for k, v in row.items():
                    if v and v.startswith(("{", "[")):
                        try:
                            task[k] = json.loads(v)
                        except json.JSONDecodeError:
                            task[k] = v
                    else:
                        task[k] = v
                tasks.append(task)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    click.echo(f"✓ 导入成功: {output_path} ({len(tasks)} 条)")


if __name__ == "__main__":
    main()
