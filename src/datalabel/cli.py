"""DataLabel CLI - 命令行界面."""

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
    "-o", "--output",
    type=click.Path(),
    help="输出文件路径 (默认: analysis_dir/10_标注工具/annotator.html)"
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
        click.echo(f"\n在浏览器中打开此文件即可开始标注")
    else:
        click.echo(f"✗ 生成失败: {result.error}", err=True)
        sys.exit(1)


@main.command()
@click.argument("schema_file", type=click.Path(exists=True))
@click.argument("tasks_file", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    required=True,
    help="输出 HTML 文件路径"
)
@click.option(
    "-g", "--guidelines",
    type=click.Path(exists=True),
    help="标注指南文件路径 (Markdown 格式)"
)
@click.option(
    "-t", "--title",
    type=str,
    help="标注界面标题"
)
def create(
    schema_file: str,
    tasks_file: str,
    output: str,
    guidelines: Optional[str],
    title: Optional[str],
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

    click.echo(f"正在创建标注界面...")
    click.echo(f"  Schema: {schema_file}")
    click.echo(f"  任务数: {len(tasks)}")

    generator = AnnotatorGenerator()
    result = generator.generate(
        schema=schema,
        tasks=tasks,
        output_path=output,
        guidelines=guidelines_content,
        title=title,
    )

    if result.success:
        click.echo(f"✓ 创建成功: {result.output_path}")
        click.echo(f"\n在浏览器中打开此文件即可开始标注")
    else:
        click.echo(f"✗ 创建失败: {result.error}", err=True)
        sys.exit(1)


@main.command()
@click.argument("result_files", nargs=-1, type=click.Path(exists=True), required=True)
@click.option(
    "-o", "--output",
    type=click.Path(),
    required=True,
    help="合并结果输出路径"
)
@click.option(
    "-s", "--strategy",
    type=click.Choice(["majority", "average", "strict"]),
    default="majority",
    help="合并策略 (默认: majority)"
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

    click.echo(f"\n标注员间一致性 (IAA) 指标:")
    click.echo(f"  标注员数: {metrics['annotator_count']}")
    click.echo(f"  共同任务: {metrics['common_tasks']}")
    click.echo(f"  完全一致率: {metrics['exact_agreement_rate']:.1%}")

    click.echo(f"\n两两一致矩阵:")
    files = [Path(f).name for f in metrics['files']]

    # 打印表头
    header = "          " + "  ".join(f"{f[:8]:>8}" for f in files)
    click.echo(header)

    # 打印矩阵
    for i, row in enumerate(metrics['pairwise_agreement']):
        row_str = f"{files[i][:8]:>8}  " + "  ".join(f"{v:>8.1%}" for v in row)
        click.echo(row_str)


if __name__ == "__main__":
    main()
