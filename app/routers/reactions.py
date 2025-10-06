from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..schemas.reaction import (
    MessageReactionCreate,
    MessageReactionUpdate,
    ReactionResponse,
    MessageWithReactions,
    ReactionType
)
from ..schemas.user import User
from ..services.reaction_service import ReactionService
from .auth import get_current_user

router = APIRouter(prefix="/api/reactions", tags=["reactions"])


@router.post("/add", response_model=ReactionResponse)
async def add_reaction(
    reaction_data: MessageReactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add or update a reaction to a message"""
    try:
        reaction_service = ReactionService(db)
        reaction = reaction_service.add_reaction(reaction_data, current_user.id)
        
        # Get updated reaction summary
        reaction_summary = reaction_service.get_message_reactions(reaction_data.message_id)
        
        return ReactionResponse(
            success=True,
            message="Reaction added successfully",
            reaction=reaction,
            reaction_summary=reaction_summary
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add reaction: {str(e)}")


@router.delete("/remove/{message_id}", response_model=ReactionResponse)
async def remove_reaction(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a user's reaction from a message"""
    try:
        reaction_service = ReactionService(db)
        success = reaction_service.remove_reaction(message_id, current_user.id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Reaction not found")
        
        # Get updated reaction summary
        reaction_summary = reaction_service.get_message_reactions(message_id)
        
        return ReactionResponse(
            success=True,
            message="Reaction removed successfully",
            reaction=None,
            reaction_summary=reaction_summary
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove reaction: {str(e)}")


@router.get("/message/{message_id}", response_model=MessageWithReactions)
async def get_message_with_reactions(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a message with its reactions and current user's reaction"""
    reaction_service = ReactionService(db)
    message_with_reactions = reaction_service.get_message_with_reactions(message_id, current_user.id)
    
    if not message_with_reactions:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return message_with_reactions


@router.get("/room/{room_id}/messages", response_model=List[MessageWithReactions])
async def get_room_messages_with_reactions(
    room_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get messages in a room with their reactions"""
    reaction_service = ReactionService(db)
    messages_with_reactions = reaction_service.get_messages_with_reactions(
        room_id, current_user.id, limit
    )
    
    return messages_with_reactions


@router.get("/available", response_model=List[ReactionType])
async def get_available_reactions():
    """Get list of available reaction types"""
    reaction_service = ReactionService(None)  # No DB needed for this
    return reaction_service.get_available_reactions()


@router.get("/stats/{room_id}")
async def get_room_reaction_stats(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get reaction statistics for a room"""
    reaction_service = ReactionService(db)
    stats = reaction_service.get_reaction_stats(room_id)
    
    return {
        "room_id": room_id,
        "reaction_stats": stats,
        "total_reactions": sum(stats.values())
    }

