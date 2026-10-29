

from sqlalchemy import or_
from app.common.pagination import normalize_page
from app.common.response import PageResponse
from app.common.exceptions import BusinessException
from app.models.user import User
from app.models.reservation import Reservation
from app.models.ai import AIConversation
from app.schemas.user import UserResponse,UserUpdateRequest,PasswordUpdateRequest,UserCreateRequest
from sqlalchemy.orm import Session
from app.utils.password import verify_password,hash_password

def get_user_info(user: User) -> UserResponse:
    return UserResponse.model_validate(user)


def update_user_info(db: Session, user: User, data: UserUpdateRequest):
    user_dict = data.model_dump(exclude_none=True,exclude={"role","status"})  # pydantic对象转换成字典
    for field, value in user_dict.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_password(db: Session, user: User, data: PasswordUpdateRequest):
    """修改密码"""
    if not verify_password(data.old_password, user.password):
        raise BusinessException(message="原密码错误")
    if data.old_password == data.new_password:
        raise BusinessException(message="新密码不能跟原密码相同")
    user.password = hash_password(data.new_password)
    db.commit()


def get_user_page_list(
    db: Session, page: int, page_size: int, keywords: str | None = None
):
    page, page_size = normalize_page(page, page_size)
    query = db.query(User)
    
    if keywords:
        # 使用 or_ 进行多字段联合模糊搜索
        query = query.filter(
            or_(
                User.username.ilike(f"%{keywords}%"),
                User.name.ilike(f"%{keywords}%")
            )
        )
    
    # 先计算总数（不带排序，SQL 更简洁）
    total = query.count()
    
    # 分页与排序
    items = (
        query.order_by(User.id.desc())  # 必须放在 limit/offset 之前
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return PageResponse(
        list=[UserResponse.model_validate(item) for item in items],
        total=total
    ) 

def create_user(db: Session, data: UserCreateRequest):
    """新增用户"""
    exist = db.query(User).filter(User.username == data.username).first()
    if exist:
        raise BusinessException(message="账号已存在")

    user = User(
        username=data.username,
        password=hash_password(data.password),
        name=data.name,
        role=data.role,
        email=data.email,
        phone=data.phone,
        avatar=data.avatar,
        status=data.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def update_user(db: Session, user_id: int, data: UserUpdateRequest):
    """更新用户"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    payload = data.model_dump(exclude_none=True)
    for filed, value in payload.items():
        setattr(user, filed, value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

def delete_user(db: Session, user_id: int, current_user: User):
    """删除用户"""
    if user_id == current_user.id:
        raise BusinessException(message="不能删除当前登录的账号")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    # 有关联数据时不允许删除，避免外键约束导致删除失败
    if db.query(Reservation).filter(Reservation.user_id == user_id).count() > 0:
        raise BusinessException(message="该用户存在预约记录，无法删除")
    if db.query(AIConversation).filter(AIConversation.user_id == user_id).count() > 0:
        raise BusinessException(message="该用户存在AI对话记录，无法删除")
    db.delete(user)
    db.commit()