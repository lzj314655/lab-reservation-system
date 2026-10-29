from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.common.response import Response
from app.common.pagination import MAX_PAGE_SIZE
from app.models.user import User
from app.dependencies.auth import get_current_admin, get_current_user
from app.schemas.lab import (
    LabCreateRequest,
    LabUpdateRequest,
)
from app.services import lab_service
from app.database import get_db

router = APIRouter(prefix="/lab", tags=["实验室信息接口"])

@router.get("/list")
def get_lab_list(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(10, ge=1, le=MAX_PAGE_SIZE, description="每页条数，上限 100"),
    keywords: str | None = None,
    status:int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = lab_service.get_lab_page_list(db, page, page_size, keywords, status)
    return Response.success(data=res)

@router.post("")
def create_lab(
    data: LabCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = lab_service.create_lab(db, data)
    return Response.success(data=res)

@router.put("/{lab_id}")
def update_lab(
    lab_id: int,
    data: LabUpdateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    res = lab_service.update_lab(db, lab_id, data)
    return Response.success(data=res)


@router.delete("/{lab_id}")
def delete_lab(
    lab_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lab_service.delete_lab(db, lab_id)
    return Response.success()

@router.get("/{lab_id}")
def get_lab(
    lab_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = lab_service.get_lab(db, lab_id)
    return Response.success(data=res)