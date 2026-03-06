from fastapi import Header, HTTPException, Request
from typing import Optional

class UserContext:
    def __init__(self, user_id: str, token: str):
        self.user_id = user_id
        self.token = token

async def get_validated_user_context(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> UserContext:
    # Simplified implementation
    # In a real scenario, this would validate the token
    # For now, we extract user_id from headers or use a default
    user_id = request.headers.get("X-User-Id", "default_user")
    token = authorization or ""
    return UserContext(user_id=user_id, token=token)
