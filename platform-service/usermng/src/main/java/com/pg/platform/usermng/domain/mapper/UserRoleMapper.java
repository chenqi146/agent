package com.pg.platform.usermng.domain.mapper;

import com.pg.platform.usermng.domain.model.UserRoleEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface UserRoleMapper {

    List<UserRoleEntity> findByUserId(Long userId);

    int deleteByUserId(Long userId);

    int deleteByRoleId(Long roleId);

    int insert(UserRoleEntity entity);

    int countByUserIdAndRoleId(@Param("userId") Long userId, @Param("roleId") Long roleId);
}
