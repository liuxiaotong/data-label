"""结果收集路由"""

from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def submit_result(body: dict):
    """提交单条标注结果"""
    # TODO: 验证并存储标注结果，回调 antgather
    return {"status": "not_implemented", "message": "Single submission pending"}


@router.post("/batch")
async def submit_batch(body: dict):
    """批量提交标注结果"""
    # TODO: 批量验证并存储，回调 antgather
    return {"status": "not_implemented", "message": "Batch submission pending"}
