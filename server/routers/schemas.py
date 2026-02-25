"""Schema 管理路由"""

from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def create_schema(body: dict):
    """创建标注 Schema"""
    # TODO: 调用 datalabel 核心模块验证并存储 schema
    return {"status": "not_implemented", "message": "Schema creation pending"}


@router.get("/{schema_id}")
async def get_schema(schema_id: str):
    """获取标注 Schema"""
    # TODO: 从存储中读取 schema 并返回
    return {"status": "not_implemented", "schema_id": schema_id}
