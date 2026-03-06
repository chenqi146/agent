package com.pg.platform.usermng.application.command;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 角色创建/更新命令
 */
@Data
public class RoleCommand {

    private Long id;

    @NotBlank(message = "角色编码不能为空")
    @Size(max = 50)
    private String roleCode;

    @NotBlank(message = "角色名称不能为空")
    @Size(max = 100)
    private String roleName;

    @NotBlank(message = "上一级角色不能为空")
    @Size(max = 50)
    private String upperLevelRoleCode;

    @NotBlank(message = "下一级角色不能为空")
    @Size(max = 50)
    private String nextLevelRoleCode;

    @Size(max = 500)
    private String description;

    private Integer status;

    @Size(max = 50)
    private String createBy;

    @Size(max = 50)
    private String updateBy;

    @Size(max = 500)
    private String remark;
}
