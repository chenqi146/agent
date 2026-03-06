package com.pg.platform.securitymng.domain.model.user;

import com.pg.platform.securitymng.domain.mapper.UserMapper;
import com.pg.platform.securitymng.shared.exception.SsoException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Optional;

/**
 * 用户领域服务：按用户名查找并校验
 */
@Service
public class UserService {

    @Autowired
    private UserMapper userMapper;

    public Optional<User> findByUsername(String username) {
        return userMapper.findByUsername(username);
    }

    /** 校验用户名与明文密码，成功返回用户，失败抛出 SSO 异常 */
    public User authenticate(String username, String rawPassword) {
        User user = userMapper.findByUsername(username)
                .orElseThrow(SsoException::invalidCredentials);


        if (!user.checkPassword(rawPassword)) {
            throw SsoException.invalidCredentials();
        }
        return user;
    }
}
