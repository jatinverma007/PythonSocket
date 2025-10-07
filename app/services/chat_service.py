from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.chat_room import ChatRoom
from ..models.message import Message
from ..schemas.chat import ChatRoomCreate, MessageCreate, LastMessage
from typing import List, Dict, Optional, Any


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
    
    def get_all_rooms_with_last_message(self) -> List[Dict[str, Any]]:
        """Get all rooms with their last message"""
        rooms = self.db.query(ChatRoom).order_by(ChatRoom.created_at.desc()).all()
        result = []
        
        for room in rooms:
            # Get the last message for this room
            last_message_obj = self.db.query(Message).filter(
                Message.room_id == room.id
            ).order_by(desc(Message.timestamp)).first()
            
            room_dict = {
                "id": room.id,
                "name": room.name,
                "created_at": room.created_at,
                "last_message": None
            }
            
            if last_message_obj:
                room_dict["last_message"] = {
                    "message_id": last_message_obj.id,
                    "sender": last_message_obj.sender.username,
                    "message": last_message_obj.content,
                    "message_type": last_message_obj.message_type,
                    "timestamp": last_message_obj.timestamp
                }
            
            result.append(room_dict)
        
        return result

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

