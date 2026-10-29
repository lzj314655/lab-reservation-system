import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.ai import ChatRequest, ConversationItem, ConversationDetail
from app.services import agent_service
from app.models.ai import AIConversation, AIMessage

router = APIRouter(prefix="/ai", tags=["AI相关的API"])

# 每用户每日 AI 提问上限（按 user 角色消息计数，assistant 回复不占额度）
AI_DAILY_MESSAGE_LIMIT = 200


def _check_daily_limit(db: Session, user: User):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cnt = (
        db.query(AIMessage)
        .join(AIConversation)
        .filter(
            AIConversation.user_id == user.id,
            # 只统计用户提问：原先把 assistant 回复也算进去，实际只有一半轮次
            AIMessage.role == "user",
            AIMessage.created_at >= today_start,
        )
        .count()
    )
    if cnt >= AI_DAILY_MESSAGE_LIMIT:
        raise BusinessException(
            message=f"今日 AI 对话次数已达上限（{AI_DAILY_MESSAGE_LIMIT} 条），请明天再试",
            code=429,
        )


@router.post("/chat/stream")
async def chat_stream(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_daily_limit(db, current_user)

    async def event_gen():
        # 👇 核心修改：将 data.conversation_id 传给 stream_agent
        async for event in agent_service.stream_agent(
            db, current_user, data, data.conversation_id
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
def get_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的会话列表"""
    convs = (
        db.query(AIConversation)
        .filter(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
        .all()
    )
    items = [ConversationItem.model_validate(c) for c in convs]
    return Response.success(data=items)


@router.get("/conversations/{conv_id}")
def get_conversation_detail(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取某个会话的详细聊天记录"""
    conv = db.query(AIConversation).filter(
        AIConversation.id == conv_id,
        AIConversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return Response.success(data=ConversationDetail.model_validate(conv))


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除某个会话"""
    conv = db.query(AIConversation).filter(
        AIConversation.id == conv_id,
        AIConversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.delete(conv)
    db.commit()
    return Response.success(message="删除成功")