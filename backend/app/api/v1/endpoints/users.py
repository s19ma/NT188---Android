from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import (
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.api.v1.endpoints.auth import send_verification_code

router = APIRouter(prefix="/users", tags=["Users"])


# 1. Register
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản người dùng mới",
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    normalized_email = user_in.email.strip().lower()

    # Kiểm tra email tồn tại (không phân biệt hoa thường)
    stmt = select(User).where(func.lower(User.email) == normalized_email)
    existing_user = db.scalar(stmt)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(user_in.password),
        display_name=user_in.display_name,
        native_language=user_in.native_language,
        target_language=user_in.target_language,
        cefr_level=user_in.cefr_level,
        email_verified=False,
    )

    try:
        db.add(user)
        db.flush()
        send_verification_code(user, db)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    return user


# 2. Login (OAuth2 Form: username = email)
@router.post(
    "/login",
    response_model=Token,
    summary="Đăng nhập lấy Access Token (JWT)",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    normalized_email = form_data.username.strip().lower()

    stmt = select(User).where(func.lower(User.email) == normalized_email)
    user = db.scalar(stmt)

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Email verification required")

    access_token = create_access_token(user.id)
    return Token(access_token=access_token, token_type="bearer")


# 3. Get profile
@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin tài khoản hiện tại",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


# 4. Update profile
@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Cập nhật thông tin hồ sơ của tài khoản hiện tại",
)
def update_me(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = user_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


# 5. Delete account
@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa tài khoản hiện tại",
)
def delete_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.delete(current_user)
    db.commit()
    return None
