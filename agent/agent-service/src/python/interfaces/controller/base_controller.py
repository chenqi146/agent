"""
BaseController：所有需要用户登录态的 Controller 的基类。
- 通过 get_validated_user_context 依赖实现 token 是否有效（可选调用 security 校验）
- 将 user_id 注入到请求中，供子类在路由中通过 user_ctx.user_id 使用。
OpsController 不继承此类（运维接口无需用户信息）。
"""

from fastapi import Depends

from interfaces.deps.user_context import UserContext, get_validated_user_context


class BaseController:
    """
    基类控制器：提供统一的用户上下文依赖。
    子类在注册路由时使用 user_ctx: UserContext = Depends(get_validated_user_context)，
    即可获得已校验的 user_id 与 token，并用于业务（如 RAG 的 binding_user_id）。
    """

    # 供子类在路由中注入：Depends(get_validated_user_context)
    get_validated_user_context = get_validated_user_context

    @staticmethod
    def require_user_context():
        """返回依赖，供路由使用：Depends(BaseController.require_user_context())"""
        return Depends(get_validated_user_context)
