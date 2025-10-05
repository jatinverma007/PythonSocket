#!/usr/bin/env python3
"""
Script to create additional users for testing the chat application
"""
import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_user(username: str, password: str):
    """Create a new user with the given credentials"""
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists!")
            return False
        
        # Create new user
        hashed_password = get_password_hash(password)
        new_user = User(
            username=username,
            hashed_password=hashed_password
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"✅ Successfully created user: {username}")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 create_user.py <username> <password>")
        print("\nExample:")
        print("python3 create_user.py john doe123")
        return
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    print(f"Creating user '{username}'...")
    create_user(username, password)

if __name__ == "__main__":
    main()

