package com.pg.platform.securitymng.domain.model.sso;

import com.pg.platform.securitymng.domain.model.token.Token;
import com.pg.platform.securitymng.domain.model.user.User;

/**
 * SSO 策略接口：由基础设施实现（如 JWT 签发/解析），领域只依赖此抽象
 */
public interface SsoStrategy {

    /**
     * 为用户签发 Token（如生成 JWT 并封装为 Token）
     */
    Token issueToken(User user, long expirationMs);

    /**
     * 从 token 字符串解析出 Token 聚合（不校验 Redis 是否存在，仅解析）
     */
    Token parseToken(String tokenValue);
}
