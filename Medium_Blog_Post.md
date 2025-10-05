# Building a Real-Time Chat Application with FastAPI and WebSocket: A Complete Guide

*Learn how to build a production-ready chat application with real-time messaging, file uploads, and JWT authentication*

---

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture Overview](#architecture-overview)
3. [Project Setup](#project-setup)
4. [Database Models](#database-models)
5. [Authentication System](#authentication-system)
6. [WebSocket Implementation](#websocket-implementation)
7. [File Upload System](#file-upload-system)
8. [API Endpoints](#api-endpoints)
9. [Frontend Integration](#frontend-integration)
10. [Testing and Deployment](#testing-and-deployment)
11. [Conclusion](#conclusion)

---

## Introduction

In today's digital world, real-time communication is essential for modern applications. Whether you're building a customer support system, team collaboration tool, or social platform, having a robust chat system can significantly enhance user experience.

In this comprehensive guide, we'll build a complete real-time chat application using:
- **FastAPI** - Modern, fast web framework for building APIs
- **WebSocket** - Real-time bidirectional communication
- **SQLAlchemy** - Python SQL toolkit and ORM
- **JWT Authentication** - Secure token-based authentication
- **File Upload Support** - Handle images, videos, audio, and documents

By the end of this tutorial, you'll have a fully functional chat application that can handle multiple chat rooms, real-time messaging, file uploads, and secure authentication.

---

## Architecture Overview

Our chat application follows a clean, modular architecture:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   iOS/Web       │    │   FastAPI       │    │   SQLite        │
│   Client        │◄──►│   Backend       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   File Storage  │
│   Connection    │    │   (uploads/)    │
└─────────────────┘    └─────────────────┘
```

### Key Components:
- **REST API**: Handle authentication, room management, and message history
- **WebSocket**: Real-time message broadcasting
- **Database**: Store users, rooms, and messages
- **File System**: Store uploaded media files
- **JWT Tokens**: Secure authentication and authorization

---

## Project Setup

### 1. Create Project Structure

```bash
mkdir chat-app
cd chat-app
mkdir -p app/{core,models,routers,schemas,services,websocket}
mkdir uploads/{images,videos,audio,documents}
```

### 2. Install Dependencies

Create `requirements.txt`:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
websockets==12.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create `.env` file:
```env
DATABASE_URL=sqlite:///./chat.db
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Database Models

### 1. User Model (`app/models/user.py`)

```python
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    refresh_token = Column(Text, nullable=True)
    refresh_token_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    messages = relationship("Message", back_populates="sender", lazy="dynamic")
```

### 2. Chat Room Model (`app/models/chat_room.py`)

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    messages = relationship("Message", back_populates="room", lazy="dynamic")
```

### 3. Message Model (`app/models/message.py`)

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
from .message_type import MessageType

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=True)  # Made nullable for media-only messages
    message_type = Column(String, default=MessageType.TEXT)
    file_url = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Foreign Keys
    room_id = Column(Integer, ForeignKey("chat_rooms.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", back_populates="messages")
```

### 4. Message Type Enum (`app/models/message_type.py`)

```python
from enum import Enum

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
```

---

## Authentication System

### 1. Security Configuration (`app/core/security.py`)

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def create_refresh_token() -> str:
    return jwt.encode(
        {"exp": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)},
        settings.secret_key,
        algorithm=settings.algorithm
    )
```

### 2. Authentication Router (`app/routers/auth.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta

from ..core.database import get_db
from ..core.security import create_access_token, verify_token, create_refresh_token
from ..core.config import settings
from ..schemas.user import UserCreate, UserLogin, Token, User, TokenRefresh
from ..services.user_service import UserService

router = APIRouter(prefix="/api/auth", tags=["authentication"])
security = HTTPBearer()

@router.post("/signup", response_model=dict)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    user_service = UserService(db)
    
    if user_service.user_exists(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    user_service.create_user(user)
    return {"message": "User registered successfully"}

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user_service = UserService(db)
    user = user_service.authenticate_user(
        user_credentials.username, 
        user_credentials.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    # Create and store refresh token
    refresh_token = create_refresh_token()
    user_service.store_refresh_token(user, refresh_token)
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
```

---

## WebSocket Implementation

### 1. Connection Manager (`app/websocket/chat.py`)

```python
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

    async def broadcast_to_room(self, room_id: int, message: dict, exclude_websocket: WebSocket = None):
        if room_id in self.active_connections:
            broken_connections = []
            connections_to_notify = [
                conn for conn in self.active_connections[room_id] 
                if conn != exclude_websocket
            ]
            
            for connection in connections_to_notify:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send message to connection: {e}")
                    broken_connections.append(connection)
            
            # Clean up broken connections
            for connection in broken_connections:
                self.disconnect(connection)

manager = ConnectionManager()
```

### 2. WebSocket Endpoint

```python
async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str):
    # Get database session
    db = next(get_db())
    
    try:
        # Authenticate user
        user = await get_current_user_from_token(token, db)
        
        # Connect to room
        user_info = {
            "user_id": user.id,
            "username": user.username,
            "room_id": room_id,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.connect(websocket, room_id, user_info)
        
        # Verify room exists
        chat_service = ChatService(db)
        room = chat_service.get_room_by_id(room_id)
        if not room:
            await manager.send_personal_message({
                "type": "error",
                "message": "Room not found"
            }, websocket)
            await websocket.close()
            return
        
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "room_id": room_id,
            "room_name": room.name,
            "message": f"Connected to {room.name}",
            "timestamp": user_info["timestamp"]
        }, websocket)
        
        # Main message loop
        while True:
            try:
                message = await websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        data = message["text"]
                        message_data = json.loads(data)
                    elif "bytes" in message:
                        data = message["bytes"].decode("utf-8")
                        message_data = json.loads(data)
                    else:
                        continue
                elif message["type"] == "websocket.disconnect":
                    break
                else:
                    continue
                
                if message_data.get("type") == "message":
                    # Save message to database
                    message_create = MessageCreate(
                        content=message_data.get("content"),
                        message_type=message_data.get("message_type", "text"),
                        file_url=message_data.get("file_url"),
                        file_name=message_data.get("file_name"),
                        file_size=message_data.get("file_size"),
                        mime_type=message_data.get("mime_type"),
                        room_id=room_id
                    )
                    
                    saved_message = chat_service.create_message(message_create, user.id)
                    
                    # Broadcast message to all users in room
                    broadcast_message = {
                        "type": "message",
                        "room_id": room_id,
                        "sender": user.username,
                        "message": saved_message.content,
                        "message_type": saved_message.message_type,
                        "file_url": saved_message.file_url,
                        "file_name": saved_message.file_name,
                        "file_size": saved_message.file_size,
                        "mime_type": saved_message.mime_type,
                        "timestamp": saved_message.timestamp.isoformat()
                    }
                    
                    await manager.broadcast_to_room(room_id, broadcast_message, exclude_websocket=websocket)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format"
                }, websocket)
            except Exception as e:
                await manager.send_personal_message({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                }, websocket)
    
    except Exception as e:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
    finally:
        manager.disconnect(websocket)
        db.close()
```

---

## File Upload System

### 1. File Upload Endpoint (`app/routers/chat.py`)

```python
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
```

### 2. File Serving Endpoint

```python
@router.get("/files/{filename}")
async def get_file(filename: str):
    """Generic file serving endpoint that searches all upload directories"""
    upload_dirs = ["uploads/images", "uploads/videos", "uploads/audio", "uploads/documents"]
    
    for upload_dir in upload_dirs:
        file_path = os.path.join(upload_dir, filename)
        if os.path.exists(file_path):
            return FileResponse(file_path)
    
    raise HTTPException(status_code=404, detail="File not found")
```

---

## API Endpoints

### 1. Main Application (`app/main.py`)

```python
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from .core.database import engine, Base
from .core.config import settings
from .routers import auth, chat
from .websocket.chat import websocket_endpoint
from .models import User, ChatRoom, Message

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Chat Backend API",
    description="Real-time chat application with WebSocket support",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)

@app.websocket("/ws/chat/{room_id}")
async def websocket_route(websocket: WebSocket, room_id: int, token: str = Query(...)):
    await websocket_endpoint(websocket, room_id, token)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### 2. Available Endpoints

**Authentication:**
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user info

**Chat Rooms:**
- `GET /api/rooms` - Get all chat rooms
- `POST /api/rooms` - Create new chat room
- `GET /api/rooms/{room_id}` - Get specific room

**Messages:**
- `GET /api/messages/{room_id}` - Get all messages in room
- `GET /api/messages/{room_id}/recent` - Get recent messages

**File Upload:**
- `POST /api/upload-file` - Upload any file type
- `POST /api/upload-image` - Upload image specifically
- `GET /api/files/{filename}` - Serve uploaded files

**WebSocket:**
- `WS /ws/chat/{room_id}?token={jwt_token}` - Real-time chat connection

---

## Frontend Integration

### 1. JavaScript WebSocket Client

```javascript
class ChatClient {
    constructor(serverUrl, token) {
        this.serverUrl = serverUrl;
        this.token = token;
        this.websocket = null;
        this.roomId = null;
    }

    connect(roomId) {
        this.roomId = roomId;
        const wsUrl = `ws://${this.serverUrl}/ws/chat/${roomId}?token=${this.token}`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
            console.log('Connected to chat room');
        };

        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.websocket.onclose = () => {
            console.log('Disconnected from chat room');
        };

        this.websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    sendMessage(content, messageType = 'text') {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const message = {
                type: 'message',
                content: content,
                message_type: messageType
            };
            this.websocket.send(JSON.stringify(message));
        }
    }

    sendFileMessage(fileUrl, fileName, fileSize, mimeType, messageType) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const message = {
                type: 'message',
                file_url: fileUrl,
                file_name: fileName,
                file_size: fileSize,
                mime_type: mimeType,
                message_type: messageType
            };
            this.websocket.send(JSON.stringify(message));
        }
    }

    handleMessage(data) {
        switch (data.type) {
            case 'message':
                this.displayMessage(data);
                break;
            case 'user_joined':
                this.displaySystemMessage(data.message);
                break;
            case 'connected':
                this.displaySystemMessage(data.message);
                break;
            case 'error':
                console.error('Server error:', data.message);
                break;
        }
    }

    displayMessage(data) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message';
        
        if (data.message_type === 'text') {
            messageElement.innerHTML = `
                <strong>${data.sender}:</strong> ${data.message}
                <small>${new Date(data.timestamp).toLocaleTimeString()}</small>
            `;
        } else {
            messageElement.innerHTML = `
                <strong>${data.sender} sent a ${data.message_type}:</strong>
                <a href="${data.file_url}" target="_blank">${data.file_name}</a>
                <small>${new Date(data.timestamp).toLocaleTimeString()}</small>
            `;
        }
        
        document.getElementById('messages').appendChild(messageElement);
    }

    displaySystemMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'system-message';
        messageElement.textContent = message;
        document.getElementById('messages').appendChild(messageElement);
    }
}
```

### 2. Swift iOS Integration

```swift
import Network

