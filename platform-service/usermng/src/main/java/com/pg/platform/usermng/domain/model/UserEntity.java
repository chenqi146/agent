package com.pg.platform.usermng.domain.model;

import lombok.*;

import java.time.LocalDateTime;

/**
 * 用户表 user_tbl（MyBatis 实体）
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserEntity {

    private Long id;
    private String username;
    private String password;
    private String realName;
    private String email;
    private String phone;
    private String avatar;
    @Builder.Default
    private Integer status = 1;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
    private String createBy;
    private String updateBy;
    private String remark;
}
