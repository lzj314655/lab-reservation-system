
from app.common.response import PageResponse
from app.common.pagination import normalize_page
from app.models.lab import Lab
from app.schemas.lab import LabCreateRequest, LabResponse, LabUpdateRequest
from app.common.exceptions import BusinessException
from sqlalchemy.orm import Session


def get_lab_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    status: int | None = None,
):
    """分页模糊查询实验室列表"""
    page, page_size = normalize_page(page, page_size)
    query = db.query(Lab)
    if keywords:
        query = query.filter(Lab.name.ilike(f"%{keywords}%"))
    # 注意用 is not None：status=0（已关闭）是有效筛选条件，不能当"没传"
    if status is not None:
        query = query.filter(Lab.status == status)

    total = query.count()
    items = (
        query.order_by(Lab.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PageResponse(
        list=[LabResponse.model_validate(item) for item in items], total=total
    )


def get_lab(db: Session, lab_id: int):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    return LabResponse.model_validate(lab)


def create_lab(db: Session, data: LabCreateRequest):
    """新增实验室"""
    exist = db.query(Lab).filter(Lab.name == data.name).first()
    if exist:
        raise BusinessException(message="实验室已存在")
    lab = Lab(**data.model_dump())
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def update_lab(db: Session, lab_id: int, data: LabUpdateRequest):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    payload = data.model_dump(exclude_none=True)
    for field, value in payload.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


def delete_lab(db: Session, lab_id: int):
    """删除实验室"""
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    # 有关联数据时不允许删除，避免外键约束导致删除失败
    from app.models.equipment import Equipment
    from app.models.reservation import Reservation

    if db.query(Equipment).filter(Equipment.lab_id == lab_id).count() > 0:
        raise BusinessException(message="该实验室下存在设备，请先删除设备")
    if db.query(Reservation).filter(Reservation.lab_id == lab_id).count() > 0:
        raise BusinessException(message="该实验室存在关联的预约记录，无法删除")
    db.delete(lab)
    db.commit()
