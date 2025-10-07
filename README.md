# Python FastAPI Chat Backend

A real-time chat application backend built with FastAPI, WebSocket, JWT authentication, and SQLAlchemy.

## Features

- **Real-time messaging** using WebSocket
- **JWT-based authentication** for secure user sessions
- **REST API** for chat history and room management
- **SQLite database** (easily configurable for PostgreSQL)
- **CORS support** for frontend/iOS integration
- **Auto-generated API documentation** with Swagger

## Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation & Running

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python run.py
   ```

3. **The application will start on:** `http://localhost:8000`

## API Documentation

### Base URL
```
http://localhost:8000
```

### Authentication Endpoints

#### Register User
```http
POST /api/auth/signup
Content-Type: application/json

{
  "username": "testuser",
  "password": "password123"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer YOUR_JWT_TOKEN
```

### Chat Room Endpoints

#### Get All Rooms
```http
GET /api/rooms
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Create Room
```http
POST /api/rooms
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "name": "My New Room"
}
```

#### Get Room Details
```http
GET /api/rooms/{room_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

### Message Endpoints

#### Get Chat History
```http
GET /api/messages/{room_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Get Recent Messages
```http
GET /api/messages/{room_id}/recent?limit=50
Authorization: Bearer YOUR_JWT_TOKEN
```

### WebSocket Connection

#### Connect to Chat Room
```
ws://localhost:8000/ws/chat/{room_id}?token={jwt_token}
```

#### WebSocket Message Format

**Send Message:**
```json
{
  "type": "message",
  "content": "Hello, world!"
}
```

**Send Typing Indicator:**
```json
{
  "type": "typing"
}
```

**Receive Messages:**
```json
{
  "type": "message",
  "room_id": 1,
  "sender": "username",
  "message": "Hello, world!",
  "timestamp": "2024-01-01T12:00:00"
}
```

## Sample Data

### Pre-created Users
- **Username:** `admin`, **Password:** `admin123`
- **Username:** `user1`, **Password:** `password123`
- **Username:** `user2`, **Password:** `password123`

### Pre-created Rooms
- General
- Random
- Tech Talk

## Swift UI Integration

### 1. Authentication Flow

```swift
// Register user
func registerUser(username: String, password: String) async throws {
    let url = URL(string: "http://localhost:8000/api/auth/signup")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body = ["username": username, "password": password]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)
    
    let (_, response) = try await URLSession.shared.data(for: request)
    // Handle response
}

// Login
func login(username: String, password: String) async throws -> String {
    let url = URL(string: "http://localhost:8000/api/auth/login")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body = ["username": username, "password": password]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)
    
    let (data, _) = try await URLSession.shared.data(for: request)
    let response = try JSONDecoder().decode(LoginResponse.self, from: data)
    return response.accessToken
}
```

### 2. WebSocket Connection

```swift
import Network

class ChatWebSocket: ObservableObject {
    private var webSocketTask: URLSessionWebSocketTask?
    @Published var messages: [ChatMessage] = []
    
    func connect(roomId: Int, token: String) {
        let url = URL(string: "ws://localhost:8000/ws/chat/\(roomId)?token=\(token)")!
        webSocketTask = URLSession.shared.webSocketTask(with: url)
        webSocketTask?.resume()
        
        receiveMessage()
    }
    
    func sendMessage(_ content: String) {
        let message = [
            "type": "message",
            "content": content
        ]
        
        let data = try! JSONSerialization.data(withJSONObject: message)
        webSocketTask?.send(.data(data)) { error in
            if let error = error {
                print("Error sending message: \(error)")
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
}
```

### 3. Data Models

```swift
struct LoginResponse: Codable {
    let accessToken: String
    let tokenType: String
    
    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

struct ChatMessage: Codable {
    let type: String
    let roomId: Int
    let sender: String
    let message: String
    let timestamp: String
    
    enum CodingKeys: String, CodingKey {
        case type
        case roomId = "room_id"
        case sender
        case message
        case timestamp
    }
}

struct ChatRoom: Codable {
    let id: Int
    let name: String
    let createdAt: String
    
    enum CodingKeys: String, CodingKey {
        case id
        case name
        case createdAt = "created_at"
    }
}
```

## Testing

### 1. API Documentation
Visit: `http://localhost:8000/docs`

### 2. Test WebSocket
Visit: `http://localhost:8000/test`

### 3. Health Check
```http
GET /health
```

## Configuration

### Environment Variables
Create a `.env` file:
```
DATABASE_URL=sqlite:///./chat.db
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Database
The application uses SQLite by default. To use PostgreSQL:
1. Install `psycopg2-binary` in requirements.txt
2. Update `DATABASE_URL` in `.env` file
3. Update database configuration in `app/core/config.py`

## Project Structure

```
app/
├── core/           # Configuration and utilities
├── models/         # SQLAlchemy models
├── routers/        # API endpoints
├── schemas/        # Pydantic schemas
├── services/       # Business logic
├── websocket/      # WebSocket handlers
└── main.py         # FastAPI application
```

## Development

### Running in Development Mode
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migration
The application automatically creates tables on startup. For production, consider using Alembic for migrations.

## Production Deployment

1. Set strong `SECRET_KEY` in environment variables
2. Use PostgreSQL or MySQL for production database
3. Configure proper CORS origins
4. Use a reverse proxy (nginx) for production
5. Enable HTTPS for WebSocket connections




