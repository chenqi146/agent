package com.pg.platform.securitymng.interfaces.dto;

import jakarta.validation.Valid;

/**
 * 通用请求封装：所有请求体统一为 {\"tag\":\"agent\",\"timestamp\":123,\"data\":{...}}
 */
public class AgentRequest<T> {

    /**
     * 请求来源标记，例如 \"agent\"，可用于路由或审计
     */
    private String tag;

    /**
     * 客户端发送请求时的时间戳（毫秒）
     */
    private Long timestamp;

    /**
     * 真实业务数据
     */
    @Valid
    private T data;

    public AgentRequest() {
    }

    public AgentRequest(String tag, Long timestamp, T data) {
        this.tag = tag;
        this.timestamp = timestamp;
        this.data = data;
    }

    public String getTag() {
        return tag;
    }

    public void setTag(String tag) {
        this.tag = tag;
    }

    public Long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Long timestamp) {
        this.timestamp = timestamp;
    }

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }
}

