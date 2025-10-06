from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from typing import Dict, List
import asyncio
import logging
from datetime import datetime

from ..core.database import get_db
from ..core.security import verify_token
from ..schemas.chat import WebSocketMessage, ChatMessage
from ..services.chat_service import ChatService
from ..services.user_service import UserService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Dictionary to store active connections by room_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Dictionary to store user info for each connection
        self.connection_users: Dict[WebSocket, dict] = {}
        # Dictionary to store last ping time for each connection
        self.last_ping: Dict[WebSocket, datetime] = {}
        # Ping interval in seconds
        self.ping_interval = 30

    async def connect(self, websocket: WebSocket, room_id: int, user_info: dict):
        await websocket.accept()
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        
        self.active_connections[room_id].append(websocket)
        self.connection_users[websocket] = user_info
        self.last_ping[websocket] = datetime.now()
        
        logger.info(f"User {user_info['username']} connected to room {room_id}")
        
        # Notify others in the room that user joined
        await self.broadcast_to_room(room_id, {
            "type": "user_joined",
            "room_id": room_id,
            "sender": user_info["username"],
            "message": f"{user_info['username']} joined the chat",
            "timestamp": user_info["timestamp"]
        }, exclude_websocket=websocket)

    def disconnect(self, websocket: WebSocket):
        user_info = self.connection_users.get(websocket)
        if user_info:
            room_id = user_info.get("room_id")
            username = user_info.get("username")
            
            logger.info(f"User {username} disconnected from room {room_id}")
            
            if room_id and room_id in self.active_connections:
                try:
                    self.active_connections[room_id].remove(websocket)
                    if not self.active_connections[room_id]:
                        del self.active_connections[room_id]
                except ValueError:
                    pass  # Connection already removed
            
            # Clean up user info and ping tracking
            self.connection_users.pop(websocket, None)
            self.last_ping.pop(websocket, None)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")
            self.disconnect(websocket)

    async def broadcast_to_room(self, room_id: int, message: dict, exclude_websocket: WebSocket = None):
        logger.info(f"Broadcasting message to room {room_id}")
        logger.info(f"Active connections for room {room_id}: {len(self.active_connections.get(room_id, []))}")
        
        if room_id in self.active_connections:
            broken_connections = []
            connections_to_notify = [conn for conn in self.active_connections[room_id] if conn != exclude_websocket]
            logger.info(f"Notifying {len(connections_to_notify)} connections (excluding sender)")
            
            for connection in connections_to_notify:
                try:
                    await connection.send_text(json.dumps(message))
                    logger.info(f"Message sent to connection successfully")
                except Exception as e:
                    logger.warning(f"Failed to send message to connection: {e}")
                    broken_connections.append(connection)
            
            # Clean up broken connections
            for connection in broken_connections:
                logger.warning(f"Disconnecting broken connection")
                self.disconnect(connection)
        else:
            logger.warning(f"No active connections found for room {room_id}")

    async def send_ping(self, websocket: WebSocket):
        """Send ping to keep connection alive"""
        try:
            await websocket.send_text(json.dumps({"type": "ping", "timestamp": datetime.now().isoformat()}))
            self.last_ping[websocket] = datetime.now()
        except Exception as e:
            logger.warning(f"Failed to send ping: {e}")
            self.disconnect(websocket)

    async def handle_pong(self, websocket: WebSocket):
        """Handle pong response"""
        self.last_ping[websocket] = datetime.now()
        logger.debug("Received pong from client")

    async def cleanup_stale_connections(self):
        """Remove connections that haven't responded to pings"""
        current_time = datetime.now()
        stale_connections = []
        
        for websocket, last_ping_time in self.last_ping.items():
            if (current_time - last_ping_time).seconds > self.ping_interval * 2:
                stale_connections.append(websocket)
        
        for connection in stale_connections:
            logger.info("Removing stale connection")
            self.disconnect(connection)


manager = ConnectionManager()


