"""Schema 管理路由"""

import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException

from datalabel.validator import SchemaValidator

router = APIRouter()

# 内存存储（Phase 3 迁移到 antgather DB）
_schemas: Dict[str, dict] = {}

_validator = SchemaValidator()


def _gen_schema_id() -> str:
    """生成短格式 schema ID"""
    return uuid.uuid4().hex[:12]


@router.post("")
async def create_schema(body: dict):
    """创建标注 Schema

    验证 schema 合法性后存入内存，返回 schema_id。
    """
    result = _validator.validate_schema(body)
    if not result.valid:
        raise HTTPException(status_code=422, detail={
            "errors": result.errors,
            "warnings": result.warnings,
        })

    schema_id = _gen_schema_id()
    _schemas[schema_id] = body

    return {
        "schema_id": schema_id,
        "warnings": result.warnings,
    }


@router.get("/{schema_id}")
async def get_schema(schema_id: str):
    """获取标注 Schema"""
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' 不存在")
    return {"schema_id": schema_id, "schema": _schemas[schema_id]}


@router.put("/{schema_id}")
async def update_schema(schema_id: str, body: dict):
    """更新标注 Schema"""
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' 不存在")

    result = _validator.validate_schema(body)
    if not result.valid:
        raise HTTPException(status_code=422, detail={
            "errors": result.errors,
            "warnings": result.warnings,
        })

    _schemas[schema_id] = body
    return {
        "schema_id": schema_id,
        "warnings": result.warnings,
    }


@router.delete("/{schema_id}")
async def delete_schema(schema_id: str):
    """删除标注 Schema"""
    if schema_id not in _schemas:
        raise HTTPException(status_code=404, detail=f"Schema '{schema_id}' 不存在")

    del _schemas[schema_id]
    return {"deleted": schema_id}
