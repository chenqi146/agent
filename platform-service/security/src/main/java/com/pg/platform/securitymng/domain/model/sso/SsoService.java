package com.pg.platform.securitymng.domain.model.sso;

import com.pg.platform.securitymng.domain.model.token.Token;
import com.pg.platform.securitymng.domain.model.token.TokenService;
import com.pg.platform.securitymng.domain.model.user.User;
import com.pg.platform.securitymng.domain.model.user.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * SSO 领域服务：协调用户认证与 Token 签发/校验
 */
@Service
public class SsoService {
    @Autowired
    private UserService userService;
    @Autowired
    private TokenService tokenService;
    @Autowired
    private SsoStrategy ssoStrategy;
    @Value("${security.jwt.expiration-ms:86400000}")
    private long tokenExpirationMs;


    /** 登录：校验用户并签发 Token，持久化到 Redis */
    public Token login(String username, String rawPassword) {
        User user = userService.authenticate(username, rawPassword);
        Token token = ssoStrategy.issueToken(user, tokenExpirationMs);
        tokenService.save(token);
        return token;
    }

    /** 校验 token 字符串（Redis + 过期），返回 Token 聚合 */
    public Token validateToken(String tokenValue) {
        return tokenService.validate(tokenValue);
    }

    /** 登出：使 token 失效 */
    public void logout(String tokenValue) {
        tokenService.invalidate(tokenValue);
    }

    /** 按用户 ID 使该用户所有 token 失效（单点登出） */
    public void logoutByUserId(Long userId) {
        tokenService.invalidateByUserId(userId);
    }
}
