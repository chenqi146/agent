package com.pg.platform.securitymng.infrastructure.persistence;

import com.pg.platform.securitymng.domain.mapper.TokenMapper;
import com.pg.platform.securitymng.domain.model.token.Token;
import com.pg.platform.securitymng.domain.valueobject.TokenValue;
import com.pg.platform.securitymng.shared.constant.SsoContant;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Token 仓储 Redis 实现：token 存 Redis，支持按 userId 清理（单点登出）
 */
@Repository
public class TokenMapperImpl implements TokenMapper {

    private final StringRedisTemplate redis;

    @Autowired
    public TokenMapperImpl(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    public void save(Token token, long ttlSeconds) {
        String key = SsoContant.REDIS_TOKEN_PREFIX + token.getTokenValue().getValue();
        String value = token.getUserId() + ":" + token.getUsername() + ":" + token.getExpiresAt().getEpochSecond();
        redis.opsForValue().set(key, value, ttlSeconds, TimeUnit.SECONDS);
        String userTokenKey = SsoContant.REDIS_USER_TOKEN_PREFIX + token.getUserId();
        redis.opsForSet().add(userTokenKey, token.getTokenValue().getValue());
        redis.expire(userTokenKey, ttlSeconds, TimeUnit.SECONDS);
    }

    @Override
    public Optional<Token> findByValue(String tokenValue) {
        String key = SsoContant.REDIS_TOKEN_PREFIX + tokenValue;
        String value = redis.opsForValue().get(key);
        if (value == null) {
            return Optional.empty();
        }
        String[] parts = value.split(":", 3);
        if (parts.length != 3) {
            return Optional.empty();
        }
        try {
            Long userId = Long.parseLong(parts[0]);
            String username = parts[1];
            long expiresEpoch = Long.parseLong(parts[2]);
            return Optional.of(new Token(
                    new TokenValue(tokenValue),
                    userId,
                    username,
                    Instant.ofEpochSecond(expiresEpoch)
            ));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    @Override
    public void deleteByValue(String tokenValue) {
        Optional<Token> t = findByValue(tokenValue);
        t.ifPresent(token -> redis.opsForSet().remove(SsoContant.REDIS_USER_TOKEN_PREFIX + token.getUserId(), tokenValue));
        redis.delete(SsoContant.REDIS_TOKEN_PREFIX + tokenValue);
    }

    @Override
    public void deleteByUserId(Long userId) {
        String userTokenKey = SsoContant.REDIS_USER_TOKEN_PREFIX + userId;
        Set<String> tokens = redis.opsForSet().members(userTokenKey);
        if (tokens != null) {
            for (String tokenValue : tokens) {
                redis.delete(SsoContant.REDIS_TOKEN_PREFIX + tokenValue);
            }
        }
        redis.delete(userTokenKey);
    }
}
