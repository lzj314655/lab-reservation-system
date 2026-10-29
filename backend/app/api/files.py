import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from app.common.exceptions import BusinessException
from app.common.response import Response
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, UPLOAD_DIR
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.file import FileResponse

router = APIRouter(prefix="/files", tags=["文件管理"])

CHUNK = 1024 * 1024


@router.post("/upload")
def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """文件上传接口（必须登录：否则任何人都能匿名上传并占满磁盘）"""
    if not file.filename:
        raise BusinessException(message="文件名不能为空")

    # 1. 取出纯文件名，防止路径穿越（兼容 Windows 分隔符）
    original_name = file.filename.replace("\\", "/").split("/")[-1]

    # 2. 后缀白名单
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessException(message=f"不支持的文件后缀: {ext}")

    # 3. 唯一文件名
    disk_name = f"{uuid.uuid4().hex}{ext}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / disk_name

    # 4. 流式写入 + 大小限制 + 失败清理
    written = 0
    try:
        with open(save_path, "wb") as out:
            while chunk := file.file.read(CHUNK):
                written += len(chunk)
                if written > MAX_FILE_SIZE:
                    raise BusinessException(
                        message=f"文件不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB"
                    )
                out.write(chunk)
    except BusinessException:
        save_path.unlink(missing_ok=True)
        raise
    except Exception:
        save_path.unlink(missing_ok=True)
        raise BusinessException(message="文件保存失败")
    finally:
        file.file.close()

    return Response.success(data=FileResponse(original_name=original_name,
                                              disk_name=disk_name,
                                              size=written,
                                              url=f"/uploads/{disk_name}"))