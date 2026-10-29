import asyncio
from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import UPLOAD_DIR, settings
from app.database import Base, engine
from app.api import api
from app.common.exceptions import (
    BusinessException,
    business_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    global_exception_handler
)
from app.services import kb_service
from app import scheduler



Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app:FastAPI):
    # 定时任务先行启动（不依赖知识库，不应被预热阻塞）
    scheduler.start_scheduler()

    # 知识库预热放后台：首次加载 embedding 模型可能较慢，
    # 不阻塞对外服务；kb_service.search 本身也有懒加载兜底
    warmup_task = asyncio.create_task(asyncio.to_thread(_safe_warmup))
    try:
        yield
    finally:
        warmup_task.cancel()
        scheduler.shutdown_scheduler()


def _safe_warmup():
    try:
        kb_service.warmup()
    except Exception:
        traceback.print_exc()

# 关键：lifespan 必须显式传入，否则启动钩子（知识库预热/定时扫描）不会执行
app = FastAPI(lifespan=lifespan)

origins = settings.cors_origin_list
app.add_middleware(CORSMiddleware,allow_origins=origins,
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"],
                   )

app.include_router(api)
# 1. 注册业务异常处理器（必须是这个！）
app.add_exception_handler(BusinessException, business_exception_handler)

# 2. 注册 HTTP 异常处理器
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

# 3. 注册参数校验异常处理器
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# 4. 注册全局兜底异常处理器（必须最后）
app.add_exception_handler(Exception, global_exception_handler)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")



@app.get("/")
def root():
    return {"message": "Hello FastAPI"}


@app.get("/health")
def health():
    """容器健康检查：数据库连通性探活"""
    from sqlalchemy import text

    from app.database import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except Exception:
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=503, content={"status": "degraded", "db": "down"})