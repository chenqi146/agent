package com.pg.platform.securitymng.interfaces.filter;

import com.pg.platform.securitymng.domain.model.sso.SsoService;
import com.pg.platform.securitymng.domain.model.token.Token;
import com.pg.platform.securitymng.shared.constant.SsoContant;
import com.pg.platform.securitymng.shared.exception.SsoException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.util.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;

/**
 * JWT 过滤器：从 Header 取 Token，校验后设置 SecurityContext
 */
@Component
public class JwtFilter extends OncePerRequestFilter {

    private final SsoService ssoService;

    @Autowired
    public JwtFilter(SsoService ssoService) {
        this.ssoService = ssoService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String authHeader = request.getHeader(SsoContant.HEADER_AUTHORIZATION);
        String tokenValue = null;
        if (StringUtils.hasText(authHeader) && authHeader.startsWith(SsoContant.BEARER_PREFIX)) {
            tokenValue = authHeader.substring(SsoContant.BEARER_PREFIX.length()).trim();
        }

        if (StringUtils.hasText(tokenValue)) {
            try {
                Token token = ssoService.validateToken(tokenValue);
                UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                        token.getUsername(),
                        null,
                        Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER"))
                );
                SecurityContextHolder.getContext().setAuthentication(auth);
                request.setAttribute("userId", token.getUserId());
                request.setAttribute("username", token.getUsername());
            } catch (SsoException e) {
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                response.setContentType("application/json;charset=UTF-8");
                response.getWriter().write("{\"code\":\"" + e.getCode() + "\",\"message\":\"" + e.getMessage() + "\"}");
                return;
            }
        }

        filterChain.doFilter(request, response);
    }
}
