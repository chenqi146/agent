package com.pg.platform.securitymng.application.event;

import com.pg.platform.securitymng.domain.event.UserLoggedInEvent;
import com.pg.platform.securitymng.domain.event.UserLoggedOutEvent;
import com.pg.platform.securitymng.infrastructure.client.rabbitmq.RabbitMqProducer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

/**
 * 用户登录/登出事件处理器：可发送 MQ 等
 */
@Component
public class UserEventHandler {

    private static final Logger log = LoggerFactory.getLogger(UserEventHandler.class);

    private final RabbitMqProducer rabbitMqProducer;

    @Autowired
    public UserEventHandler(RabbitMqProducer rabbitMqProducer) {
        this.rabbitMqProducer = rabbitMqProducer;
    }

    @Async
    @EventListener
    public void onUserLoggedIn(UserLoggedInEvent event) {
        log.info("User logged in: userId={}, username={}", event.getUserId(), event.getUsername());
        rabbitMqProducer.sendUserLoggedIn(event);
    }

    @Async
    @EventListener
    public void onUserLoggedOut(UserLoggedOutEvent event) {
        log.info("User logged out: userId={}, username={}", event.getUserId(), event.getUsername());
        rabbitMqProducer.sendUserLoggedOut(event);
    }
}
