"""标注界面渲染路由"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/{task_batch_id}")
async def render_labeling_page(task_batch_id: str):
    """渲染标注页面 HTML"""
    # TODO: 调用 datalabel.generator 生成标注界面 HTML
    return {"status": "not_implemented", "task_batch_id": task_batch_id}
