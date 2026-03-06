package com.pg.platform.usermng.interfaces.rest.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class IdRequest {
    @NotNull(message = "id不能为空")
    private Long id;
}
