from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin, get_current_user
from app.models.user import User
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["数据统计"])


@router.get("/overview")
def get_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return Response.success(data=stats_service.get_overview(db, current_user))


@router.get("/trend")
def get_trend(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return Response.success(data=stats_service.get_trend(db, current_user, days))


@router.get("/lab-usage")
def get_lab_usage(
    limit: int = Query(8, ge=1, le=20),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return Response.success(data=stats_service.get_lab_usage(db, limit))


@router.get("/my-status")
def get_my_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return Response.success(data=stats_service.get_my_status(db, current_user))
