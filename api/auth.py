from datetime import timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from config import settings
from db.database import get_db
from models.user_models import User, Skill
from services.auth_service import AuthService
from exceptions import AuthenticationError, ConflictError, UserNotFoundError

router = APIRouter(prefix="/auth", tags=["authentication"])


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Optional[str] = None
    goals: Optional[str] = None
    industries: Optional[List[str]] = None
    skills: Optional[List[str]] = None


@router.post("/register", response_model=Token)
def register(user_in: UserRegister, db: Session = Depends(get_db)) -> Any:
    """
    Register a new user.
    """
    normalized_email = user_in.email.lower().strip()
    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )
    if user:
        raise ConflictError(message="User with this email already exists")
    
    hashed_password = AuthService.get_password_hash(user_in.password)
    
    # Map fields
    # role -> personality (or just store in interest/personality for now)
    # goals -> interest
    # industries -> (maybe append to interest?)
    
    interest = user_in.goals
    if user_in.industries:
        interest = f"{interest} | Industries: {', '.join(user_in.industries)}" if interest else f"Industries: {', '.join(user_in.industries)}"

    new_user = User(
        email=normalized_email,
        hashed_password=hashed_password,
        name=user_in.name,
        personality=user_in.role, # Mapping role to personality for now
        interest=interest
    )
    
    # Handle skills
    if user_in.skills:
        for skill_name in user_in.skills:
            skill = db.query(Skill).filter(Skill.name == skill_name).first()
            if not skill:
                skill = Skill(name=skill_name)
                db.add(skill)
            new_user.skills.append(skill)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = AuthService.create_access_token(subject=new_user.id)
    refresh_token = AuthService.create_refresh_token(subject=new_user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    normalized_email = form_data.username.lower().strip()
    user = (
        db.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .first()
    )
    if not user:
        raise AuthenticationError(message="Incorrect email or password")
    
    if not AuthService.verify_password(form_data.password, user.hashed_password):
        raise AuthenticationError(message="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthService.create_access_token(
        subject=user.id, expires_delta=access_token_expires
    )
    refresh_token = AuthService.create_refresh_token(subject=user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token
    }
