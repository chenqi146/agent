package com.pg.platform.gateway.config;

import com.pg.platform.gateway.filter.ApiKeyGlobalFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 注册网关全局过滤器（如 API Key 校验）
 */
@Configuration
public class GatewayFilterConfig {

    @Bean
    public ApiKeyGlobalFilter apiKeyGlobalFilter(GatewayApiKeyProperties apiKeyProperties) {
        return new ApiKeyGlobalFilter(apiKeyProperties);
    }
}
