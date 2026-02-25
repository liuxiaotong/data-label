"""标注界面渲染路由"""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from datalabel.generator import AnnotatorGenerator

router = APIRouter()

_generator = AnnotatorGenerator()


@router.post("/generate")
async def generate_annotation_page(body: dict):
    """接收 schema + tasks，返回标注页面 HTML

    Body:
        schema: dict — 标注 Schema 定义
        tasks: list — 待标注任务数据
        callback_url: str (可选) — 标注结果提交地址
        title: str (可选) — 页面标题
        guidelines: str (可选) — 标注指南 (markdown)
        theme: str (可选) — 主题 (default / knowlyr)
    """
    schema = body.get("schema")
    if not schema:
        raise HTTPException(status_code=422, detail="缺少 schema 字段")

    tasks = body.get("tasks", [])
    callback_url = body.get("callback_url")
    title = body.get("title")
    guidelines = body.get("guidelines")
    theme = body.get("theme", "default")

    # 生成到临时文件
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        tmp_path = tmp.name

    result = _generator.generate(
        schema=schema,
        tasks=tasks,
        output_path=tmp_path,
        guidelines=guidelines,
        title=title,
        theme=theme,
    )

    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)

    html_content = Path(tmp_path).read_text(encoding="utf-8")

    # 如果有 callback_url，注入在线提交脚本替换 localStorage 保存
    if callback_url:
        html_content = _inject_callback(html_content, callback_url)

    # 清理临时文件
    Path(tmp_path).unlink(missing_ok=True)

    return HTMLResponse(content=html_content)


@router.get("/{task_batch_id}")
async def render_labeling_page(
    task_batch_id: str,
    token: Optional[str] = Query(None),
    callback_url: Optional[str] = Query(None),
):
    """通过 task_batch_id 渲染标注页面

    从内存 schema store 查找关联的 batch 数据。
    目前返回提示信息，待与 batch 管理集成后启用。
    """
    # Phase 1: batch 管理尚未实现，返回说明
    raise HTTPException(
        status_code=501,
        detail=f"Batch '{task_batch_id}' 渲染尚未实现。请使用 POST /api/render/generate 直接传入 schema + tasks。"
    )


def _inject_callback(html: str, callback_url: str) -> str:
    """将 HTML 中的 localStorage 保存逻辑增强为同时 POST 到 callback_url。

    在 saveCurrentResponse 函数的 localStorage.setItem 后面注入 fetch 调用。
    """
    inject_script = f"""
                // === Online callback (injected by data-label server) ===
                try {{
                    fetch('{callback_url}', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(responses[taskId]),
                    }}).catch(err => console.warn('回调提交失败:', err));
                }} catch(e) {{ console.warn('回调异常:', e); }}
                // === End online callback ==="""

    # 在 localStorage.setItem 行之后注入
    target = "localStorage.setItem(storageKey, JSON.stringify(responses));"
    if target in html:
        html = html.replace(
            target,
            target + "\n" + inject_script,
        )

    return html
