package com.pg.platform.usermng.application.service;

import com.pg.platform.usermng.application.command.RoleCommand;
import com.pg.platform.usermng.domain.model.RoleEntity;
import com.pg.platform.usermng.interfaces.rest.dto.ApiResult;
import com.pg.platform.usermng.interfaces.rest.dto.PageRequest;
import com.pg.platform.usermng.interfaces.rest.dto.PageResult;
import com.pg.platform.usermng.interfaces.rest.dto.RoleVO;
import com.pg.platform.usermng.domain.mapper.RoleMapper;
import com.pg.platform.usermng.domain.mapper.UserRoleMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class RoleAppService {

    private final RoleMapper roleMapper;
    private final UserRoleMapper userRoleMapper;

    @Transactional(readOnly = true)
    public ApiResult<PageResult<RoleVO>> list(PageRequest req) {
        int page = req.getPage() != null ? req.getPage() : 0;
        int size = req.getSize() != null ? req.getSize() : 10;
        int offset = page * size;

        long total;
        List<RoleEntity> rows;
        if (req.getKeyword() != null && !req.getKeyword().isBlank()) {
            String kw = "%" + req.getKeyword().trim() + "%";
            total = roleMapper.countByKeyword(kw);
            rows = roleMapper.selectPageByKeyword(kw, offset, size);
        } else {
            total = roleMapper.countAll();
            rows = roleMapper.selectPage(offset, size);
        }
        List<RoleVO> list = rows.stream().map(this::toVO).collect(Collectors.toList());
        return ApiResult.ok(new PageResult<>(list, total, page, size));
    }

    @Transactional(readOnly = true)
    public ApiResult<RoleVO> getById(Long id) {
        RoleEntity e = roleMapper.findById(id);
        if (e == null) return ApiResult.fail(404, "角色不存在");
        return ApiResult.ok(toVO(e));
    }

    @Transactional
    public ApiResult<RoleVO> save(RoleCommand cmd) {
        if (cmd.getId() != null) {
            RoleEntity existing = roleMapper.findById(cmd.getId());
            if (existing == null) return ApiResult.fail(404, "角色不存在");
            if (roleMapper.countByRoleCodeExcludeId(cmd.getRoleCode(), cmd.getId()) > 0) {
                return ApiResult.fail(400, "角色编码已存在");
            }
            existing.setRoleCode(cmd.getRoleCode());
            existing.setRoleName(cmd.getRoleName());
            existing.setUpperLevelRoleCode(cmd.getUpperLevelRoleCode());
            existing.setNextLevelRoleCode(cmd.getNextLevelRoleCode());
            existing.setDescription(cmd.getDescription());
            if (cmd.getStatus() != null) existing.setStatus(cmd.getStatus());
            existing.setUpdateBy(cmd.getUpdateBy());
            existing.setRemark(cmd.getRemark());
            roleMapper.update(existing);
            return ApiResult.ok(toVO(roleMapper.findById(cmd.getId())));
        }
        if (roleMapper.countByRoleCode(cmd.getRoleCode()) > 0) {
            return ApiResult.fail(400, "角色编码已存在");
        }
        RoleEntity entity = RoleEntity.builder()
                .roleCode(cmd.getRoleCode())
                .roleName(cmd.getRoleName())
                .upperLevelRoleCode(cmd.getUpperLevelRoleCode())
                .nextLevelRoleCode(cmd.getNextLevelRoleCode())
                .description(cmd.getDescription())
                .status(cmd.getStatus() != null ? cmd.getStatus() : 1)
                .createBy(cmd.getCreateBy())
                .updateBy(cmd.getUpdateBy())
                .remark(cmd.getRemark())
                .build();
        roleMapper.insert(entity);
        return ApiResult.ok(toVO(roleMapper.findById(entity.getId())));
    }

    @Transactional
    public ApiResult<Void> delete(Long id) {
        if (roleMapper.findById(id) == null) {
            return ApiResult.fail(404, "角色不存在");
        }
        userRoleMapper.deleteByRoleId(id);
        roleMapper.deleteById(id);
        return ApiResult.ok();
    }

    private RoleVO toVO(RoleEntity e) {
        RoleVO vo = new RoleVO();
        vo.setId(e.getId());
        vo.setRoleCode(e.getRoleCode());
        vo.setRoleName(e.getRoleName());
        vo.setUpperLevelRoleCode(e.getUpperLevelRoleCode());
        vo.setNextLevelRoleCode(e.getNextLevelRoleCode());
        vo.setDescription(e.getDescription());
        vo.setStatus(e.getStatus());
        vo.setCreateTime(e.getCreateTime());
        vo.setUpdateTime(e.getUpdateTime());
        vo.setCreateBy(e.getCreateBy());
        vo.setUpdateBy(e.getUpdateBy());
        vo.setRemark(e.getRemark());
        return vo;
    }
}
