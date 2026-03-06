package com.pg.platform.securitymng.interfaces.controller;

import com.pg.platform.securitymng.application.command.LoginCommand;
import com.pg.platform.securitymng.application.command.LogoutCommand;
import com.pg.platform.securitymng.application.command.ValidateTokenCommand;
import com.pg.platform.securitymng.application.service.SsoApplicationService;
import com.pg.platform.securitymng.domain.model.token.Token;
import com.pg.platform.securitymng.interfaces.dto.AgentRequest;
import com.pg.platform.securitymng.interfaces.dto.ApiResult;
import com.pg.platform.securitymng.shared.constant.ErrorCode;
import com.pg.platform.securitymng.shared.constant.ErrorMessage;
import com.pg.platform.securitymng.shared.constant.SsoContant;
import com.pg.platform.securitymng.shared.exception.BusinessException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;

/**
 * SSO 登录/登出/校验接口
 */
@RestController
@RequestMapping("/v1/agent/sso")
@Tag(name = "单点登录管理", description = "单点登录认证和授权接口")
public class SsoController {

    private static final Logger log = LoggerFactory.getLogger(SsoController.class);
    @Autowired
    private SsoApplicationService ssoApplicationService;
    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    @PostMapping("/login")
    @Operation(
            summary = "用户登录",
            description = "使用用户名和密码进行登录，请求体统一为 {tag,timestamp,data}，响应为 ApiResult 包装"
    )
    @ApiResponses(value = {
            @ApiResponse(
                    responseCode = "200",
                    description = "登录成功，返回 ApiResult，data 为登录结果（包含 token、userId、username、expiresAt）",
                    content = @Content(schema = @Schema(implementation = ApiResult.class))
            ),
            @ApiResponse(
                    responseCode = "200",
                    description = "业务失败（如用户名或密码错误），仍返回 ApiResult，code 为业务错误码，message 为错误信息",
                    content = @Content(schema = @Schema(implementation = ApiResult.class))
            )
    })
    public ApiResult<Map<String, Object>> login(@RequestBody @Valid AgentRequest<LoginCommand> request) {
        LoginCommand command = request.getData();
        /**验证码*/
        if (command.getCaptchaId() != null && command.getCaptcha() != null) {
            String key = SsoContant.REDIS_CAPTCHA_PREFIX + command.getCaptchaId();
            String captcha = stringRedisTemplate.opsForValue().get(key);
            if (captcha == null || !captcha.equalsIgnoreCase(command.getCaptcha())) {
                log.error("验证码错误，captchaId: {}, captcha: {}", command.getCaptchaId(), command.getCaptcha());
                return ApiResult.fail(ErrorCode.CAPTCHA_INVALID.getCode(), ErrorMessage.getMessage(ErrorCode.CAPTCHA_INVALID));
            }
        }

        /**校验用户名与密码*/
        Token token = ssoApplicationService.login(command);
        Map<String, Object> body = new HashMap<>();
        body.put("token", token.getTokenValue().getValue());
        body.put("userId", token.getUserId());
        body.put("username", token.getUsername());
        body.put("expiresAt", token.getExpiresAt().toString());
        return ApiResult.ok(body);
    }

    /**
     * 获取登录验证码：生成 4 位字母数字混合验证码（非纯数字），返回 Base64 图片和验证码 ID，验证码存入 Redis，TTL 60 秒
     */
    @PostMapping("/captcha")
    @Operation(summary = "获取登录验证码", description = "生成 4 位字母数字混合验证码（非纯数字），返回 Base64 图片和验证码 ID，验证码存入 Redis，TTL 60 秒；请求体统一为 {tag,timestamp,data}")
    public ApiResult<Map<String, Object>> captcha(@RequestBody(required = false) @Valid AgentRequest<Map<String, Object>> request) {
        try {
            // 1. 生成 6 位字母数字混合验证码（避免纯数字）
            String chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";
            StringBuilder sb = new StringBuilder();
            ThreadLocalRandom random = ThreadLocalRandom.current();
            for (int i = 0; i < 6; i++) {
                sb.append(chars.charAt(random.nextInt(chars.length())));
            }
            String code = sb.toString();
            String captchaId = UUID.randomUUID().toString().replace("-", "");

            // 2. 生成验证码图片（彩色文字 + 干扰线）
            int width = 120;
            int height = 48;
            BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
            Graphics2D g = image.createGraphics();
            try {
                g.setColor(Color.WHITE);
                g.fillRect(0, 0, width, height);

                // 抗锯齿
                g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

                // 随机文字颜色
                g.setColor(new Color(random.nextInt(50, 200), random.nextInt(50, 200), random.nextInt(50, 200)));
                g.setFont(new Font("Arial", Font.BOLD, 30));
                FontMetrics fm = g.getFontMetrics();
                int textWidth = fm.stringWidth(code);
                int x = (width - textWidth) / 2;
                int y = (height - fm.getHeight()) / 2 + fm.getAscent();
                g.drawString(code, x, y);

                // 添加一条波浪干扰线
                g.setColor(new Color(180, 80, 50));
                int lineY = height / 2 + random.nextInt(-5, 6);
                int prevX = 0;
                int prevY = lineY;
                for (int i = 1; i < width; i++) {
                    int newY = lineY + (int) (4 * Math.sin(i / 6.0));
                    g.drawLine(prevX, prevY, i, newY);
                    prevX = i;
                    prevY = newY;
                }
            } finally {
                g.dispose();
            }

            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            javax.imageio.ImageIO.write(image, "png", baos);
            String base64 = Base64.getEncoder().encodeToString(baos.toByteArray());

            // 3. 存入 Redis，TTL 60 秒
            String key = SsoContant.REDIS_CAPTCHA_PREFIX + captchaId;
            stringRedisTemplate.opsForValue().set(key, code, SsoContant.CAPTCHA_TTL_SECONDS, TimeUnit.SECONDS);

            // 4. 返回给前端
            Map<String, Object> body = new HashMap<>();
            body.put("captchaId", captchaId);
            body.put("imageBase64", base64);
            body.put("expireSeconds", SsoContant.CAPTCHA_TTL_SECONDS);
            return ApiResult.ok(body);
        } catch (Exception e) {
            log.error("生成验证码失败", e);
            return ApiResult.fail(500, "生成验证码失败");
        }
    }

    @PostMapping("/logout")
    @Operation(summary = "用户登出", description = "使指定 token 失效，请求体统一为 {tag,timestamp,data}")
    public ApiResult<String> logout(@RequestBody @Valid AgentRequest<LogoutCommand> request) {
        LogoutCommand command = request.getData();
        ssoApplicationService.logout(command);
        return ApiResult.ok("登出成功");
    }

    @PostMapping("/validate")
    @Operation(summary = "Token 校验", description = "校验 token 是否有效，请求体统一为 {tag,timestamp,data}")
    public ApiResult<Map<String, Object>> validate(@RequestBody @Valid AgentRequest<ValidateTokenCommand> request) {
        ValidateTokenCommand command = request.getData();
        Token token = ssoApplicationService.validateToken(command);
        Map<String, Object> body = new HashMap<>();
        body.put("valid", true);
        body.put("userId", token.getUserId());
        body.put("username", token.getUsername());
        body.put("expiresAt", token.getExpiresAt().toString());
        return ApiResult.ok(body);
    }

    @ExceptionHandler(BusinessException.class)
    public ApiResult<Void> handleBusinessException(BusinessException e) {
        // 约定错误时使用 HTTP 200 + 业务 code
        return ApiResult.fail(401, e.getMessage());
    }
}
