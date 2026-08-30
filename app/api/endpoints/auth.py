from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.models import User
from app.schemas.schemas import RegisterRequest
from app.auth import hash_password, generate_verification_token
from app.email.email import send_verification_email
from app.schemas.schemas import LoginRequest, TokenResponse
from app.auth import verify_password, create_access_token
from app.dependencies import get_current_user


router = APIRouter(prefix="/api/auth", tags=["auth"])



@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


@router.post("/register")
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    token = generate_verification_token()

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        is_verified=False,
        verification_token=token
    )
    db.add(user)
    await db.commit()

    send_verification_email(data.email, token)

    return {"message": "Registration successful, check your email"}


@router.get("/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.verification_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.is_verified = True
    user.verification_token = None
    await db.commit()

    return {"message": "Email verified successfully"}


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token)