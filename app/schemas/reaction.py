from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class ReactionType(str, Enum):
    """Supported reaction types like WhatsApp"""
    THUMBS_UP = "👍"
    HEART = "❤️"
    LAUGH = "😂"
    SURPRISED = "😮"
    SAD = "😢"
    ANGRY = "😡"


class MessageReactionBase(BaseModel):
    reaction_type: ReactionType


class MessageReactionCreate(MessageReactionBase):
    message_id: int


class MessageReactionUpdate(MessageReactionBase):
    pass


class MessageReaction(MessageReactionBase):
    id: int
    message_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageReactionWithUser(BaseModel):
    """Reaction with user information for display"""
    id: int
    reaction_type: ReactionType
    user_id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReactionSummary(BaseModel):
    """Summary of reactions for a message"""
    reaction_type: ReactionType
    count: int
    users: List[str]  # List of usernames who reacted


class MessageWithReactions(BaseModel):
    """Message with reaction summary"""
    id: int
    content: Optional[str] = None
    message_type: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    room_id: int
    sender_id: int
    sender_username: str
    timestamp: datetime
    reactions: List[ReactionSummary] = []
    user_reaction: Optional[ReactionType] = None  # Current user's reaction

    class Config:
        from_attributes = True


class ReactionResponse(BaseModel):
    """Response for reaction operations"""
    success: bool
    message: str
    reaction: Optional[MessageReaction] = None
    reaction_summary: Optional[List[ReactionSummary]] = None

