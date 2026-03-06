package com.pg.platform.securitymng.infrastructure.config;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;

/**
 * JWT 配置：提供签名密钥与解析器
 */
@Configuration
public class JwtConfig {

    @Value("${security.jwt.secret}")
    private String secret;

    @Bean
    public SecretKey jwtSigningKey() {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        if (keyBytes.length < 32) {
            throw new IllegalStateException("security.jwt.secret 至少需要 32 字节");
        }
        return Keys.hmacShaKeyFor(keyBytes);
    }
}
