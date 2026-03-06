package com.pg.platform.usermng.domain.model;

import lombok.*;

import java.time.LocalDateTime;

/**
 * 用户角色关联表 user_role_tbl（MyBatis 实体）
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserRoleEntity {

    private Long id;
    private Long userId;
    private Long roleId;
    private LocalDateTime createTime;
    private String createBy;
}
