import logging

from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.common.pagination import normalize_page
from app.common.response import PageResponse
from app.models.equipment import Equipment
from app.models.lab import Lab
from app.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentResponse,
    EquipmentUpdateRequest,
)

logger = logging.getLogger(__name__)


def _fill_res(res: EquipmentResponse, item: Equipment) -> EquipmentResponse:
    """
    历史上 EquipmentResponse.equipment_id 字段被复用为 lab_id，
    这里集中处理这个映射，避免各函数散落修改。
    TODO: 后续统一 schema，把 equipment_id 改名成 lab_id。
    """
    res.equipment_id = item.lab_id
    res.equipment_name = item.lab.name if item.lab else None
    return res


def get_equipment_page_list(
    db: Session,
    page: int,
    page_size: int,
    keywords: str | None = None,
    lab_id: int | None = None,
):
    """分页模糊查询设备列表"""
    page, page_size = normalize_page(page, page_size)
    query = db.query(Equipment)

    if lab_id is not None:
        query = query.filter(Equipment.lab_id == lab_id)
    if keywords:
        query = query.filter(Equipment.name.ilike(f"%{keywords}%"))

    total = query.count()
    items = (
        query.order_by(Equipment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for item in items:
        res = EquipmentResponse.model_validate(item)
        _fill_res(res, item)
        result.append(res)
    return PageResponse(list=result, total=total)


def create_equipment(db: Session, data: EquipmentCreateRequest):
    """新增设备"""
    exist = db.query(Equipment).filter(Equipment.name == data.name).first()
    if exist:
        raise BusinessException(message="实验室设备已存在")

    payload = data.model_dump()
    lab_id = payload.pop("equipment_id", None)  # 兼容旧字段名
    if lab_id is not None:
        payload["lab_id"] = lab_id

    lab = db.query(Lab).filter(Lab.id == payload.get("lab_id")).first()
    if not lab:
        raise BusinessException(
            message=f"ID为 {payload.get('lab_id')} 的实验室不存在，请先选择/添加实验室"
        )

    equipment = Equipment(**payload)
    db.add(equipment)
    db.commit()
    db.refresh(equipment)

    res = EquipmentResponse.model_validate(equipment)
    _fill_res(res, equipment)
    return res


def update_equipment(db: Session, equipment_id: int, data: EquipmentUpdateRequest):
    """更新设备"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")

    payload = data.model_dump(exclude_none=True)

    lab_id = payload.pop("equipment_id", None)  # 兼容旧字段名
    if lab_id is None:
        lab_id = equipment.lab_id
    else:
        payload["lab_id"] = lab_id

    name = payload.get("name", equipment.name)

    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message=f"ID为 {lab_id} 的实验室不存在")

    exist = (
        db.query(Equipment)
        .filter(
            Equipment.lab_id == lab_id,
            Equipment.name == name,
            Equipment.id != equipment.id,
        )
        .first()
    )
    if exist:
        raise BusinessException(message="同一个实验室不能存在同名的设备")

    for field, value in payload.items():
        setattr(equipment, field, value)

    db.commit()
    db.refresh(equipment)

    res = EquipmentResponse.model_validate(equipment)
    _fill_res(res, equipment)
    return res


def delete_equipment(db: Session, equipment_id: int):
    """删除设备"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验室设备不存在")
    # 有预约关联时不允许删除，避免外键约束导致删除失败
    from app.models.reservation import Reservation

    if (
        db.query(Reservation)
        .filter(Reservation.equipment_id == equipment_id)
        .count()
        > 0
    ):
        raise BusinessException(message="该设备存在关联的预约记录，无法删除")
    db.delete(equipment)
    db.commit()
