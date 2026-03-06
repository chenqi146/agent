package com.pg.platform.securitymng.domain.valueobject;

import lombok.EqualsAndHashCode;
import lombok.Getter;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * 密码值对象：内部存储密文，支持校验明文
 */
@Getter
@EqualsAndHashCode
public class Password {

    private static final PasswordEncoder ENCODER = new BCryptPasswordEncoder();

    private final String encodedValue;

    public Password(String encodedValue) {
        if (encodedValue == null || encodedValue.isEmpty()) {
            throw new IllegalArgumentException("密码不能为空");
        }
        this.encodedValue = encodedValue;
    }

    /** 从明文创建并加密存储 */
    public static Password fromRaw(String rawPassword) {
        if (rawPassword == null || rawPassword.isEmpty()) {
            throw new IllegalArgumentException("密码不能为空");
        }
        return new Password(ENCODER.encode(rawPassword));
    }

    /** 校验明文是否与该密码匹配 */
    public boolean matches(String rawPassword) {
        return rawPassword != null && ENCODER.matches(rawPassword, this.encodedValue);
    }
}
