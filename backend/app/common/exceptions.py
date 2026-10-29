import logging
import traceback
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
# 建议将导入的自定义响应模型重命名，避免与 FastAPI 原生 Response 冲突
from app.common.response import Response as ApiResponse 

logger = logging.getLogger(__name__)

class BusinessException(Exception):
    """自定义的业务异常"""
    def __init__(self, message: str, code: int = 500):
        self.message = message
        self.code = code
        super().__init__(message)

async def business_exception_handler(request: Request, exc: BusinessException):
    """自定义业务异常处理器"""
    return JSONResponse(
        status_code=200, # 业务异常统一返回 HTTP 200
        content=ApiResponse.error(code=exc.code, message=exc.message).model_dump(),
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Http异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse.error(code=exc.status_code, message=exc.detail).model_dump(),
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数异常处理器"""
    # RequestValidationError 没有 status_code 和 detail 属性
    # 提取第一条错误信息作为提示
    errors = exc.errors()
    error_msg = errors[0].get("msg", "参数校验失败") if errors else "参数校验失败"
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiResponse.error(code=422, message=error_msg).model_dump(),
    )

async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    # 关键：记录未捕获异常的详细堆栈，方便排查问题
    logger.exception("未捕获的系统异常: %s", exc)
    print("🚨 捕获到全局异常，真实错误如下：")
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # 系统异常应返回 500
        content=ApiResponse.error(code=500, message="服务器内部错误").model_dump(),
    )