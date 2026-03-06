package com.pg.platform.securitymng.domain.mapper;

import com.pg.platform.securitymng.domain.model.token.Token;

import java.util.Optional;

/**
 * Token 仓储接口（端口），由 {@link com.pg.platform.securitymng.infrastructure.persistence.TokenMapperImpl} 实现
 */
public interface TokenMapper {

    void save(Token token, long ttlSeconds);

    Optional<Token> findByValue(String tokenValue);

    void deleteByValue(String tokenValue);

    void deleteByUserId(Long userId);
}
