package com.pg.platform.securitymng.domain.event;

import lombok.Getter;

import java.time.Instant;

/**
 * 用户登出领域事件
 */
@Getter
public class UserLoggedOutEvent {

    private final Long userId;
    private final String username;
    private final Instant at;

    public UserLoggedOutEvent(Long userId, String username) {
        this.userId = userId;
        this.username = username;
        this.at = Instant.now();
    }
}
