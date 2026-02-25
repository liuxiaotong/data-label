"""结果收集路由"""

import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, HTTPException

router = APIRouter()

# 内存暂存（后续由 antgather 拉取或主动推送）
# key: submission_id, value: 标注结果
_submissions: Dict[str, dict] = {}


@router.post("")
async def submit_result(body: dict):
    """提交单条标注结果

    Body:
        task_id: str — 任务 ID
        其他字段取决于标注类型（score / choice / choices / text / ranking / fields）

    Returns:
        submission_id + 确认信息
    """
    task_id = body.get("task_id")
    if not task_id:
        raise HTTPException(status_code=422, detail="缺少 task_id 字段")

    submission_id = uuid.uuid4().hex[:16]
    _submissions[submission_id] = {
        **body,
        "submission_id": submission_id,
        "submitted_at": datetime.now().isoformat(),
    }

    return {
        "success": True,
        "submission_id": submission_id,
        "task_id": task_id,
    }


@router.post("/batch")
async def submit_batch(body: dict):
    """批量提交标注结果

    Body:
        results: list[dict] — 标注结果数组，每条包含 task_id

    Returns:
        submission_ids 列表 + 统计信息
    """
    results = body.get("results")
    if not results or not isinstance(results, list):
        raise HTTPException(status_code=422, detail="缺少 results 数组")

    submission_ids = []
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            raise HTTPException(status_code=422, detail=f"results[{i}] 必须是字典")
        task_id = result.get("task_id")
        if not task_id:
            raise HTTPException(status_code=422, detail=f"results[{i}] 缺少 task_id")

        submission_id = uuid.uuid4().hex[:16]
        _submissions[submission_id] = {
            **result,
            "submission_id": submission_id,
            "submitted_at": datetime.now().isoformat(),
        }
        submission_ids.append(submission_id)

    return {
        "success": True,
        "count": len(submission_ids),
        "submission_ids": submission_ids,
    }


@router.get("/pending")
async def list_pending():
    """列出所有暂存的标注结果（供 antgather 拉取）"""
    return {
        "count": len(_submissions),
        "submissions": list(_submissions.values()),
    }


@router.delete("/pending/{submission_id}")
async def ack_submission(submission_id: str):
    """确认已拉取，删除暂存记录"""
    if submission_id not in _submissions:
        raise HTTPException(status_code=404, detail=f"Submission '{submission_id}' 不存在")
    del _submissions[submission_id]
    return {"deleted": submission_id}
