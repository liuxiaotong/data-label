"""DataLabel CLI - 命令行界面."""

import json
import sys
from pathlib import Path
from typing import Optional

import click

from datalabel import __version__
from datalabel.dashboard import DashboardGenerator
from datalabel.generator import AnnotatorGenerator
from datalabel.io import export_responses, extract_responses, import_tasks_from_file
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
@click.option(
    "--theme",
    type=click.Choice(["default", "knowlyr"]),
    default="default",
    help="界面主题 (默认: default)",
)
def generate(analysis_dir: str, output: Optional[str], theme: str):
    """从 DataRecipe 分析结果生成标注界面

    ANALYSIS_DIR: DataRecipe 分析输出目录的路径
    """
    click.echo(f"正在从 {analysis_dir} 生成标注界面...")

    generator = AnnotatorGenerator()
    result = generator.generate_from_datarecipe(
        analysis_dir=analysis_dir,
        output_path=output,
        theme=theme,
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
@click.option(
    "--theme",
    type=click.Choice(["default", "knowlyr"]),
    default="default",
    help="界面主题 (默认: default)",
)
def create(
    schema_file: str,
    tasks_file: str,
    output: str,
    guidelines: Optional[str],
    title: Optional[str],
    page_size: int,
    theme: str,
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
        theme=theme,
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


@main.command()
@click.argument("result_files", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("-o", "--output", type=click.Path(), required=True, help="输出 HTML 文件路径")
@click.option(
    "-s", "--schema", "schema_file", type=click.Path(exists=True), help="Schema JSON 文件（可选）"
)
@click.option("-t", "--title", type=str, help="仪表盘标题")
def dashboard(result_files: tuple, output: str, schema_file: Optional[str], title: Optional[str]):
    """生成标注进度仪表盘

    RESULT_FILES: 标注结果 JSON 文件列表
    """
    if len(result_files) < 1:
        click.echo("错误: 至少需要 1 个标注结果文件", err=True)
        sys.exit(1)

    schema = None
    if schema_file:
        with open(schema_file, "r", encoding="utf-8") as f:
            schema = json.load(f)

    click.echo(f"正在生成仪表盘 ({len(result_files)} 个结果文件)...")

    gen = DashboardGenerator()
    result = gen.generate(
        result_files=list(result_files),
        output_path=output,
        schema=schema,
        title=title,
    )

    if result.success:
        click.echo(f"✓ 仪表盘已生成: {result.output_path}")
        click.echo(f"  标注员数: {result.annotator_count}")
        click.echo(f"  总任务数: {result.total_tasks}")
        click.echo(f"  平均完成率: {result.overall_completion:.1%}")
        click.echo("\n在浏览器中打开此文件查看仪表盘")
    else:
        click.echo(f"✗ 生成失败: {result.error}", err=True)
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

    responses = extract_responses(data)
    if responses is None:
        click.echo("错误: 无法识别的结果文件格式", err=True)
        sys.exit(1)

    count = export_responses(responses, output, fmt)
    click.echo(f"✓ 导出成功: {output} ({fmt}, {count} 条)")


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
    tasks = import_tasks_from_file(input_file, fmt)

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

    click.echo(f"✓ 导入成功: {output_path} ({len(tasks)} 条)")


# ============================================================
# LLM 分析命令
# ============================================================

_PROVIDER_OPTION = click.option(
    "-p",
    "--provider",
    type=click.Choice(["moonshot", "openai", "anthropic"]),
    default="moonshot",
    help="LLM 提供商 (默认: moonshot)",
)
_MODEL_OPTION = click.option(
    "-m", "--model", type=str, default=None, help="模型名称 (默认: 提供商默认模型)"
)


def _load_tasks_file(tasks_file: str) -> list[dict]:
    """从文件加载任务列表。"""
    with open(tasks_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("samples", data.get("tasks", []))


@main.command()
@click.argument("schema_file", type=click.Path(exists=True))
@click.argument("tasks_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), required=True, help="输出文件路径")
@_PROVIDER_OPTION
@_MODEL_OPTION
@click.option("--batch-size", type=int, default=5, help="每批处理任务数 (默认: 5)")
def prelabel(
    schema_file: str,
    tasks_file: str,
    output: str,
    provider: str,
    model: Optional[str],
    batch_size: int,
):
    """使用 LLM 自动预标注

    SCHEMA_FILE: 标注规范 JSON 文件
    TASKS_FILE: 待标注任务 JSON 文件
    """
    from datalabel.llm import LLMClient, LLMConfig, PreLabeler

    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)
    tasks = _load_tasks_file(tasks_file)

    click.echo(f"正在使用 {provider} 进行自动预标注...")
    click.echo(f"  任务数: {len(tasks)}, 批大小: {batch_size}")

    config = LLMConfig(provider=provider, model=model)
    client = LLMClient(config=config)
    labeler = PreLabeler(client=client)

    result = labeler.prelabel(schema=schema, tasks=tasks, output_path=output, batch_size=batch_size)

    if result.success:
        click.echo(f"✓ 预标注完成: {result.output_path}")
        click.echo(f"  标注数: {result.labeled_tasks}/{result.total_tasks}")
        click.echo(
            f"  Token 用量: {result.total_usage.prompt_tokens} + "
            f"{result.total_usage.completion_tokens} = {result.total_usage.total_tokens}"
        )
    else:
        click.echo(f"✗ 预标注失败: {result.error}", err=True)
        sys.exit(1)


@main.command()
@click.argument("schema_file", type=click.Path(exists=True))
@click.argument("result_files", nargs=-1, type=click.Path(exists=True), required=True)
@click.option("-o", "--output", type=click.Path(), help="报告输出路径 (JSON)")
@_PROVIDER_OPTION
@_MODEL_OPTION
@click.option("--sample-size", type=int, default=20, help="每个标注员抽样数 (默认: 20)")
def quality(
    schema_file: str,
    result_files: tuple,
    output: Optional[str],
    provider: str,
    model: Optional[str],
    sample_size: int,
):
    """使用 LLM 分析标注质量

    SCHEMA_FILE: 标注规范 JSON 文件
    RESULT_FILES: 标注结果 JSON 文件列表
    """
    from datalabel.llm import LLMClient, LLMConfig, QualityAnalyzer

    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    click.echo(f"正在使用 {provider} 分析标注质量...")
    click.echo(f"  结果文件数: {len(result_files)}")

    config = LLMConfig(provider=provider, model=model)
    client = LLMClient(config=config)
    analyzer = QualityAnalyzer(client=client)

    report = analyzer.analyze(
        schema=schema,
        result_files=list(result_files),
        output_path=output,
        sample_size=sample_size,
    )

    if report.success:
        click.echo("\n质量分析报告:")
        click.echo(f"  {report.summary}")
        if report.issues:
            click.echo(f"\n发现 {len(report.issues)} 个问题:")
            for issue in report.issues:
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue.severity, "⚪")
                click.echo(f"  {icon} [{issue.task_id}] {issue.description}")
        if report.disagreement_analysis:
            click.echo("\n分歧分析:")
            patterns = report.disagreement_analysis.get("common_patterns", "")
            if patterns:
                click.echo(f"  共性模式: {patterns}")
        if output:
            click.echo(f"\n✓ 报告已保存: {output}")
        click.echo(
            f"\n  Token 用量: {report.total_usage.total_tokens}"
        )
    else:
        click.echo(f"✗ 分析失败: {report.error}", err=True)
        sys.exit(1)


@main.command(name="gen-guidelines")
@click.argument("schema_file", type=click.Path(exists=True))
@click.option("-t", "--tasks", "tasks_file", type=click.Path(exists=True), help="样例任务文件")
@click.option("-o", "--output", type=click.Path(), required=True, help="输出文件路径 (Markdown)")
@_PROVIDER_OPTION
@_MODEL_OPTION
@click.option(
    "-l",
    "--language",
    type=click.Choice(["zh", "en"]),
    default="zh",
    help="指南语言 (默认: zh)",
)
def gen_guidelines(
    schema_file: str,
    tasks_file: Optional[str],
    output: str,
    provider: str,
    model: Optional[str],
    language: str,
):
    """使用 LLM 生成标注指南

    SCHEMA_FILE: 标注规范 JSON 文件
    """
    from datalabel.llm import GuidelinesGenerator, LLMClient, LLMConfig

    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    tasks = None
    if tasks_file:
        tasks = _load_tasks_file(tasks_file)

    click.echo(f"正在使用 {provider} 生成标注指南...")

    config = LLMConfig(provider=provider, model=model)
    client = LLMClient(config=config)
    gen = GuidelinesGenerator(client=client)

    result = gen.generate(schema=schema, tasks=tasks, output_path=output, language=language)

    if result.success:
        click.echo(f"✓ 指南生成成功: {result.output_path}")
        click.echo(
            f"  Token 用量: {result.total_usage.total_tokens}"
        )
    else:
        click.echo(f"✗ 生成失败: {result.error}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
