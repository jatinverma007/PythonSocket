from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .database import Base
from ..models.user import User
from ..models.chat_room import ChatRoom
from ..core.security import get_password_hash

# Create all tables
Base.metadata.create_all(bind=engine)


def init_db():
    db = SessionLocal()
    
    try:
        # Create sample users if they don't exist
        if not db.query(User).filter(User.username == "admin").first():
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin123")
            )
            db.add(admin_user)
            print("Created admin user")
        
        if not db.query(User).filter(User.username == "user1").first():
            user1 = User(
                username="user1",
                hashed_password=get_password_hash("password123")
            )
            db.add(user1)
            print("Created user1")
        
        if not db.query(User).filter(User.username == "user2").first():
            user2 = User(
                username="user2",
                hashed_password=get_password_hash("password123")
            )
            db.add(user2)
            print("Created user2")
        
        # Create sample chat rooms if they don't exist
        if not db.query(ChatRoom).filter(ChatRoom.name == "General").first():
            general_room = ChatRoom(name="General")
            db.add(general_room)
            print("Created General chat room")
        
        if not db.query(ChatRoom).filter(ChatRoom.name == "Random").first():
            random_room = ChatRoom(name="Random")
            db.add(random_room)
            print("Created Random chat room")
        
        if not db.query(ChatRoom).filter(ChatRoom.name == "Tech Talk").first():
            tech_room = ChatRoom(name="Tech Talk")
            db.add(tech_room)
            print("Created Tech Talk chat room")
        
        db.commit()
        print("Database initialized successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()




