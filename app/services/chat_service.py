from sqlalchemy.orm import Session
from ..models.chat_room import ChatRoom
from ..models.message import Message
from ..schemas.chat import ChatRoomCreate, MessageCreate
from typing import List


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def create_room(self, room: ChatRoomCreate) -> ChatRoom:
        db_room = ChatRoom(name=room.name)
        self.db.add(db_room)
        self.db.commit()
        self.db.refresh(db_room)
        return db_room

    def get_room_by_id(self, room_id: int) -> ChatRoom:
        return self.db.query(ChatRoom).filter(ChatRoom.id == room_id).first()

    def get_all_rooms(self) -> List[ChatRoom]:
        return self.db.query(ChatRoom).order_by(ChatRoom.created_at.desc()).all()

    def create_message(self, message: MessageCreate, sender_id: int) -> Message:
        db_message = Message(
            content=message.content,
            message_type=message.message_type,
            file_url=message.file_url,
            file_name=message.file_name,
            file_size=message.file_size,
            mime_type=message.mime_type,
            room_id=message.room_id,
            sender_id=sender_id
        )
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def get_messages_by_room(self, room_id: int) -> List[Message]:
        return self.db.query(Message).filter(Message.room_id == room_id).order_by(Message.timestamp.asc()).all()

    def get_recent_messages(self, room_id: int, limit: int = 50) -> List[Message]:
        return self.db.query(Message).filter(Message.room_id == room_id).order_by(Message.timestamp.desc()).limit(limit).all()

