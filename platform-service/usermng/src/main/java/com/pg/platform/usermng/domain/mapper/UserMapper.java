package com.pg.platform.usermng.domain.mapper;

import com.pg.platform.usermng.domain.model.UserEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface UserMapper {

    UserEntity findById(Long id);

    UserEntity findByUsername(String username);

    int countAll();

    int countByKeyword(@Param("keyword") String keyword);

    List<UserEntity> selectPage(@Param("offset") int offset, @Param("limit") int limit);

    List<UserEntity> selectPageByKeyword(@Param("keyword") String keyword, @Param("offset") int offset, @Param("limit") int limit);

    int insert(UserEntity entity);

    int update(UserEntity entity);

    int deleteById(Long id);

    int countByUsername(@Param("username") String username);

    int countByUsernameExcludeId(@Param("username") String username, @Param("id") Long id);
}
