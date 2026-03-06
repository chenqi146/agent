package com.pg.platform.usermng.domain.mapper;

import com.pg.platform.usermng.domain.model.RoleEntity;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface RoleMapper {

    RoleEntity findById(Long id);

    RoleEntity findByRoleCode(String roleCode);

    int countAll();

    int countByKeyword(@Param("keyword") String keyword);

    List<RoleEntity> selectPage(@Param("offset") int offset, @Param("limit") int limit);

    List<RoleEntity> selectPageByKeyword(@Param("keyword") String keyword, @Param("offset") int offset, @Param("limit") int limit);

    int insert(RoleEntity entity);

    int update(RoleEntity entity);

    int deleteById(Long id);

    int countByRoleCode(@Param("roleCode") String roleCode);

    int countByRoleCodeExcludeId(@Param("roleCode") String roleCode, @Param("id") Long id);
}
