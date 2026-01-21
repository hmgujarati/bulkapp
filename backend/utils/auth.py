"""Authentication utilities"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path
import bcrypt
import jwt
import os

from models.schemas import TokenData, Role
from utils.database import db

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Security configuration
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Super admin email - cannot be deleted or paused
SUPER_ADMIN_EMAIL = os.environ.get('SUPER_ADMIN_EMAIL', 'bizchatapi@gmail.com')


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create a JWT access token"""
    expiration = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        'userId': user_id,
        'email': email,
        'role': role,
        'exp': expiration
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get the current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_data = TokenData(
            userId=payload['userId'],
            email=payload['email'],
            role=payload['role']
        )
        
        # Check if user exists and is not paused
        user = await db.users.find_one({"id": user_data.userId})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get('isPaused', False):
            raise HTTPException(status_code=403, detail="Account is paused")
        
        return user_data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require admin role for access"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
