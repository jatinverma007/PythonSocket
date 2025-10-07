from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from ..models.chat_room import ChatRoom
from ..models.message import Message
from ..models.message_read import MessageRead
from ..schemas.chat import ChatRoomCreate, MessageCreate, LastMessage
from typing import List, Dict, Optional, Any
from datetime import datetime


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
    
    def get_all_rooms_with_last_message(self, user_id: int = None) -> List[Dict[str, Any]]:
        """Get all rooms with their last message and unread count"""
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
                "last_message": None,
                "unread_count": 0
            }
            
            if last_message_obj:
                room_dict["last_message"] = {
                    "message_id": last_message_obj.id,
                    "sender": last_message_obj.sender.username,
                    "message": last_message_obj.content,
                    "message_type": last_message_obj.message_type,
                    "timestamp": last_message_obj.timestamp
                }
            
            # Get unread count for this room if user_id is provided
            if user_id:
                room_dict["unread_count"] = self.get_unread_count(room.id, user_id)
            
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
    
    def get_unread_count(self, room_id: int, user_id: int) -> int:
        """Get count of unread messages in a room for a specific user"""
        # Get all messages in the room that are not sent by the user
        # and that haven't been read by the user
        unread_count = self.db.query(Message).filter(
            and_(
                Message.room_id == room_id,
                Message.sender_id != user_id,  # Exclude user's own messages
                ~Message.id.in_(  # Messages not in the read list
                    self.db.query(MessageRead.message_id).filter(
                        MessageRead.user_id == user_id
                    )
                )
            )
        ).count()
        
        return unread_count
    
    def mark_messages_as_read(self, room_id: int, user_id: int) -> int:
        """Mark all unread messages in a room as read for a specific user"""
        # Get all messages in the room that haven't been read by this user
        unread_messages = self.db.query(Message).filter(
            and_(
                Message.room_id == room_id,
                Message.sender_id != user_id,  # Exclude user's own messages
                ~Message.id.in_(
                    self.db.query(MessageRead.message_id).filter(
                        MessageRead.user_id == user_id
                    )
                )
            )
        ).all()
        
        # Create read records for all unread messages
        read_count = 0
        for message in unread_messages:
            message_read = MessageRead(
                message_id=message.id,
                user_id=user_id,
                read_at=datetime.utcnow()
            )
            self.db.add(message_read)
            read_count += 1
        
        self.db.commit()
        return read_count
    
    def mark_message_as_read(self, message_id: int, user_id: int) -> bool:
        """Mark a specific message as read for a user"""
        # Check if already marked as read
        existing_read = self.db.query(MessageRead).filter(
            and_(
                MessageRead.message_id == message_id,
                MessageRead.user_id == user_id
            )
        ).first()
        
        if existing_read:
            return False  # Already marked as read
        
        # Check if message exists and user is not the sender
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message or message.sender_id == user_id:
            return False
        
        # Create read record
        message_read = MessageRead(
            message_id=message_id,
            user_id=user_id,
            read_at=datetime.utcnow()
        )
        self.db.add(message_read)
        self.db.commit()
        return True

