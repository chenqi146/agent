package com.pg.platform.securitymng.application.command;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 登出命令
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class LogoutCommand {

    @NotBlank(message = "Token 不能为空")
    private String token;
}
