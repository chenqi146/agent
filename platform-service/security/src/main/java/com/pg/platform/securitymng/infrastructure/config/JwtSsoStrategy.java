package com.pg.platform.securitymng.infrastructure.config;

import com.pg.platform.securitymng.domain.model.sso.SsoStrategy;
import com.pg.platform.securitymng.domain.model.token.Token;
import com.pg.platform.securitymng.domain.model.user.User;
import com.pg.platform.securitymng.domain.valueobject.TokenValue;
import com.pg.platform.securitymng.shared.constant.SsoContant;
import com.pg.platform.securitymng.shared.exception.SsoException;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.SignatureException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.util.Date;

/**
 * 基于 JWT 的 SSO 策略实现
 */
@Component
public class JwtSsoStrategy implements SsoStrategy {

    private final SecretKey signingKey;
    private final long defaultExpirationMs;

    @Autowired
    public JwtSsoStrategy(
            SecretKey jwtSigningKey,
            @Value("${security.jwt.expiration-ms:86400000}") long defaultExpirationMs) {
        this.signingKey = jwtSigningKey;
        this.defaultExpirationMs = defaultExpirationMs;
    }

    @Override
    public Token issueToken(User user, long expirationMs) {
        long now = System.currentTimeMillis();
        Date exp = new Date(now + expirationMs);
        String jws = Jwts.builder()
                .subject(user.getUsername())
                .claim(SsoContant.CLAIM_USER_ID, user.getId())
                .claim(SsoContant.CLAIM_USERNAME, user.getUsername())
                .issuedAt(new Date(now))
                .expiration(exp)
                .signWith(signingKey)
                .compact();
        return new Token(
                new TokenValue(jws),
                user.getId(),
                user.getUsername(),
                exp.toInstant()
        );
    }

    @Override
    public Token parseToken(String tokenValue) {
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(tokenValue)
                    .getPayload();
            Long userId = claims.get(SsoContant.CLAIM_USER_ID, Long.class);
            String username = claims.get(SsoContant.CLAIM_USERNAME, String.class);
            if (userId == null || username == null) {
                throw SsoException.tokenInvalid();
            }
            Date exp = claims.getExpiration();
            return new Token(new TokenValue(tokenValue), userId, username, exp.toInstant());
        } catch (ExpiredJwtException e) {
            throw SsoException.tokenExpired();
        } catch (SignatureException | IllegalArgumentException e) {
            throw SsoException.tokenInvalid();
        }
    }
}
