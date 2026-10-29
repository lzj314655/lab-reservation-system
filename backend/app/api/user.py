

from fastapi import APIRouter,Depends,Query
from app.common.pagination import MAX_PAGE_SIZE
from app.common.response import Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserUpdateRequest,PasswordUpdateRequest,UserCreateRequest
from app.services import user_service
from app.dependencies.auth import get_current_admin, get_current_user
router = APIRouter(prefix="/user",tags=["用户信息"])

@router.get("/info")
def get_user_info(current_user:User = Depends(get_current_user)):
    return Response.success(data= user_service.get_user_info(current_user))
        
@router.put("/update")
def update_user_info(data: UserUpdateRequest,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)
                     ):
    res = user_service.update_user_info(db, current_user, data)
    return Response.success(data=res)


@router.put("/password")
def update_password(
    data: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.update_password(db, current_user, data)
    return Response.success()

@router.get("/list")
def get_user_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=MAX_PAGE_SIZE),
    username: str | None = None,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = user_service.get_user_page_list(db, page, page_size, username)
    return Response.success(data=res)

@router.post("")
def create_user(
    data: UserCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = user_service.create_user(db, data)
    return Response.success(data=res)

@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = user_service.update_user(db, user_id, data)
    return Response.success(data=res)

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user_service.delete_user(db, user_id, current_user)
    return Response.success()