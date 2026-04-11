from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.auth.schemas import LoginRequest, Token, UserCreate, UserResponse
from app.auth.service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from app.database import get_session

from app.middleware import logger

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, session: Session = Depends(get_session)):
    logger.info(f"Attempting to register user: {user_data.username, user_data.email, 'password_hidden'}")
    if get_user_by_username(session, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    if get_user_by_email(session, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    return create_user(session, user_data)


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, session: Session = Depends(get_session)):
    """
    Retorna un token de acceso que debe incluirse en las peticiones subsecuentes
    como: Authorization: Bearer <token>
    """
    user = authenticate_user(session, login_data.email, login_data.password)
    logger.info(f"Login attempt for user: {login_data.email} - {'Success' if user else 'Failed'}")
    if not user:
        logger.info(f"Failed login attempt for user: {login_data.email}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_active_user)):
    return current_user
