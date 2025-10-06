from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict
from collections import defaultdict

from ..models.message_reaction import MessageReaction
from ..models.message import Message
from ..models.user import User
from ..schemas.reaction import (
    MessageReactionCreate, 
    MessageReactionUpdate, 
    ReactionSummary,
    MessageWithReactions,
    ReactionType
)


class ReactionService:
    def __init__(self, db: Session):
        self.db = db

    def add_reaction(self, reaction_data: MessageReactionCreate, user_id: int) -> MessageReaction:
        """Add or update a reaction to a message"""
        # Check if message exists
        message = self.db.query(Message).filter(Message.id == reaction_data.message_id).first()
        if not message:
            raise ValueError("Message not found")

        # Check if user already reacted to this message
        existing_reaction = self.db.query(MessageReaction).filter(
            MessageReaction.message_id == reaction_data.message_id,
            MessageReaction.user_id == user_id
        ).first()

        if existing_reaction:
            # Update existing reaction
            existing_reaction.reaction_type = reaction_data.reaction_type
            self.db.commit()
            self.db.refresh(existing_reaction)
            return existing_reaction
        else:
            # Create new reaction
            new_reaction = MessageReaction(
                message_id=reaction_data.message_id,
                user_id=user_id,
                reaction_type=reaction_data.reaction_type
            )
            self.db.add(new_reaction)
            self.db.commit()
            self.db.refresh(new_reaction)
            return new_reaction

    def remove_reaction(self, message_id: int, user_id: int) -> bool:
        """Remove a user's reaction from a message"""
        reaction = self.db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id
        ).first()

        if reaction:
            self.db.delete(reaction)
            self.db.commit()
            return True
        return False

    def get_message_reactions(self, message_id: int) -> List[ReactionSummary]:
        """Get all reactions for a specific message grouped by reaction type"""
        reactions = self.db.query(
            MessageReaction.reaction_type,
            func.count(MessageReaction.id).label('count'),
            func.group_concat(User.username).label('usernames')
        ).join(
            User, MessageReaction.user_id == User.id
        ).filter(
            MessageReaction.message_id == message_id
        ).group_by(
            MessageReaction.reaction_type
        ).all()

        reaction_summaries = []
        for reaction_type, count, usernames in reactions:
            username_list = usernames.split(',') if usernames else []
            reaction_summaries.append(ReactionSummary(
                reaction_type=reaction_type,
                count=count,
                users=username_list
            ))

        return reaction_summaries

    def get_user_reaction(self, message_id: int, user_id: int) -> Optional[ReactionType]:
        """Get a specific user's reaction to a message"""
        reaction = self.db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == user_id
        ).first()

        return reaction.reaction_type if reaction else None

    def get_message_with_reactions(self, message_id: int, current_user_id: int) -> Optional[MessageWithReactions]:
        """Get a message with its reactions and current user's reaction"""
        message = self.db.query(Message).filter(Message.id == message_id).first()
        if not message:
            return None

        # Get all reactions for this message
        reactions = self.get_message_reactions(message_id)
        
        # Get current user's reaction
        user_reaction = self.get_user_reaction(message_id, current_user_id)

        return MessageWithReactions(
            id=message.id,
            content=message.content,
            message_type=message.message_type,
            file_url=message.file_url,
            file_name=message.file_name,
            file_size=message.file_size,
            mime_type=message.mime_type,
            room_id=message.room_id,
            sender_id=message.sender_id,
            sender_username=message.sender.username,
            timestamp=message.timestamp,
            reactions=reactions,
            user_reaction=user_reaction
        )

    def get_messages_with_reactions(self, room_id: int, current_user_id: int, limit: int = 50) -> List[MessageWithReactions]:
        """Get messages in a room with their reactions"""
        messages = self.db.query(Message).filter(
            Message.room_id == room_id
        ).order_by(
            Message.timestamp.desc()
        ).limit(limit).all()

        messages_with_reactions = []
        for message in messages:
            # Get all reactions for this message
            reactions = self.get_message_reactions(message.id)
            
            # Get current user's reaction
            user_reaction = self.get_user_reaction(message.id, current_user_id)

            messages_with_reactions.append(MessageWithReactions(
                id=message.id,
                content=message.content,
                message_type=message.message_type,
                file_url=message.file_url,
                file_name=message.file_name,
                file_size=message.file_size,
                mime_type=message.mime_type,
                room_id=message.room_id,
                sender_id=message.sender_id,
                sender_username=message.sender.username,
                timestamp=message.timestamp,
                reactions=reactions,
                user_reaction=user_reaction
            ))

        return messages_with_reactions

    def get_reaction_stats(self, room_id: int) -> Dict[str, int]:
        """Get reaction statistics for a room"""
        stats = self.db.query(
            MessageReaction.reaction_type,
            func.count(MessageReaction.id).label('count')
        ).join(
            Message, MessageReaction.message_id == Message.id
        ).filter(
            Message.room_id == room_id
        ).group_by(
            MessageReaction.reaction_type
        ).all()

        return {reaction_type: count for reaction_type, count in stats}

    def get_available_reactions(self) -> List[ReactionType]:
        """Get list of available reaction types"""
        return [reaction_type for reaction_type in ReactionType]

