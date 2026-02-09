"""数据导入导出工具函数."""

import csv
import io
import json
from pathlib import Path
from typing import Any


def export_responses(
    responses: list[dict[str, Any]], output_path: str | Path, fmt: str = "json"
) -> int:
    """将标注结果导出为指定格式.

    Args:
        responses: 标注结果列表
        output_path: 输出文件路径
        fmt: 输出格式 (json/jsonl/csv)

    Returns:
        导出的记录数
    """
    output_path = Path(output_path)
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
                    row[k] = (
                        json.dumps(v, ensure_ascii=False)
                        if isinstance(v, (list, dict))
                        else v
                    )
                writer.writerow(row)
            output_path.write_text(buf.getvalue(), encoding="utf-8")
    else:
        raise ValueError(f"不支持的格式: {fmt}")

    return len(responses)


def import_tasks_from_file(
    input_path: str | Path, fmt: str | None = None
) -> list[dict[str, Any]]:
    """从文件导入任务数据.

    Args:
        input_path: 输入文件路径
        fmt: 输入格式 (json/jsonl/csv)，None 则自动检测

    Returns:
        任务列表
    """
    input_path = Path(input_path)

    if fmt is None:
        suffix = input_path.suffix.lower()
        if suffix == ".jsonl":
            fmt = "jsonl"
        elif suffix == ".csv":
            fmt = "csv"
        else:
            fmt = "json"

    tasks: list[dict[str, Any]] = []

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
                task: dict[str, Any] = {}
                for k, v in row.items():
                    if v and v.startswith(("{", "[")):
                        try:
                            task[k] = json.loads(v)
                        except json.JSONDecodeError:
                            task[k] = v
                    else:
                        task[k] = v
                tasks.append(task)
    else:
        raise ValueError(f"不支持的格式: {fmt}")

    return tasks


def extract_responses(data: Any) -> list[dict[str, Any]] | None:
    """从标注结果数据中提取 responses 列表.

    Args:
        data: 原始数据（list 或包含 responses 的 dict）

    Returns:
        responses 列表，无法识别则返回 None
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "responses" in data:
        return data["responses"]
    return None
