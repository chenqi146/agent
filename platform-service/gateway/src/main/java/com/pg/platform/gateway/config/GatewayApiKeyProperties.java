package com.pg.platform.gateway.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * 网关 API Key 校验配置
 */
@Component
@ConfigurationProperties(prefix = "gateway.api-key")
public class GatewayApiKeyProperties {

    /** 是否启用 API Key 校验 */
    private boolean enabled = true;

    /** 合法的 API Key 值（客户端需在 X-API-Key 或 Authorization: Bearer &lt;key&gt; 中携带） */
    private String value = "pg-gateway-key";

    /** 不校验 API Key 的路径（如 SSO 登录、验证码等），支持 Ant 风格 */
    private List<String> excludePaths = new ArrayList<>(List.of("/api/v1/agent/sso/**", "/actuator/health", "/actuator/info"));

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public String getValue() {
        return value;
    }

    public void setValue(String value) {
        this.value = value;
    }

    public List<String> getExcludePaths() {
        return excludePaths;
    }

    public void setExcludePaths(List<String> excludePaths) {
        this.excludePaths = excludePaths != null ? excludePaths : new ArrayList<>();
    }
}
