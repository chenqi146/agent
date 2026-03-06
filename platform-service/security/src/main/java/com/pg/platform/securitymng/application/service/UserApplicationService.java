package com.pg.platform.securitymng.application.service;

import com.pg.platform.securitymng.domain.model.user.User;
import com.pg.platform.securitymng.domain.model.user.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Optional;

/**
 * 用户应用服务：对外提供用户查询等
 */
@Service
public class UserApplicationService {

    private final UserService userService;

    @Autowired
    public UserApplicationService(UserService userService) {
        this.userService = userService;
    }

    public Optional<User> findByUsername(String username) {
        return userService.findByUsername(username);
    }
}
