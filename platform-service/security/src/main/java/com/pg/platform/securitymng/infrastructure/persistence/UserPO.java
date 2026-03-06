package com.pg.platform.securitymng.infrastructure.persistence;

import lombok.Data;

/**
 * 用户表持久化对象（与 DB 表 user_tbl 对应，登录仅需 id/username/password_encoded）
 */
@Data
public class UserPO {

    private Long id;
    private String username;
    private String password;
}
