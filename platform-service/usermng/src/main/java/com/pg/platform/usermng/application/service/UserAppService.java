package com.pg.platform.usermng.application.service;

import com.pg.platform.usermng.application.command.UserCommand;
import com.pg.platform.usermng.domain.model.UserEntity;
import com.pg.platform.usermng.domain.model.UserRoleEntity;
import com.pg.platform.usermng.interfaces.rest.dto.ApiResult;
import com.pg.platform.usermng.interfaces.rest.dto.PageRequest;
import com.pg.platform.usermng.interfaces.rest.dto.PageResult;
import com.pg.platform.usermng.interfaces.rest.dto.UserVO;
import com.pg.platform.usermng.domain.mapper.RoleMapper;
import com.pg.platform.usermng.domain.mapper.UserMapper;
import com.pg.platform.usermng.domain.mapper.UserRoleMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class UserAppService {

    private final UserMapper userMapper;
    private final UserRoleMapper userRoleMapper;
    private final RoleMapper roleMapper;

    @Transactional(readOnly = true)
    public ApiResult<PageResult<UserVO>> list(PageRequest req) {
        int page = req.getPage() != null ? req.getPage() : 0;
        int size = req.getSize() != null ? req.getSize() : 10;
        int offset = page * size;

        long total;
        List<UserEntity> rows;
        if (req.getKeyword() != null && !req.getKeyword().isBlank()) {
            String kw = "%" + req.getKeyword().trim() + "%";
            total = userMapper.countByKeyword(kw);
            rows = userMapper.selectPageByKeyword(kw, offset, size);
        } else {
            total = userMapper.countAll();
            rows = userMapper.selectPage(offset, size);
        }
        List<UserVO> list = rows.stream().map(this::toVO).collect(Collectors.toList());
        return ApiResult.ok(new PageResult<>(list, total, page, size));
    }

    @Transactional(readOnly = true)
    public ApiResult<UserVO> getById(Long id) {
        UserEntity u = userMapper.findById(id);
        if (u == null) return ApiResult.fail(404, "用户不存在");
        return ApiResult.ok(toVO(u));
    }

    @Transactional
    public ApiResult<UserVO> save(UserCommand cmd) {
        if (cmd.getId() != null) {
            UserEntity existing = userMapper.findById(cmd.getId());
            if (existing == null) return ApiResult.fail(404, "用户不存在");
            if (userMapper.countByUsernameExcludeId(cmd.getUsername(), cmd.getId()) > 0) {
                return ApiResult.fail(400, "用户名已存在");
            }
            existing.setUsername(cmd.getUsername());
            if (cmd.getPassword() != null && !cmd.getPassword().isBlank()) {
                existing.setPassword(cmd.getPassword());
            }
            existing.setRealName(cmd.getRealName());
            existing.setEmail(cmd.getEmail());
            existing.setPhone(cmd.getPhone());
            existing.setAvatar(cmd.getAvatar());
            if (cmd.getStatus() != null) existing.setStatus(cmd.getStatus());
            existing.setUpdateBy(cmd.getUpdateBy());
            existing.setRemark(cmd.getRemark());
            userMapper.update(existing);
            return ApiResult.ok(toVO(userMapper.findById(cmd.getId())));
        }
        if (userMapper.countByUsername(cmd.getUsername()) > 0) {
            return ApiResult.fail(400, "用户名已存在");
        }
        if (cmd.getPassword() == null || cmd.getPassword().isBlank()) {
            return ApiResult.fail(400, "密码不能为空");
        }
        UserEntity entity = UserEntity.builder()
                .username(cmd.getUsername())
                .password(cmd.getPassword())
                .realName(cmd.getRealName())
                .email(cmd.getEmail())
                .phone(cmd.getPhone())
                .avatar(cmd.getAvatar())
                .status(cmd.getStatus() != null ? cmd.getStatus() : 1)
                .createBy(cmd.getCreateBy())
                .updateBy(cmd.getUpdateBy())
                .remark(cmd.getRemark())
                .build();
        userMapper.insert(entity);
        return ApiResult.ok(toVO(userMapper.findById(entity.getId())));
    }

    @Transactional
    public ApiResult<Void> delete(Long id) {
        if (userMapper.findById(id) == null) {
            return ApiResult.fail(404, "用户不存在");
        }
        userRoleMapper.deleteByUserId(id);
        userMapper.deleteById(id);
        return ApiResult.ok();
    }

    @Transactional
    public ApiResult<Void> assignRoles(Long userId, List<Long> roleIds) {
        if (userMapper.findById(userId) == null) {
            return ApiResult.fail(404, "用户不存在");
        }
        for (Long roleId : roleIds) {
            if (roleMapper.findById(roleId) == null) {
                return ApiResult.fail(400, "角色不存在: " + roleId);
            }
        }
        userRoleMapper.deleteByUserId(userId);
        LocalDateTime now = LocalDateTime.now();
        for (Long roleId : roleIds) {
            UserRoleEntity ur = UserRoleEntity.builder()
                    .userId(userId)
                    .roleId(roleId)
                    .createTime(now)
                    .build();
            userRoleMapper.insert(ur);
        }
        return ApiResult.ok();
    }

    private UserVO toVO(UserEntity e) {
        UserVO vo = new UserVO();
        vo.setId(e.getId());
        vo.setUsername(e.getUsername());
        vo.setRealName(e.getRealName());
        vo.setEmail(e.getEmail());
        vo.setPhone(e.getPhone());
        vo.setAvatar(e.getAvatar());
        vo.setStatus(e.getStatus());
        vo.setCreateTime(e.getCreateTime());
        vo.setUpdateTime(e.getUpdateTime());
        vo.setCreateBy(e.getCreateBy());
        vo.setUpdateBy(e.getUpdateBy());
        vo.setRemark(e.getRemark());
        List<Long> roleIds = userRoleMapper.findByUserId(e.getId()).stream()
                .map(UserRoleEntity::getRoleId)
                .collect(Collectors.toList());
        vo.setRoleIds(roleIds);
        return vo;
    }
}
