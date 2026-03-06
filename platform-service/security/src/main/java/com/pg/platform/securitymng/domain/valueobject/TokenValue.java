package com.pg.platform.securitymng.domain.valueobject;

/**
 * Token 值对象
 */
public class TokenValue {

    private final String value;

    public TokenValue(String value) {
        if (value == null || value.isEmpty()) {
            throw new IllegalArgumentException("Token 不能为空");
        }
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        TokenValue that = (TokenValue) o;
        return value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return value.hashCode();
    }
}

