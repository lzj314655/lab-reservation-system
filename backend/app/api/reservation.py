from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.pagination import MAX_PAGE_SIZE
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user,get_current_admin
from app.models.user import User
from app.schemas.reservation import ReservationCreateRequest,ReservationResponse,AuditReservationRequest
from app.services import reservation_service

router = APIRouter(prefix="/reservation", tags=["预约相关接口"])


@router.post("")
def create_reservation(
    data: ReservationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = reservation_service.create_reservation(db, current_user, data)
    return Response.success(
        message="预约已提交，请等待管理员审核",
        data=ReservationResponse.model_validate(item),
    )


@router.get("/list")
def get_reservation_page_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=MAX_PAGE_SIZE),
    status: int | None = None,
    keyword: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = reservation_service.get_reservation_page_list(
        db, current_user, page, page_size, status, keyword
    )
    return Response.success(data=res)

@router.get("/calendar")
def get_lab_calendar(
    lab_id: int,
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """实验室日历视图：查询某实验室在日期区间内的预约占用"""
    res = reservation_service.get_lab_calendar(db, lab_id, start_date, end_date)
    return Response.success(data=res)


@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reservation_service.cancel_reservation(db, current_user, reservation_id)
    return Response.success()

@router.put("/{reservation_id}/audit")
def audit_reservation(
    reservation_id: int,
    data: AuditReservationRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    reservation_service.audit_reservation(db, reservation_id, data.status)
    return Response.success()