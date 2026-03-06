package com.pg.platform.usermng.interfaces.rest.controller;

import com.pg.platform.usermng.application.command.RoleCommand;
import com.pg.platform.usermng.application.service.RoleAppService;
import com.pg.platform.usermng.interfaces.rest.dto.*;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

/**
 * 角色管理接口（仅 POST）
 */
@RestController
@RequestMapping("/api/role")
@RequiredArgsConstructor
public class RoleController {

    private final RoleAppService roleAppService;

    @PostMapping("/list")
    public ApiResult<PageResult<RoleVO>> list(@RequestBody(required = false) PageRequest req) {
        if (req == null) req = new PageRequest();
        return roleAppService.list(req);
    }

    @PostMapping("/getById")
    public ApiResult<RoleVO> getById(@RequestBody @Valid IdRequest req) {
        return roleAppService.getById(req.getId());
    }

    @PostMapping("/save")
    public ApiResult<RoleVO> save(@RequestBody @Valid RoleCommand cmd) {
        return roleAppService.save(cmd);
    }

    @PostMapping("/delete")
    public ApiResult<Void> delete(@RequestBody @Valid IdRequest req) {
        return roleAppService.delete(req.getId());
    }
}
