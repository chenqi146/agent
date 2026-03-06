package com.pg.platform.securitymng.domain.model.token;

import com.pg.platform.securitymng.domain.mapper.TokenMapper;
import com.pg.platform.securitymng.domain.valueobject.TokenValue;
import com.pg.platform.securitymng.shared.exception.SsoException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Optional;

/**
 * Token 领域服务：签发、校验、失效
 */
@Service
public class TokenService {

    @Autowired
    private TokenMapper tokenMapper;


    public void save(Token token) {
        long ttl = token.getExpiresAt().getEpochSecond() - Instant.now().getEpochSecond();
        if (ttl <= 0) {
            throw new IllegalArgumentException("Token 已过期，无法保存");
        }
        tokenMapper.save(token, ttl);
    }

    public Optional<Token> findByValue(String tokenValue) {
        return tokenMapper.findByValue(tokenValue);
    }

    /** 校验 token 字符串：存在、未过期 */
    public Token validate(String tokenValue) {
        Token token = tokenMapper.findByValue(tokenValue)
                .orElseThrow(SsoException::tokenInvalid);
        if (token.isExpired()) {
            tokenMapper.deleteByValue(tokenValue);
            throw SsoException.tokenExpired();
        }
        return token;
    }

    public void invalidate(String tokenValue) {
        tokenMapper.deleteByValue(tokenValue);
    }

    public void invalidateByUserId(Long userId) {
        tokenMapper.deleteByUserId(userId);
    }

    public Token createToken(TokenValue value, Long userId, String username, Instant expiresAt) {
        return new Token(value, userId, username, expiresAt);
    }
}
