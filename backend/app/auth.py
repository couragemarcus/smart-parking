from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.parking import User, VisitorSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user

async def get_current_security(user: User = Depends(get_current_user)) -> User:
    if user.role not in ["admin", "security"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user

def verify_device_credentials(x_device_id: str = Header(None), x_device_secret: str = Header(None)):
    if x_device_id != settings.DEVICE_ID or x_device_secret != settings.DEVICE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid device credentials")
    return True

async def get_visitor_session(
    x_visitor_token: Optional[str] = Header(None), 
    token: Optional[str] = None, 
    db: AsyncSession = Depends(get_db)
) -> VisitorSession:
    token_to_check = x_visitor_token or token
    if not token_to_check:
        raise HTTPException(status_code=401, detail="Visitor token missing")
    result = await db.execute(select(VisitorSession).where(VisitorSession.token == token_to_check))
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid visitor token")
    return session
