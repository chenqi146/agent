package com.pg.platform.usermng.domain.model;

import lombok.*;

import java.time.LocalDateTime;

/**
 * 角色表 role_tbl（MyBatis 实体）
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RoleEntity {

    private Long id;
    private String roleCode;
    private String roleName;
    private String upperLevelRoleCode;
    private String nextLevelRoleCode;
    private String description;
    @Builder.Default
    private Integer status = 1;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private String createBy;
    private String updateBy;
    private String remark;
}
