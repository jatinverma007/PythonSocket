from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from .core.database import engine, Base
from .core.config import settings
from .routers import auth, chat, reactions
from .websocket.chat import websocket_endpoint
from .models import User, ChatRoom, Message, MessageRead  # Import all models

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
app.include_router(reactions.router)


@app.get("/")
async def root():
    return {
        "message": "Chat Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": f"/ws/chat/{{room_id}}?token={{jwt_token}}"
    }


@app.websocket("/ws/chat/{room_identifier}")
async def websocket_route(websocket: WebSocket, room_identifier: str, token: str = Query(...)):
    """WebSocket endpoint that accepts either room_id (int) or room_name (str)"""
    from .core.database import get_db
    from .services.chat_service import ChatService
    
    # Determine if room_identifier is an ID or a name
    room_id = None
    
    # Try to parse as integer first
    try:
        room_id = int(room_identifier)
    except ValueError:
        # It's a room name, look it up
        db = next(get_db())
        try:
            chat_service = ChatService(db)
            rooms = chat_service.get_all_rooms()
            
            # Find room by name (case-insensitive)
            room_name_lower = room_identifier.lower()
            for room in rooms:
                if room.name.lower() == room_name_lower:
                    room_id = room.id
                    break
            
            if room_id is None:
                # Room not found
                await websocket.close(code=1008, reason=f"Room '{room_identifier}' not found")
                return
        finally:
            db.close()
    
    await websocket_endpoint(websocket, room_id, token)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Sample HTML page for testing WebSocket
@app.get("/test", response_class=HTMLResponse)
async def test_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chat Test</title>
    </head>
    <body>
        <h1>Chat Test Page</h1>
        <div id="messages"></div>
        <input type="text" id="messageInput" placeholder="Type a message...">
        <button onclick="sendMessage()">Send</button>
        <script>
            const roomId = 1;
            const token = "YOUR_JWT_TOKEN_HERE"; // Replace with actual token
            const ws = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}?token=${token}`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const messages = document.getElementById('messages');
                messages.innerHTML += `<div>${data.sender}: ${data.message}</div>`;
            };
            
            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value;
                if (message) {
                    ws.send(JSON.stringify({
                        type: "message",
                        content: message
                    }));
                    input.value = '';
                }
            }
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
