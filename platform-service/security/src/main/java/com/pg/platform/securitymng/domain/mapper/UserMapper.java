package com.pg.platform.securitymng.domain.mapper;

import com.pg.platform.securitymng.domain.model.user.User;

import java.util.Optional;

/**
 * 用户仓储接口（端口），由 {@link com.pg.platform.securitymng.infrastructure.persistence.UserMapperImpl} 实现
 */
public interface UserMapper {

    Optional<User> findByUsername(String username);
}
