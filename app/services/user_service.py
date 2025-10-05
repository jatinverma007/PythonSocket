from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..models.user import User
from ..schemas.user import UserCreate
from ..core.security import get_password_hash, verify_password, create_refresh_token, verify_refresh_token
from ..core.config import settings


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user: UserCreate) -> User:
        hashed_password = get_password_hash(user.password)
        db_user = User(username=user.username, hashed_password=hashed_password)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_user_by_username(self, username: str) -> User:
        return self.db.query(User).filter(User.username == username).first()

    def get_user_by_id(self, user_id: int) -> User:
        return self.db.query(User).filter(User.id == user_id).first()

    def authenticate_user(self, username: str, password: str) -> User:
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def user_exists(self, username: str) -> bool:
        return self.db.query(User).filter(User.username == username).first() is not None

    def store_refresh_token(self, user: User, refresh_token: str) -> None:
        """Store refresh token and expiration time for user"""
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        user.refresh_token = refresh_token
        user.refresh_token_expires = expires_at
        self.db.commit()

    def get_user_by_refresh_token(self, refresh_token: str) -> User:
        """Get user by refresh token if it's valid and not expired"""
        user = self.db.query(User).filter(
            User.refresh_token == refresh_token,
            User.refresh_token_expires > datetime.utcnow()
        ).first()
        return user

    def revoke_refresh_token(self, user: User) -> None:
        """Revoke refresh token for user"""
        user.refresh_token = None
        user.refresh_token_expires = None
        self.db.commit()

