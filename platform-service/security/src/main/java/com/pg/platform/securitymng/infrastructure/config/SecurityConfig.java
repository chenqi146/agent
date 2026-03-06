package com.pg.platform.securitymng.infrastructure.config;

import com.pg.platform.securitymng.interfaces.filter.JwtFilter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import java.util.Arrays;
import java.util.List;

/**
 * Spring Security 配置：放行 SSO 接口，其余走 JWT 过滤
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /** 放行路径（不校验 JWT），支持从 Nacos 覆盖；默认包含 SSO 与文档等 */
    @Value("${security.sso.exclude-paths:/v1/agent/sso/**,/api-docs/**,/swagger-ui/**,/swagger-ui.html,/actuator/**,/v3/api-docs/**}")
    private String excludePaths;

    @Bean
    @Order(1)
    public SecurityFilterChain securityFilterChain(HttpSecurity http, JwtFilter jwtFilter) throws Exception {
        List<String> permitPaths = Arrays.asList(excludePaths.split(","));
        String[] permit = permitPaths.stream().map(String::trim).filter(s -> !s.isEmpty()).toArray(String[]::new);

        http
                .securityMatcher("/**")
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(permit).permitAll()
                        .anyRequest().authenticated()
                )
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
