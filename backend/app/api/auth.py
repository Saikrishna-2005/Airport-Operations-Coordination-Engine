from fastapi import APIRouter, HTTPException, status
from fastapi import Depends
from app.core.dependencies import get_current_user
from app.core.permissions import require_roles

from app.core.security import (
    create_access_token,
    verify_password
)

from app.database.database import get_user_by_username

from app.schemas.auth import (
    LoginRequest,
    TokenResponse
)

import sqlite3
from uuid import uuid4

from fastapi import HTTPException, status

from app.database.database import create_user

from app.schemas.auth import SignupRequest


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(request: LoginRequest):

    user = get_user_by_username(request.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    password_valid = verify_password(
        request.password,
        user["hashed_password"]
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        user_id=user["user_id"],
        role=user["role"]
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )

@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "message": "Authentication successful",
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "role": current_user["role"]
    }
    
@router.get("/admin-only")
def admin_only(
    current_user: dict = Depends(require_roles("admin"))
):
    return {
        "message": "Admin access granted",
        "username": current_user["username"],
        "role": current_user["role"]
    }

# ============================================================
# DYNAMIC USER SIGNUP
# POST /auth/signup
# ============================================================

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(request: SignupRequest):

    # Step 1: Normalize username
    username = request.username.strip()

    # Step 2: Check whether username already exists
    existing_user = get_user_by_username(username)

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )

    # Step 3: Generate unique user ID
    user_id = f"USR-{uuid4().hex[:12].upper()}"

    # Step 4: Assign restricted default role
    role = "operator"

    # Step 5: Save user in SQLite
    # create_user() hashes the password automatically.
    try:
        create_user(
            user_id=user_id,
            username=username,
            password=request.password,
            role=role
        )

    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )

    # Step 6: Return signup confirmation
    return {
        "success": True,
        "message": "Account created successfully",
        "user_id": user_id,
        "username": username,
        "role": role
    }