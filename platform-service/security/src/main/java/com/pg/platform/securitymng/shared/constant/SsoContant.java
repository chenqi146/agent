package com.pg.platform.securitymng.shared.constant;

/**
 * SSO 常量（类名保持 SsoContant 与现有文件一致）
 */
public final class SsoContant {
    private SsoContant() {}

    public static final String HEADER_AUTHORIZATION = "Authorization";
    public static final String BEARER_PREFIX = "Bearer ";
    public static final String CLAIM_USER_ID = "userId";
    public static final String CLAIM_USERNAME = "username";
    public static final String REDIS_TOKEN_PREFIX = "sso:token:";
    public static final String REDIS_USER_TOKEN_PREFIX = "sso:user:token:";
    /** 验证码 Redis 前缀 */
    public static final String REDIS_CAPTCHA_PREFIX = "sso:captcha:";
    /** 验证码过期时间（秒） */
    public static final long CAPTCHA_TTL_SECONDS = 60L;
};
