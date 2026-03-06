package com.pg.platform.usermng.interfaces.rest.controller;

import com.pg.platform.usermng.application.command.UserCommand;
import com.pg.platform.usermng.application.service.UserAppService;
import com.pg.platform.usermng.interfaces.rest.dto.*;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 用户管理接口（仅 POST）
 */
@RestController
@RequestMapping("/api/user")
@RequiredArgsConstructor
public class UserController {

    private final UserAppService userAppService;

    @PostMapping("/list")
    public ApiResult<PageResult<UserVO>> list(@RequestBody(required = false) PageRequest req) {
        if (req == null) req = new PageRequest();
        return userAppService.list(req);
    }

    @PostMapping("/getById")
    public ApiResult<UserVO> getById(@RequestBody @Valid IdRequest req) {
        return userAppService.getById(req.getId());
    }

    @PostMapping("/save")
    public ApiResult<UserVO> save(@RequestBody @Valid UserCommand cmd) {
        return userAppService.save(cmd);
    }

    @PostMapping("/delete")
    public ApiResult<Void> delete(@RequestBody @Valid IdRequest req) {
        return userAppService.delete(req.getId());
    }

    @PostMapping("/assignRoles")
    public ApiResult<Void> assignRoles(@RequestBody @Valid AssignRolesRequest req) {
        return userAppService.assignRoles(req.getUserId(), req.getRoleIds());
    }
}
