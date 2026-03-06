package com.pg.platform.securitymng.application.service;

import com.pg.platform.securitymng.application.command.LoginCommand;
import com.pg.platform.securitymng.application.command.LogoutCommand;
import com.pg.platform.securitymng.application.command.ValidateTokenCommand;
import com.pg.platform.securitymng.domain.event.UserLoggedInEvent;
import com.pg.platform.securitymng.domain.event.UserLoggedOutEvent;
import com.pg.platform.securitymng.domain.model.sso.SsoService;
import com.pg.platform.securitymng.domain.model.token.Token;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

/**
 * SSO 应用服务：编排登录/登出/校验，发布领域事件
 */
@Service
public class SsoApplicationService {

    private final SsoService ssoService;
    private final ApplicationEventPublisher eventPublisher;

    @Autowired
    public SsoApplicationService(SsoService ssoService, ApplicationEventPublisher eventPublisher) {
        this.ssoService = ssoService;
        this.eventPublisher = eventPublisher;
    }

    public Token login(LoginCommand command) {
        Token token = ssoService.login(command.getUsername(), command.getPassword());
        eventPublisher.publishEvent(new UserLoggedInEvent(token.getUserId(), token.getUsername()));
        return token;
    }

    public void logout(LogoutCommand command) {
        ssoService.logout(command.getToken());
        eventPublisher.publishEvent(new UserLoggedOutEvent(null, null));
    }

    public Token validateToken(ValidateTokenCommand command) {
        return ssoService.validateToken(command.getToken());
    }
}
