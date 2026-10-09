from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Moderator

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_moderator(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Moderator:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate moderator credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    moderator = db.query(Moderator).filter(Moderator.username == username).first()
    if moderator is None:
        raise credentials_exception
    return moderator

def seed_default_moderator(db: Session):
    """Ensures at least one administrator/moderator account exists."""
    existing = db.query(Moderator).filter(Moderator.username == settings.DEFAULT_ADMIN_USERNAME).first()
    if not existing:
        admin = Moderator(
            username=settings.DEFAULT_ADMIN_USERNAME,
            hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
            role="ADMIN"
        )
        db.add(admin)
        db.commit()
