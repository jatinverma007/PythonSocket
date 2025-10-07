from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime

from ..core.database import get_db
from ..schemas.chat import ChatRoom, ChatRoomCreate, Message, MessageCreate, ChatMessage, ChatMessageWithReactions, FileUploadResponse, ImageUploadResponse, ChatRoomWithLastMessage
from ..models.message_type import MessageType
from ..schemas.user import User
from ..services.chat_service import ChatService
from .auth import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/rooms", response_model=List[ChatRoomWithLastMessage])
async def get_rooms(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chat_service = ChatService(db)
    return chat_service.get_all_rooms_with_last_message(user_id=current_user.id)


@router.post("/rooms", response_model=ChatRoom)
async def create_room(room: ChatRoomCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chat_service = ChatService(db)
    return chat_service.create_room(room)


@router.get("/rooms/{room_id}", response_model=ChatRoom)
async def get_room(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    chat_service = ChatService(db)
    room = chat_service.get_room_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.get("/messages/{room_id}", response_model=List[ChatMessageWithReactions])
async def get_messages(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..services.reaction_service import ReactionService
    
    chat_service = ChatService(db)
    reaction_service = ReactionService(db)
    
    # Check if room exists
    room = chat_service.get_room_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    messages = chat_service.get_messages_by_room(room_id)
    result = []
    
    for msg in messages:
        # Get reactions for this message
        reactions = reaction_service.get_message_reactions(msg.id)
        user_reaction = reaction_service.get_user_reaction(msg.id, current_user.id)
        
        # Convert reactions to dict format
        reactions_dict = [
            {
                "reaction_type": r.reaction_type,
                "count": r.count,
                "users": r.users
            }
            for r in reactions
        ]
        
        result.append(ChatMessageWithReactions(
            message_id=msg.id,
            room_id=msg.room_id,
            sender=msg.sender.username,
            message=msg.content,
            message_type=msg.message_type,
            file_url=msg.file_url,
            file_name=msg.file_name,
            file_size=msg.file_size,
            mime_type=msg.mime_type,
            timestamp=msg.timestamp,
            reactions=reactions_dict,
            user_reaction=user_reaction
        ))
    
    return result


@router.get("/messages/{room_id}/recent", response_model=List[ChatMessageWithReactions])
async def get_recent_messages(room_id: int, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ..services.reaction_service import ReactionService
    
    chat_service = ChatService(db)
    reaction_service = ReactionService(db)
    
    # Check if room exists
    room = chat_service.get_room_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    messages = chat_service.get_recent_messages(room_id, limit)
    result = []
    
    for msg in reversed(messages):  # Reverse to get chronological order
        # Get reactions for this message
        reactions = reaction_service.get_message_reactions(msg.id)
        user_reaction = reaction_service.get_user_reaction(msg.id, current_user.id)
        
        # Convert reactions to dict format
        reactions_dict = [
            {
                "reaction_type": r.reaction_type,
                "count": r.count,
                "users": r.users
            }
            for r in reactions
        ]
        
        result.append(ChatMessageWithReactions(
            message_id=msg.id,
            room_id=msg.room_id,
            sender=msg.sender.username,
            message=msg.content,
            message_type=msg.message_type,
            file_url=msg.file_url,
            file_name=msg.file_name,
            file_size=msg.file_size,
            mime_type=msg.mime_type,
            timestamp=msg.timestamp,
            reactions=reactions_dict,
            user_reaction=user_reaction
        ))
    
    return result


@router.post("/upload-file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file size (10MB limit)
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    # Determine file type and message type
    mime_type = file.content_type or "application/octet-stream"
    
    # Determine message type based on MIME type
    if mime_type.startswith('image/'):
        message_type = MessageType.IMAGE
        upload_dir = "uploads/images"
    elif mime_type.startswith('video/'):
        message_type = MessageType.VIDEO
        upload_dir = "uploads/videos"
    elif mime_type.startswith('audio/'):
        message_type = MessageType.AUDIO
        upload_dir = "uploads/audio"
    else:
        message_type = MessageType.DOCUMENT
        upload_dir = "uploads/documents"
    
    # Generate unique filename
    file_extension = os.path.splitext(file.filename or "file")[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Create uploads directory if it doesn't exist
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_dir, unique_filename)
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # Return the file URL
    file_url = f"/api/files/{unique_filename}"
    
    return FileUploadResponse(
        file_url=file_url,
        filename=unique_filename,
        file_size=file_size,
        mime_type=mime_type,
        message="File uploaded successfully"
    )


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Use the generic upload function
    file_upload = await upload_file(file, db, current_user)
    
    return ImageUploadResponse(
        image_url=file_upload.file_url,
        filename=file_upload.filename,
        message="Image uploaded successfully"
    )


@router.get("/files/{filename}")
async def get_file(filename: str):
    """Generic file serving endpoint that searches all upload directories"""
    upload_dirs = ["uploads/images", "uploads/videos", "uploads/audio", "uploads/documents"]
    
    for upload_dir in upload_dirs:
        file_path = os.path.join(upload_dir, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/images/{filename}")
async def get_image(filename: str):
    """Backward compatibility endpoint for images"""
    file_path = os.path.join("uploads/images", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(file_path)


@router.post("/rooms/{room_id}/mark-read")
async def mark_room_as_read(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark all messages in a room as read for the current user"""
    chat_service = ChatService(db)
    
    # Check if room exists
    room = chat_service.get_room_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Mark all messages as read
    read_count = chat_service.mark_messages_as_read(room_id, current_user.id)
    
    return {
        "message": f"Marked {read_count} messages as read",
        "read_count": read_count
    }

