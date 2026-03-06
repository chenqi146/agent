"""
用户上下文依赖：从请求头读取 user_id、token，供需要登录态的接口使用。
除 OpsController 外，其他 Controller 的接口均应注入本依赖。

- get_user_context: 仅校验请求头存在
- get_validated_user_context: 校验请求头 + 可选调用 security 校验 token 是否有效，并转发 user_id
"""

from typing import Annotated, Optional

import requests
from fastapi import Depends, Header, HTTPException, Request

# 请求头名称（与网关/前端约定一致）
HEADER_USER_ID = "x-user-id"
HEADER_AUTHORIZATION = "authorization"
BEARER_PREFIX = "Bearer "


class UserContext:
    """当前请求的用户信息（user_id + token）"""

    def __init__(self, user_id: str, token: str):
        self.user_id = user_id
        self.token = token


async def get_user_context(
    x_user_id: Annotated[Optional[str], Header(alias="X-User-Id")] = None,
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
) -> UserContext:
    """
    从请求头解析用户 ID 与 token。
    - 如果存在 X-API-Key，则仅校验 X-User-Id，允许 Authorization 为空
    - 否则 X-User-Id 和 Authorization 缺一不可
    """
    user_id = (x_user_id or "").strip()
    token = ""
    if authorization and authorization.startswith(BEARER_PREFIX):
        token = authorization[len(BEARER_PREFIX) :].strip()

    # 如果有 API Key，允许不传 Token，但必须传 X-User-Id
    if x_api_key and x_api_key.strip():
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": 401,
                    "message": "Missing user_id: require header X-User-Id when using API Key",
                },
            )
    else:
        if not user_id or not token:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": 401,
                    "message": "Missing user context: require header X-User-Id and Authorization: Bearer <token>",
                },
            )
    return UserContext(user_id=user_id, token=token)


async def get_validated_user_context(
    request: Request,
    user_ctx: UserContext = Depends(get_user_context),
) -> UserContext:
    """
    在 get_user_context 基础上，可选调用 security 服务校验 token 是否有效；
    校验通过后转发 user_id 供业务使用。
    配置 system.security.validate_url 时才会发起校验（如 http://localhost:19092/v1/agent/sso/validate）。
    """
    config = getattr(request.app.state, "config", None)
    if not config:
        return user_ctx
    
    # 如果没有 token (API Key 模式)，则跳过校验
    if not user_ctx.token:
        return user_ctx

    system = (config.get_system_config() or {}).get("security") or {}
    validate_url = (system.get("validate_url") or "").strip()
    if not validate_url:
        return user_ctx
    try:
        import time
        resp = requests.post(
            validate_url,
            json={
                "tag": "agent",
                "timestamp": int(time.time() * 1000),
                "data": {"token": user_ctx.token},
            },
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail={"code": 401, "message": "Token invalid or expired"},
            )
        data = resp.json()
        inner = (data.get("data") or data) if isinstance(data, dict) else {}
        if not inner.get("valid", False):
            raise HTTPException(
                status_code=401,
                detail={"code": 401, "message": "Token invalid or expired"},
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=401,
            detail={"code": 401, "message": "Token validation failed"},
        )
    return user_ctx
