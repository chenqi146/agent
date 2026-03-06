package com.pg.platform.securitymng.domain.model.user;

import com.pg.platform.securitymng.domain.valueobject.Password;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

/**
 * 用户聚合根
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class User {

    private Long id;
    private String username;
    private String password;

    private static final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    /** 校验传入的明文密码 */
    public boolean checkPassword(String rawPassword) {
        if (rawPassword == null) {
            return false;
        }
        return passwordEncoder.matches(rawPassword, this.password);
    }
}

