"""合并 + IAA 计算路由"""

import json
import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException

from datalabel.merger import ResultMerger

router = APIRouter()

_merger = ResultMerger()


@router.post("")
async def merge_results(body: dict):
    """合并多人标注结果

    Body:
        responses: list[dict] — 多个标注者的结果文件内容
            每个元素格式: {"metadata": {...}, "responses": [{"task_id": ..., "score": ...}, ...]}
        strategy: str — 合并策略 ("majority" / "average" / "strict")，默认 "majority"

    Returns:
        合并后的结果 + 统计信息
    """
    responses_data = body.get("responses")
    if not responses_data or not isinstance(responses_data, list):
        raise HTTPException(status_code=422, detail="缺少 responses 数组")

    if len(responses_data) < 1:
        raise HTTPException(status_code=422, detail="至少需要 1 份标注结果")

    strategy = body.get("strategy", "majority")
    if strategy not in ("majority", "average", "strict"):
        raise HTTPException(status_code=422, detail=f"不支持的合并策略: {strategy}")

    # ResultMerger 需要文件路径，写入临时文件
    with tempfile.TemporaryDirectory() as tmpdir:
        files = []
        for i, data in enumerate(responses_data):
            path = Path(tmpdir) / f"ann_{i}.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            files.append(str(path))

        output_path = Path(tmpdir) / "merged.json"

        result = _merger.merge(
            result_files=files,
            output_path=str(output_path),
            strategy=strategy,
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)

        merged_data = json.loads(output_path.read_text(encoding="utf-8"))

    return {
        "success": True,
        "annotator_count": result.annotator_count,
        "total_tasks": result.total_tasks,
        "agreement_rate": result.agreement_rate,
        "conflict_count": len(result.conflicts),
        "merged": merged_data,
    }


@router.post("/iaa")
async def calculate_iaa(body: dict):
    """计算标注者间一致性（Inter-Annotator Agreement）

    Body:
        responses: list[dict] — 多个标注者的结果文件内容（至少 2 份）

    Returns:
        IAA 指标（exact_agreement_rate, Cohen's Kappa, Fleiss' Kappa, Krippendorff's Alpha）
    """
    responses_data = body.get("responses")
    if not responses_data or not isinstance(responses_data, list):
        raise HTTPException(status_code=422, detail="缺少 responses 数组")

    if len(responses_data) < 2:
        raise HTTPException(status_code=422, detail="至少需要 2 份标注结果才能计算 IAA")

    # 写入临时文件供 merger 读取
    with tempfile.TemporaryDirectory() as tmpdir:
        files = []
        for i, data in enumerate(responses_data):
            path = Path(tmpdir) / f"ann_{i}.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            files.append(str(path))

        metrics = _merger.calculate_iaa(result_files=files)

    if "error" in metrics:
        raise HTTPException(status_code=422, detail=metrics["error"])

    return {"success": True, "metrics": metrics}
