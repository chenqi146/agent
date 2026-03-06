package com.pg.platform.securitymng.application.command;

import jakarta.validation.constraints.NotBlank;
import lombok.*;

/**
 * 登录命令
 */
@Data
public class LoginCommand {

    @NotBlank(message = "用户名不能为空")
    private String username;

    @NotBlank(message = "密码不能为空")
    private String password;

    @NotBlank(message = "验证码不能为空")
    private String captchaId;

    @NotBlank(message = "验证码不能为空")
    private String captcha;
}
