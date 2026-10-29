from fastapi import APIRouter, Depends, Request
from app.common.response import Response
from app.schemas.auth import LoginRequest, RegisterRequest
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import auth_service


router = APIRouter(prefix="/auth", tags=["权限验证"])

@router.post("/login")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else ""
    result = auth_service.login(db, data, client_ip)
    return Response.success(
        message="登录成功",
        data=result,
    )


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    auth_service.register(db, data)
    return Response.success(
        message="注册成功",
    )
