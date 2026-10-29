from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from app.schemas.user import UserResponse
from app.services import login_guard
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token

def login(db: Session, data: LoginRequest, client_ip: str = ""):
    # 0. 失败次数限流：同一 (IP, 账号) 15 分钟内失败 5 次后直接拒绝
    if login_guard.is_blocked(client_ip, data.username):
        raise BusinessException(
            message="登录失败次数过多，请 15 分钟后再试", code=429
        )

    user = db.query(User).filter(User.username == data.username).first()
        # 2. 校验用户是否存在 & 密码是否正确（利用短路运算防止空指针）
    if not user or not verify_password(data.password, user.password):
        login_guard.record_failure(client_ip, data.username)
        raise BusinessException(message="账号密码错误")
        # 3. 校验用户状态
    if user.status != 1:
        raise BusinessException(message="账号被禁用")
        # 4. 所有校验都通过后，才生成 Token（安全做法）
    login_guard.reset(client_ip, data.username)
    token = create_access_token(user.id)

    return LoginResponse(token=token,user=UserResponse.model_validate(user))

def register(db: Session, data: RegisterRequest):
    user = db.query(User).filter(User.username == data.username).first()
    if user:
        raise BusinessException(message="账号已存在")
    
    # 2. 加密密码
    hashed_pwd = hash_password(data.password)
    
    # 3. 数据兜底检查（防止意外崩溃）
    if not hashed_pwd:
        raise BusinessException(message="密码加密失败")

    # 4. 写入数据库
    user_model = User(
        username=data.username,
        password=hashed_pwd,
        name=data.name or data.username,
        role="student",
        status=1,
    )
    
    try:
        db.add(user_model)
        db.commit()
        db.refresh(user_model)
    except Exception as e:
        db.rollback() # 发生错误时回滚事务，非常重要！
        raise e