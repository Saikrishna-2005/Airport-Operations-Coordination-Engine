import sqlite3

from app.database.connection import get_db_connection


# ============================================================
# GET ALL REGISTERED USERS
# ============================================================

def get_all_users():

    connection = get_db_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                user_id,
                username,
                role,
                created_at
            FROM users
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ============================================================
# UPDATE USER ROLE
# ============================================================

def update_user_role(
    target_user_id: str,
    new_role: str,
    acting_admin_id: str,
):

    allowed_roles = {"admin", "pilot", "operator"}

    if new_role not in allowed_roles:
        return {
            "success": False,
            "reason": "Invalid role",
        }

    connection = get_db_connection()

    try:
        # Start a write transaction to protect role changes.
        connection.execute("BEGIN IMMEDIATE")

        # Verify the acting user is still an admin.
        admin = connection.execute(
            """
            SELECT role
            FROM users
            WHERE user_id = ?
            """,
            (acting_admin_id,),
        ).fetchone()

        if admin is None or admin["role"] != "admin":
            connection.rollback()
            return {
                "success": False,
                "reason": "Administrator permission required",
            }

        # Find the target user.
        target = connection.execute(
            """
            SELECT user_id, username, role
            FROM users
            WHERE user_id = ?
            """,
            (target_user_id,),
        ).fetchone()

        if target is None:
            connection.rollback()
            return {
                "success": False,
                "reason": "User not found",
            }

        # Prevent demoting the last remaining admin.
        if target["role"] == "admin" and new_role != "admin":

            admin_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE role = 'admin'
                """
            ).fetchone()[0]

            if admin_count <= 1:
                connection.rollback()
                return {
                    "success": False,
                    "reason": "Cannot demote the last administrator",
                }

        # Update the role.
        connection.execute(
            """
            UPDATE users
            SET role = ?
            WHERE user_id = ?
            """,
            (new_role, target_user_id),
        )

        connection.commit()

        return {
            "success": True,
            "message": "User role updated successfully",
            "user_id": target_user_id,
            "username": target["username"],
            "old_role": target["role"],
            "new_role": new_role,
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()