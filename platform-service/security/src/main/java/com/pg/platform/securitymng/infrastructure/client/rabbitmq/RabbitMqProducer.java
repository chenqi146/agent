package com.pg.platform.securitymng.infrastructure.client.rabbitmq;

import com.pg.platform.securitymng.domain.event.UserLoggedInEvent;
import com.pg.platform.securitymng.domain.event.UserLoggedOutEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * 用户登录/登出 MQ 发送（当前为占位实现，仅打日志；接入 Rabbit 后可在此发送消息）
 */
@Component
public class RabbitMqProducer {

    private static final Logger log = LoggerFactory.getLogger(RabbitMqProducer.class);

    public void sendUserLoggedIn(UserLoggedInEvent event) {
        log.debug("MQ sendUserLoggedIn: userId={}, username={}", event.getUserId(), event.getUsername());
        // 接入 RabbitMQ 后: rabbitTemplate.convertAndSend("sso.exchange", "user.logged.in", event);
    }

    public void sendUserLoggedOut(UserLoggedOutEvent event) {
        log.debug("MQ sendUserLoggedOut: userId={}, username={}", event.getUserId(), event.getUsername());
        // 接入 RabbitMQ 后: rabbitTemplate.convertAndSend("sso.exchange", "user.logged.out", event);
    }
}
