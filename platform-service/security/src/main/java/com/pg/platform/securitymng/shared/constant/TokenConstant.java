package com.pg.platform.securitymng.shared.constant;

/**
 * Token 常量
 */
public final class TokenConstant {
    private TokenConstant() {}

    /** Token 在 Redis 中的默认过期时间（秒），与 JWT 过期一致时由配置覆盖 */
    public static final long DEFAULT_TTL_SECONDS = 86400L;
}
