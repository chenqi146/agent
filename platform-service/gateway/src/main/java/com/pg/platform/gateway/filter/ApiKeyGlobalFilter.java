package com.pg.platform.gateway.filter;

import com.pg.platform.gateway.config.GatewayApiKeyProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.StringUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.List;

/**
 * 网关 API Key 全局过滤器：对未在排除列表中的路径校验 X-API-Key 或 Authorization: Bearer &lt;key&gt;
 */
public class ApiKeyGlobalFilter implements GlobalFilter, Ordered {

    private static final Logger log = LoggerFactory.getLogger(ApiKeyGlobalFilter.class);

    private static final String HEADER_X_API_KEY = "X-API-Key";
    /** 与前端 request.js 中 api-key 对应，浏览器会规范为 Api-Key */
    private static final String HEADER_API_KEY = "Api-Key";
    private static final String HEADER_AUTHORIZATION = "Authorization";
    private static final String BEARER_PREFIX = "Bearer ";

    private final GatewayApiKeyProperties properties;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    public ApiKeyGlobalFilter(GatewayApiKeyProperties properties) {
        this.properties = properties;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        if (!properties.isEnabled()) {
            return chain.filter(exchange);
        }

        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().value();

        if (isExcluded(path)) {
            return chain.filter(exchange);
        }

        String apiKey = resolveApiKey(request);
        if (apiKey != null && apiKey.equals(properties.getValue())) {
            return chain.filter(exchange);
        }

        log.warn("API Key missing or invalid for path: {}", path);
        return write401(exchange.getResponse());
    }

    private boolean isExcluded(String path) {
        List<String> excludePaths = properties.getExcludePaths();
        if (excludePaths == null || excludePaths.isEmpty()) {
            return false;
        }
        for (String pattern : excludePaths) {
            if (pathMatcher.match(pattern.trim(), path)) {
                return true;
            }
        }
        return false;
    }

    private String resolveApiKey(ServerHttpRequest request) {
        HttpHeaders headers = request.getHeaders();
        // 1) X-API-Key
        String key = headers.getFirst(HEADER_X_API_KEY);
        if (StringUtils.hasText(key)) {
            return key.trim();
        }
        // 2) Api-Key（前端常用，与 request.js 中 headers['api-key'] 对应）
        key = headers.getFirst(HEADER_API_KEY);
        if (StringUtils.hasText(key)) {
            return key.trim();
        }
        // 3) Authorization: Bearer <key>（仅当值为网关 key 时用于校验，避免与用户 JWT 冲突）
        String auth = headers.getFirst(HEADER_AUTHORIZATION);
        if (StringUtils.hasText(auth) && auth.startsWith(BEARER_PREFIX)) {
            return auth.substring(BEARER_PREFIX.length()).trim();
        }
        return null;
    }

    private Mono<Void> write401(ServerHttpResponse response) {
        response.setStatusCode(HttpStatus.UNAUTHORIZED);
        response.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        String body = "{\"code\":401,\"message\":\"Invalid or missing API Key\"}";
        DataBuffer buffer = response.bufferFactory().wrap(body.getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(buffer));
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
