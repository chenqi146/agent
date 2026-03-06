package com.pg.platform.securitymng.shared.exception;

import com.pg.platform.securitymng.shared.constant.ErrorCode;
import com.pg.platform.securitymng.shared.constant.ErrorMessage;

/**
 * SSO 相关异常
 */
public class SsoException extends BusinessException {

    public SsoException(int code, String message) {
        super(code, message);
    }

    public SsoException(int code, String message, Throwable cause) {
        super(code, message, cause);
    }

    public static SsoException invalidCredentials() {
        return new SsoException(ErrorCode.INVALID_USER_OR_PASSWORD.getCode(), ErrorMessage.getMessage(ErrorCode.INVALID_USER_OR_PASSWORD));
    }

    public static SsoException tokenInvalid() {
        return new SsoException(ErrorCode.TOKEN_INVALID.getCode(), "Token 无效");
    }

    public static SsoException tokenExpired() {
        return new SsoException(ErrorCode.TOKEN_EXPIRED.getCode(), "Token 已过期");
    }

    public static SsoException tokenMissing() {
        return new SsoException(ErrorCode.TOKEN_MISSING.getCode(), "缺少 Token");
    }
}
