"""Account management service — delete account functionality."""

import logging

from app.db.session import get_db
from app.services import auth_service

logger = logging.getLogger(__name__)


def delete_account(user_id: int, password: str) -> dict:
    """
    Delete a user account after verifying the password.

    Args:
        user_id: The ID of the user to delete.
        password: The user's current password for authorization.

    Returns:
        dict with status: "ok", "invalid_password", or "not_found"
    """
    conn = get_db()
    cursor = conn.cursor()

    # SELECT the row to get password hash for verification
    cursor.execute("SELECT id, username, password FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        logger.warning(f"Delete account: user_id={user_id} not found")
        return {"status": "not_found"}

    # Verify the password using auth_service (bcrypt)
    if not auth_service.verify_password(password, row["password"]):
        logger.info(f"Delete account: invalid password for user_id={user_id}")
        return {"status": "invalid_password"}

    # Delete the user row
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()

    logger.info(f"Account deleted: user_id={user_id}")
    return {"status": "ok"}