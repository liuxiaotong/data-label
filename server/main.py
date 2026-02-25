"""data-label 在线服务 -- FastAPI 应用入口"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import schemas, render, submit, merge

app = FastAPI(
    title="data-label API",
    version="0.1.0",
    description="标注 Schema 管理、界面渲染、结果收集、IAA 计算",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schemas.router, prefix="/api/schemas", tags=["schemas"])
app.include_router(render.router, prefix="/api/render", tags=["render"])
app.include_router(submit.router, prefix="/api/submit", tags=["submit"])
app.include_router(merge.router, prefix="/api/merge", tags=["merge"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "data-label", "version": "0.1.0"}
