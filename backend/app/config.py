from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 当前文件所在目录的上一级 = backend 根目录
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY:str
    JWT_EXPIRE_HOURS:int
    JWT_ALGORITHM:str="HS256"
    LLM_API_KEY:str
    LLM_MODEL:str
    LLM_BASE_URL:str
    # 允许跨域的前端地址，逗号分隔；默认覆盖 Vite 开发服务器
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100M

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
}