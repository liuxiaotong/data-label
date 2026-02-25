"""合并 + IAA 计算路由"""

from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def merge_results(body: dict):
    """合并多人标注结果"""
    # TODO: 调用 datalabel.merger 执行合并
    return {"status": "not_implemented", "message": "Merge pending"}


@router.post("/iaa")
async def calculate_iaa(body: dict):
    """计算标注者间一致性（Inter-Annotator Agreement）"""
    # TODO: 调用 datalabel.merger 计算 IAA 指标
    return {"status": "not_implemented", "message": "IAA calculation pending"}
