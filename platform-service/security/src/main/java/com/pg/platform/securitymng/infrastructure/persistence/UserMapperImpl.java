package com.pg.platform.securitymng.infrastructure.persistence;

import com.pg.platform.securitymng.domain.mapper.UserMapper;
import com.pg.platform.securitymng.domain.model.user.User;
import com.pg.platform.securitymng.domain.valueobject.Password;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Optional;

/**
 * 用户仓储实现：委托 MyBatis，将 UserPO 转为领域 User
 */
@Repository
public class UserMapperImpl implements UserMapper {

    @Autowired
    private UserPersistenceMapper persistenceMapper;

    @Override
    public Optional<User> findByUsername(String username) {
        UserPO po = persistenceMapper.findByUsername(username);
        if (po == null) {
            return Optional.empty();
        }
        User user = new User(
                po.getId(),
                po.getUsername(),
                po.getPassword()
        );
        return Optional.of(user);
    }
}
