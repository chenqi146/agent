package com.pg.platform.usermng.interfaces.rest.dto;

import lombok.Data;

@Data
public class PageRequest {
    private Integer page = 0;
    private Integer size = 10;
    private String keyword; // 用户名/姓名 或 角色编码/名称 模糊查询
}