class ChatWebSocket: ObservableObject {
    private var webSocketTask: URLSessionWebSocketTask?
    @Published var messages: [ChatMessage] = []
    private let serverUrl: String
    private let token: String
    
    init(serverUrl: String, token: String) {
        self.serverUrl = serverUrl
        self.token = token
    }
    
    func connect(roomId: Int) {
        let url = URL(string: "ws://\(serverUrl)/ws/chat/\(roomId)?token=\(token)")!
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        
        receiveMessage()
    }
    
    func sendMessage(_ content: String) {
        let message = [
            "type": "message",
            "content": content,
            "message_type": "text"
        ]
        
        let data = try! JSONSerialization.data(withJSONObject: message)
        webSocketTask?.send(.data(data)) { error in
            if let error = error {
                print("Error sending message: \(error)")
            }
        }
    }
    
    func sendFileMessage(fileUrl: String, fileName: String, fileSize: Int, mimeType: String, messageType: String) {
        let message = [
            "type": "message",
            "file_url": fileUrl,
            "file_name": fileName,
            "file_size": fileSize,
            "mime_type": mimeType,
            "message_type": messageType
        ]
        
        let data = try! JSONSerialization.data(withJSONObject: message)
        webSocketTask?.send(.data(data)) { error in
            if let error = error {
                print("Error sending file message: \(error)")
            }
        }
    }
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .success(let message):
                switch message {
                case .data(let data):
                    if let chatMessage = try? JSONDecoder().decode(ChatMessage.self, from: data) {
                        DispatchQueue.main.async {
                            self?.messages.append(chatMessage)
                        }
                    }
                case .string(let text):
                    if let data = text.data(using: .utf8),
                       let chatMessage = try? JSONDecoder().decode(ChatMessage.self, from: data) {
                        DispatchQueue.main.async {
                            self?.messages.append(chatMessage)
                        }
                    }
                @unknown default:
                    break
                }
                self?.receiveMessage()
            case .failure(let error):
                print("WebSocket error: \(error)")
            }
        }
    }
    
    func disconnect() {
        webSocketTask?.cancel()
    }
}
```

---

## Testing and Deployment

### 1. Running the Application

Create `run.py`:

```python
#!/usr/bin/env python3
"""
Startup script for the Chat Backend API
"""
import uvicorn
from app.core.init_db import init_db