async def get_current_user_from_token(token: str, db: Session):
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    user_service = UserService(db)
    user = user_service.get_user_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str):
    logger.info(f"WebSocket endpoint called with room_id={room_id}, token={token[:20]}...")
    
    # Get database session
    db = next(get_db())
    logger.info("Database session created")
    
    try:
        # Authenticate user
        logger.info("Starting user authentication")
        user = await get_current_user_from_token(token, db)
        logger.info(f"User authenticated: {user.username}")
        
        # Connect to room
        user_info = {
            "user_id": user.id,
            "username": user.username,
            "room_id": room_id,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"User info created: {user_info}")
        
        logger.info("Connecting to manager")
        await manager.connect(websocket, room_id, user_info)
        logger.info("Connected to manager successfully")
        
        # Verify room exists
        logger.info("Verifying room exists")
        chat_service = ChatService(db)
        room = chat_service.get_room_by_id(room_id)
        if not room:
            logger.warning("Room not found")
            await manager.send_personal_message({
                "type": "error",
                "message": "Room not found"
            }, websocket)
            await websocket.close()
            return
        
        logger.info(f"Room found: {room.name}")
        
        # Send welcome message
        logger.info("Sending welcome message")
        await manager.send_personal_message({
            "type": "connected",
            "room_id": room_id,
            "room_name": room.name,
            "message": f"Connected to {room.name}",
            "timestamp": user_info["timestamp"]
        }, websocket)
        logger.info("Welcome message sent")
        
        # Main message loop
        while True:
            try:
                # Handle different message types
                message = await websocket.receive()
                print(f"DEBUG: Received message type: {message.get('type')}")
                
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        data = message["text"]
                        print(f"DEBUG: Raw received data: {data}")
                        message_data = json.loads(data)
                        print(f"DEBUG: Parsed message data: {message_data}")
                    elif "bytes" in message:
                        data = message["bytes"].decode("utf-8")
                        print(f"DEBUG: Raw received bytes data: {data}")
                        message_data = json.loads(data)
                        print(f"DEBUG: Parsed message data: {message_data}")
                    else:
                        print(f"DEBUG: Unknown message format: {message}")
                        continue
                elif message["type"] == "websocket.disconnect":
                    print(f"DEBUG: WebSocket disconnected")
                    break
                else:
                    print(f"DEBUG: Unknown message type: {message['type']}")
                    continue
                
                if message_data.get("type") == "message":
                    print(f"DEBUG: Processing message type")
                    
                    # Check if content or file_url field exists
                    if "content" not in message_data and "file_url" not in message_data and "attachment" not in message_data:
                        print(f"DEBUG: Missing content, file_url, or attachment field. Keys: {list(message_data.keys())}")
                        await manager.send_personal_message({
                            "type": "error",
                            "message": f"Missing 'content', 'file_url', or 'attachment' field. Received: {list(message_data.keys())}"
                        }, websocket)
                        continue
                    
                    print(f"DEBUG: Content field found: {message_data.get('content')}")
                    print(f"DEBUG: File URL field found: {message_data.get('file_url')}")
                    print(f"DEBUG: Attachment field found: {message_data.get('attachment')}")
                    print(f"DEBUG: Complete message data: {message_data}")
                    
                    # Extract file data from attachment object if present
                    attachment = message_data.get("attachment", {})
                    file_url = message_data.get("file_url") or attachment.get("url")
                    file_name = message_data.get("file_name") or attachment.get("filename")
                    file_size = message_data.get("file_size") or attachment.get("size")
                    mime_type = message_data.get("mime_type") or attachment.get("mime_type")
                    
                    # Convert full URL to relative path if needed
                    if file_url and file_url.startswith("http"):
                        # Extract just the path part from full URL
                        import re
                        match = re.search(r'/api/files/([^/]+)', file_url)
                        if match:
                            file_url = f"/api/files/{match.group(1)}"
                    
                    print(f"DEBUG: Extracted file data - URL: {file_url}, Name: {file_name}, Size: {file_size}, MIME: {mime_type}")
                    
                    # Save message to database
                    from ..schemas.chat import MessageCreate
                    print(f"DEBUG: Creating MessageCreate object")
                    message_create = MessageCreate(
                        content=message_data.get("content"),
                        message_type=message_data.get("message_type", "text"),
                        file_url=file_url,
                        file_name=file_name,
                        file_size=file_size,
                        mime_type=mime_type,
                        room_id=room_id
                    )
                    print(f"DEBUG: MessageCreate created successfully")
                    
                    print(f"DEBUG: Calling chat_service.create_message")
                    saved_message = chat_service.create_message(message_create, user.id)
                    print(f"DEBUG: Message saved successfully: {saved_message.id}")
                    
                    # Get reactions for this message (will be empty for new messages)
                    from ..services.reaction_service import ReactionService
                    reaction_service = ReactionService(db)
                    reactions = reaction_service.get_message_reactions(saved_message.id)
                    
                    # Convert reactions to dict format
                    reactions_dict = [
                        {
                            "reaction_type": r.reaction_type,
                            "count": r.count,
                            "users": r.users
                        }
                        for r in reactions
                    ]
                    
                    # Broadcast message to all users in room
                    broadcast_message = {
                        "type": "message",
                        "room_id": room_id,
                        "message_id": saved_message.id,
                        "sender": user.username,
                        "message": saved_message.content,
                        "message_type": saved_message.message_type,
                        "file_url": saved_message.file_url,
                        "file_name": saved_message.file_name,
                        "file_size": saved_message.file_size,
                        "mime_type": saved_message.mime_type,
                        "timestamp": saved_message.timestamp.isoformat(),
                        "reactions": reactions_dict,
                        "user_reaction": None  # New messages don't have user reactions yet
                    }
                    logger.info(f"Broadcasting message: {broadcast_message}")
                    await manager.broadcast_to_room(room_id, broadcast_message, exclude_websocket=websocket)
                
                elif message_data.get("type") == "typing":
                    # Broadcast typing indicator
                    await manager.broadcast_to_room(room_id, {
                        "type": "typing",
                        "room_id": room_id,
                        "sender": user.username,
                        "message": f"{user.username} is typing...",
                        "timestamp": datetime.now().isoformat()
                    }, exclude_websocket=websocket)
                
                elif message_data.get("type") == "reaction":
                    # Handle message reaction
                    print(f"DEBUG: Processing reaction type")
                    
                    message_id = message_data.get("message_id")
                    reaction_type = message_data.get("reaction_type")
                    action = message_data.get("action", "add")  # "add" or "remove"
                    
                    if not message_id or not reaction_type:
                        await manager.send_personal_message({
                            "type": "error",
                            "message": "Missing message_id or reaction_type"
                        }, websocket)
                        continue
                    
                    try:
                        from ..services.reaction_service import ReactionService
                        from ..schemas.reaction import MessageReactionCreate
                        
                        reaction_service = ReactionService(db)
                        
                        if action == "add":
                            # Add or update reaction
                            reaction_data = MessageReactionCreate(
                                message_id=message_id,
                                reaction_type=reaction_type
                            )
                            reaction = reaction_service.add_reaction(reaction_data, user.id)
                            reaction_summary = reaction_service.get_message_reactions(message_id)
                            
                            # Broadcast reaction to all users in room
                            await manager.broadcast_to_room(room_id, {
                                "type": "reaction_added",
                                "room_id": room_id,
                                "message_id": message_id,
                                "sender": user.username,
                                "reaction_type": reaction_type,
                                "reaction_summary": [
                                    {
                                        "reaction_type": r.reaction_type,
                                        "count": r.count,
                                        "users": r.users
                                    } for r in reaction_summary
                                ],
                                "timestamp": datetime.now().isoformat()
                            })
                            
                        elif action == "remove":
                            # Remove reaction
                            success = reaction_service.remove_reaction(message_id, user.id)
                            if success:
                                reaction_summary = reaction_service.get_message_reactions(message_id)
                                
                                # Broadcast reaction removal to all users in room
                                await manager.broadcast_to_room(room_id, {
                                    "type": "reaction_removed",
                                    "room_id": room_id,
                                    "message_id": message_id,
                                    "sender": user.username,
                                    "reaction_type": reaction_type,
                                    "reaction_summary": [
                                        {
                                            "reaction_type": r.reaction_type,
                                            "count": r.count,
                                            "users": r.users
                                        } for r in reaction_summary
                                    ],
                                    "timestamp": datetime.now().isoformat()
                                })
                            else:
                                await manager.send_personal_message({
                                    "type": "error",
                                    "message": "Reaction not found"
                                }, websocket)
                        
                    except Exception as e:
                        print(f"DEBUG: Reaction error: {str(e)}")
                        await manager.send_personal_message({
                            "type": "error",
                            "message": f"Failed to process reaction: {str(e)}"
                        }, websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
            except Exception as e:
                print(f"DEBUG: Exception occurred: {str(e)}")
                print(f"DEBUG: Exception type: {type(e)}")
                if 'message_data' in locals():
                    print(f"DEBUG: Message data was: {message_data}")
                else:
                    print(f"DEBUG: Message data not available")
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                }, websocket)
    
    except HTTPException as e:
        print(f"DEBUG: HTTPException occurred: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail)
    except Exception as e:
        print(f"DEBUG: General exception occurred: {str(e)}")
        print(f"DEBUG: Exception type: {type(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
    finally:
        print(f"DEBUG: Cleaning up connection")
        manager.disconnect(websocket)
        db.close()
