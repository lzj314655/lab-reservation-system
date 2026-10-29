from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReservationCreateRequest(BaseModel):
    lab_id: int = Field(gt=0)
    equipment_id: int | None = Field(default=None, gt=0)
    date: str
    start_time: str
    end_time: str
    # 数据库列为 String(255)，超长会在 MySQL 严格模式下抛 1406 → 500
    remark: str | None = Field(default=None, max_length=255)

    @field_validator("date")
    @classmethod
    def _validate_date(cls, value: str) -> str:
        """日期必须是 YYYY-MM-DD。

        服务层用字符串比较判断"是否过去"，格式不合法时比较结果不可信
        （如 2026-99-99 会被当成未来日期落库），因此在入口强制归一化。
        """
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError):
            raise ValueError("预约日期格式应为 YYYY-MM-DD")
        return value


class ReservationResponse(BaseModel):
    id: int
    user_id: int
    user_name: str | None = None
    lab_id: int
    lab_name: str | None = None
    equipment_id: int | None = None
    equipment_name: str | None = None
    type: str | None = None
    date: str
    start_time: str
    end_time: str
    remark: str | None = None
    status: int

    model_config = ConfigDict(from_attributes=True)


class AuditReservationRequest(BaseModel):
    status: int  # 1 | 2
