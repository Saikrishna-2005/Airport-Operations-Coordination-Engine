from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.permissions import require_roles
from app.database.user_management import (
    get_all_users,
    update_user_role,
)


router = APIRouter(
    prefix="/admin",
    tags=["Admin User Management"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class UpdateUserRoleRequest(BaseModel):
    role: str = Field(pattern="^(admin|pilot|operator)$")


# ============================================================
# GET ALL REGISTERED USERS
# GET /admin/users
# ============================================================

@router.get("/users")
def list_registered_users(
    current_user: dict = Depends(require_roles("admin")),
):
    users = get_all_users()

    return {
        "success": True,
        "total_users": len(users),
        "users": users,
    }


# ============================================================
# UPDATE USER ROLE
# PATCH /admin/users/{user_id}/role
# ============================================================

@router.patch("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_user: dict = Depends(require_roles("admin")),
):
    result = update_user_role(
        target_user_id=user_id,
        new_role=request.role,
        acting_admin_id=current_user["user_id"],
    )

    if not result["success"]:
        reason = result["reason"]

        if reason == "User not found":
            code = status.HTTP_404_NOT_FOUND

        elif reason == "Administrator permission required":
            code = status.HTTP_403_FORBIDDEN

        elif reason == "Cannot demote the last administrator":
            code = status.HTTP_409_CONFLICT

        else:
            code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=code,
            detail=reason,
        )

    return result