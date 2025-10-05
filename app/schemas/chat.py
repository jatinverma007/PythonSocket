from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from ..models.message_type import MessageType


class ChatRoomBase(BaseModel):
    name: str


class ChatRoomCreate(ChatRoomBase):
    pass


class ChatRoom(ChatRoomBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessageBase(BaseModel):
    content: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None


class MessageCreate(MessageBase):
    room_id: int


class Message(MessageBase):
    id: int
    room_id: int
    sender_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    room_id: int
    sender: str
    message: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    timestamp: datetime


class WebSocketMessage(BaseModel):
    type: str  # "message", "join", "typing"
    room_id: int
    content: Optional[str] = None
    sender: Optional[str] = None
    message_type: Optional[MessageType] = MessageType.TEXT
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None


class FileUploadResponse(BaseModel):
    file_url: str
    filename: str
    file_size: int
    mime_type: str
    message: str


# Keep ImageUploadResponse for backward compatibility
class ImageUploadResponse(BaseModel):
    image_url: str
    filename: str
    message: str