if __name__ == "__main__":
    # Initialize database with sample data
    print("Initializing database...")
    init_db()
    
    # Start the server
    print("Starting Chat Backend API server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
```

Run the application:
```bash
python run.py
```

### 2. Testing with cURL

**Register a user:**
```bash
curl -X POST "http://localhost:8000/api/auth/signup" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "password123"}'
```

**Login:**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "password123"}'
```

**Get chat rooms:**
```bash
curl -X GET "http://localhost:8000/api/rooms" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. WebSocket Testing

Visit `http://localhost:8000/test` for a simple HTML test page.

### 4. Production Deployment

**Docker Setup:**

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  chat-app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./chat.db:/app/chat.db
    environment:
      - DATABASE_URL=sqlite:///./chat.db
      - SECRET_KEY=your-production-secret-key
```

---

## Conclusion

Congratulations! You've built a complete real-time chat application with the following features:

✅ **Real-time messaging** using WebSocket  
✅ **JWT authentication** with refresh tokens  
✅ **File upload support** for images, videos, audio, and documents  
✅ **Multiple chat rooms** with room management  
✅ **Message history** and recent messages  
✅ **CORS support** for frontend integration  
✅ **Auto-generated API documentation**  
✅ **Production-ready** with proper error handling  

### Key Takeaways:

1. **FastAPI** provides excellent performance and automatic API documentation
2. **WebSocket** enables real-time bidirectional communication
3. **JWT tokens** offer secure, stateless authentication
4. **SQLAlchemy ORM** simplifies database operations
5. **Modular architecture** makes the code maintainable and scalable

### Next Steps:

- Add message encryption for enhanced security
- Implement user presence indicators
- Add message reactions and replies
- Create a mobile app using the same backend
- Add push notifications for mobile devices
- Implement message search functionality
- Add user roles and permissions

This chat application serves as a solid foundation that you can extend with additional features based on your specific requirements. The modular design makes it easy to add new functionality while maintaining code quality and performance.

---

*Happy coding! 🚀*

**GitHub Repository:** [Link to your repository]  
**Live Demo:** [Link to your demo]  
**API Documentation:** `http://your-server:8000/docs`
