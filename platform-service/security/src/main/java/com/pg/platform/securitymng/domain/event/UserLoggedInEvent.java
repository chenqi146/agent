package com.pg.platform.securitymng.domain.event;

import lombok.Getter;

import java.time.Instant;

/**
 * 用户登录成功领域事件
 */
@Getter
public class UserLoggedInEvent {

    private final Long userId;
    private final String username;
    private final Instant at;

    public UserLoggedInEvent(Long userId, String username) {
        this.userId = userId;
        this.username = username;
        this.at = Instant.now();
    }
}
