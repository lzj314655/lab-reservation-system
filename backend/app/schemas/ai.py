from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MessageItem(BaseModel):
    role: str
    content: str

    class Config:
        from_attributes = True

class ConversationItem(BaseModel):
    id: int
    title: str
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationDetail(ConversationItem):
    messages: List[MessageItem]

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    # 👇 必须加上这个字段，接收前端传来的历史会话 ID
    conversation_id: Optional[int] = None 