# Import all models to ensure they are registered with SQLAlchemy
from .user import User
from .chat_room import ChatRoom
from .message import Message

__all__ = ["User", "ChatRoom", "Message"]