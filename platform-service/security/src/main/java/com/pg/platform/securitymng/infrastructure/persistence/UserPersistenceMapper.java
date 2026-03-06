package com.pg.platform.securitymng.infrastructure.persistence;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * MyBatis 用户表 Mapper
 */
@Mapper
public interface UserPersistenceMapper {

    UserPO findByUsername(@Param("username") String username);
}
