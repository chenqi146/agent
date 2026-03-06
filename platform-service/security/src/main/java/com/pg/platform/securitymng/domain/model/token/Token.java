package com.pg.platform.securitymng.domain.model.token;

import com.pg.platform.securitymng.domain.valueobject.TokenValue;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Token 聚合根：与用户关联的访问令牌
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Token {

    private TokenValue tokenValue;
    private Long userId;
    private String username;
    private Instant expiresAt;

    public boolean isExpired() {
        return Instant.now().isAfter(expiresAt);
    }
}

