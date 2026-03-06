package com.pg.platform.securitymng.application.command;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * 校验 Token 命令
 */
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class ValidateTokenCommand {

    @NotBlank(message = "Token 不能为空")
    private String token;
}
