package com.pg.platform.usermng.application.command;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 用户创建/更新命令
 */
@Data
public class UserCommand {

    private Long id;

    @NotBlank(message = "用户名不能为空")
    @Size(max = 50)
    private String username;

    @Size(max = 255)
    private String password; // 为空时表示不修改密码

    @Size(max = 50)
    private String realName;

    @Size(max = 100)
    private String email;

    @Size(max = 20)
    private String phone;

    @Size(max = 255)
    private String avatar;

    private Integer status; // 0-禁用 1-启用

    @Size(max = 50)
    private String createBy;

    @Size(max = 50)
    private String updateBy;

    @Size(max = 500)
    private String remark;
}
