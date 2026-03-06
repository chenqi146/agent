## 算法与算力资源描述
--算法-- | -- 显存 ---
qwen3-32B： 67208MiB
Qwen3-VL-32B-Thinking: 67208MiB
Qwen3-VL-32B-Instruct-AWQ: 67208MiB   
# 备注： 最小的显存：19.5561 GiB(model weight) + 43.80(kvcache)
Qwen3-Embedding-8B： 15942MiB  ---  AWQ量化版本
Qwen3-Reranker-0.6B: 6380MiB

# 下载地址
modelscope download --model Qwen/Qwen3-VL-32B-Thinking --local_dir Qwen/Qwen3-VL-32B-Thinking
modelscope download --model Qwen/Qwen/Qwen3-32B --local_dir Qwen/Qwen3-32B
modelscope download --model Qwen/Qwen3-Embedding-8B

---

## 引擎模式说明

服务支持两种引擎模式，通过配置 `engine_type` 选择：

| 引擎类型 | 同步请求 | 流式请求 | 说明 |
|---------|---------|---------|------|
| `llm` | ✅ 支持 | ✅ chunk 模式 | 使用 vLLM LLM 类，先完整生成再分块返回 |
| `async` | ❌ 不支持 | ✅ token 模式 | 使用 AsyncLLMEngine，真正的逐 token 流式 |

> **注意**：当配置为 `async` 引擎时，同步请求（`stream=false`）会返回错误，请使用流式模式。

---

## VLM 接口（视觉语言模型）

### 1. `/v1/vision/completions` - 视觉对话补全

**用途**：多模态大模型推理接口，支持文本+图片的连续推理。

**请求方式**：POST

#### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | string | 否 | null | 模型名称（可选） |
| `messages` | array | **是** | - | 对话历史（支持图像），至少1条 |
| `max_tokens` | integer | 否 | 配置值 | 最大生成 token 数（1-8192） |
| `temperature` | float | 否 | 配置值 | 温度参数（0.0-2.0） |
| `top_p` | float | 否 | null | Top-p 采样参数（0.0-1.0） |
| `top_k` | integer | 否 | null | Top-k 采样参数 |
| `stream` | boolean | 否 | false | 是否流式输出 |
| `stream_options` | object | 否 | null | 流式输出选项 |
| `stop` | string/array | 否 | null | 停止词 |
| `user` | string | 否 | null | 用户标识 |

#### messages 消息格式

```json
{
  "role": "user|system|assistant",
  "content": "文本内容" 或 [内容数组]
}
```

**content 内容数组格式**：
```json
[
  {"type": "text", "text": "文本内容"},
  {"type": "image_url", "image_url": {"url": "图片base64或URL", "detail": "auto|low|high"}}
]
```

#### stream_options 流式选项

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mode` | string | "auto" | 流式模式：`token`/`chunk`/`auto` |
| `chunk_size` | integer | 10 | chunk 模式下每块字符数（1-100） |
| `include_usage` | boolean | false | 是否在最后一个块中包含 usage 信息 |

#### 请求示例

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的图像分析助手。"
    },
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "请描述这张图片 /think"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ..."}}
      ]
    }
  ],
  "max_tokens": 512,
  "temperature": 0.7,
  "stream": false
}
```

#### 响应格式（非流式）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "chatcmpl-abc123...",
    "object": "chat.completion",
    "created": 1703234567,
    "model": "Qwen3-VL-32B-Thinking",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "这张图片显示了..."
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 1024,
      "completion_tokens": 256,
      "total_tokens": 1280
    }
  }
}
```

#### 响应格式（流式 SSE）

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1703234567,"model":"Qwen3-VL","choices":[{"index":0,"delta":{"role":"assistant","content":"这"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1703234567,"model":"Qwen3-VL","choices":[{"index":0,"delta":{"content":"张"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1703234567,"model":"Qwen3-VL","choices":[{"index":0,"delta":{"content":"图片"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1703234567,"model":"Qwen3-VL","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

---

### 2. `/v1/vision/analyze` - 单图像分析

**用途**：单张图片快速分析，简化接口。

**请求方式**：POST

#### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `image` | string | **是** | - | 图像 URL 或 base64 编码 |
| `prompt` | string | 否 | "请描述这张图片" | 分析提示词 |
| `max_tokens` | integer | 否 | 配置值 | 最大生成 token 数（1-4096） |
| `temperature` | float | 否 | 配置值 | 温度参数（0.0-2.0） |
| `detail` | string | 否 | "auto" | 图像细节级别：`auto`/`low`/`high` |

#### 请求示例

```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQ...",
  "prompt": "描述图片中的车辆信息",
  "max_tokens": 200
}
```

#### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "description": "图片中显示了一辆白色轿车...",
    "prompt_tokens": 512,
    "completion_tokens": 128,
    "latency_ms": 1234.56
  }
}
```

---

### 3. `/v1/vision/analyze/multi` - 多图像分析

**用途**：多张图片对比分析、时序分析。

**请求方式**：POST

#### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `images` | array | **是** | - | 图像列表（1-10张） |
| `prompt` | string | 否 | "请分析这些图片" | 分析提示词 |
| `max_tokens` | integer | 否 | 配置值 | 最大生成 token 数 |
| `temperature` | float | 否 | 配置值 | 温度参数 |

#### 请求示例

```json
{
  "images": [
    "data:image/jpeg;base64,/9j/4AAQ...",
    "data:image/jpeg;base64,/9j/4BBR...",
    "data:image/jpeg;base64,/9j/4CCS..."
  ],
  "prompt": "对比这三张图片，分析停车场变化趋势",
  "max_tokens": 500
}
```

#### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "description": "通过对比三张图片，可以看到...",
    "prompt_tokens": 1536,
    "completion_tokens": 256,
    "latency_ms": 3456.78
  }
}
```

---

## LLM 接口（纯文本语言模型）

### 4. `/v1/chat/completions` - 对话补全

**用途**：纯文本对话推理，兼容 OpenAI Chat API。

**请求方式**：POST

#### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | string | 否 | null | 模型名称 |
| `messages` | array | **是** | - | 对话历史 |
| `max_tokens` | integer | 否 | 配置值 | 最大生成 token 数 |
| `temperature` | float | 否 | 配置值 | 温度参数 |
| `top_p` | float | 否 | null | Top-p 采样参数 |
| `top_k` | integer | 否 | null | Top-k 采样参数 |
| `stream` | boolean | 否 | false | 是否流式输出 |
| `stream_options` | object | 否 | null | 流式输出选项 |
| `stop` | string/array | 否 | null | 停止词 |
| `n` | integer | 否 | 1 | 生成数量（1-10） |
| `presence_penalty` | float | 否 | 0.0 | 存在惩罚（-2.0~2.0） |
| `frequency_penalty` | float | 否 | 0.0 | 频率惩罚（-2.0~2.0） |

#### messages 消息格式

```json
[
  {"role": "system", "content": "系统提示词"},
  {"role": "user", "content": "用户消息"},
  {"role": "assistant", "content": "助手回复"}
]
```

#### 请求示例

```json
{
  "messages": [
    {"role": "system", "content": "你是一个有帮助的助手。"},
    {"role": "user", "content": "你好，请介绍一下你自己"}
  ],
  "max_tokens": 256,
  "temperature": 0.7,
  "stream": true,
  "stream_options": {
    "mode": "token"
  }
}
```

#### 响应格式（非流式）

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "chatcmpl-abc123...",
    "object": "chat.completion",
    "created": 1703234567,
    "model": "Qwen3-32B",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "你好！我是一个人工智能助手..."
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 32,
      "completion_tokens": 128,
      "total_tokens": 160
    }
  }
}
```

---

### 5. `/v1/completions` - 文本补全

**用途**：纯文本补全，兼容 OpenAI Completions API。

**请求方式**：POST

#### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string/array | **是** | - | 输入提示词，支持单条或批量 |
| `max_tokens` | integer | 否 | 配置值 | 最大生成 token 数 |
| `temperature` | float | 否 | 配置值 | 温度参数 |
| `stream` | boolean | 否 | false | 是否流式输出 |
| `stop` | string/array | 否 | null | 停止词 |

#### 请求示例

```json
{
  "prompt": "人工智能的未来发展趋势是",
  "max_tokens": 256,
  "temperature": 0.8
}
```

#### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "cmpl-abc123...",
    "object": "text_completion",
    "created": 1703234567,
    "model": "Qwen3-32B",
    "choices": [
      {
        "index": 0,
        "text": "人工智能的未来发展趋势是多元化的...",
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 16,
      "completion_tokens": 128,
      "total_tokens": 144
    }
  }
}
```

#### 响应格式（流式 SSE）

```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1703234567,"model":"Qwen3-32B","choices":[{"index":0,"delta":{"role":"assistant","content":"你"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1703234567,"model":"Qwen3-32B","choices":[{"index":0,"delta":{"content":"好"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1703234567,"model":"Qwen3-32B","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

---

### 6. `/v1/models` - 获取模型列表

**用途**：获取可用模型列表，兼容 OpenAI Models API。

**请求方式**：POST（空请求体 `{}`）

#### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "object": "list",
    "data": [
      {
        "id": "Qwen3-32B",
        "object": "model",
        "created": 1703234567,
        "owned_by": "organization"
      }
    ]
  }
}
```

---

## Embedding 接口（文本向量化）

### 7. `/v1/embeddings` - 文本向量化

**用途**：将文本转换为向量表示，兼容 OpenAI Embeddings API。

**请求方式**：POST

#### 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `model` | string | 否 | null | 模型名称（可选） |
| `input` | string/array | **是** | - | 输入文本，支持单条或批量 |
| `encoding_format` | string | 否 | "float" | 编码格式：`float` 或 `base64` |
| `dimensions` | integer | 否 | null | 输出向量维度（部分模型支持） |
| `user` | string | 否 | null | 用户标识 |

#### 请求示例（单条文本）

```json
{
  "input": "这是一段需要向量化的文本",
  "model": "Qwen3-Embedding-8B"
}
```

#### 请求示例（批量文本）

```json
{
  "input": [
    "第一段文本",
    "第二段文本",
    "第三段文本"
  ]
}
```

#### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "object": "list",
    "model": "Qwen3-Embedding-8B",
    "data": [
      {
        "object": "embedding",
        "index": 0,
        "embedding": [0.0123, -0.0456, 0.0789, ...]
      },
      {
        "object": "embedding",
        "index": 1,
        "embedding": [0.0234, -0.0567, 0.0890, ...]
      }
    ],
    "usage": {
      "prompt_tokens": 24,
      "total_tokens": 24
    }
  }
}
```

---

## 服务管理接口

### VLM 服务管理

#### `/vlm/health` - VLM 健康检查

**请求方式**：POST（空请求体 `{}`）

#### `/vlm/metrics` - VLM 服务指标

**请求方式**：POST（空请求体 `{}`）

#### `/vlm/gpu/resources` - VLM GPU 资源查询

**请求方式**：POST（空请求体 `{}`）

#### `/vlm/model/reload` - 重新加载 VLM 模型

**请求方式**：POST

```json
{
  "force": false
}
```

---

### LLM 服务管理

#### `/health` - LLM 健康检查

**请求方式**：POST（空请求体 `{}`）

#### `/metrics` - LLM 服务指标

**请求方式**：POST（空请求体 `{}`）

#### `/gpu/resources` - LLM GPU 资源查询

**请求方式**：POST（空请求体 `{}`）

#### `/model/reload` - 重新加载 LLM 模型

**请求方式**：POST

```json
{
  "force": false
}
```

---

### Embedding 服务管理

#### `/embedding/health` - Embedding 健康检查

**请求方式**：POST（空请求体 `{}`）

#### `/embedding/metrics` - Embedding 服务指标

**请求方式**：POST（空请求体 `{}`）

#### `/embedding/gpu/resources` - Embedding GPU 资源查询

**请求方式**：POST（空请求体 `{}`）

---

### 健康检查响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "is_healthy": true,
    "model_status": "ready",
    "model_name": "Qwen3-32B",
    "uptime_seconds": 3600.5,
    "total_requests": 1000,
    "successful_requests": 995,
    "failed_requests": 5,
    "active_requests": 2,
    "avg_latency_ms": 1234.56,
    "gpu_resources": [
      {
        "gpu_id": 0,
        "gpu_name": "NVIDIA A100",
        "total_memory_mb": 81920,
        "used_memory_mb": 65536,
        "free_memory_mb": 16384,
        "memory_utilization": 0.8,
        "gpu_utilization": 0.65,
        "temperature": 55.0
      }
    ]
  }
}
```

### 服务指标响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "model_name": "Qwen3-32B",
    "engine_type": "async",
    "token_stream_available": true,
    "model_status": "ready",
    "total_requests": 1000,
    "successful_requests": 995,
    "failed_requests": 5,
    "active_requests": 2,
    "avg_latency_ms": 1234.56,
    "uptime_seconds": 3600.5
  }
}
```

### GPU 资源响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "gpu_count": 1,
    "gpus": [
      {
        "gpu_id": 0,
        "gpu_name": "NVIDIA A100-SXM4-80GB",
        "total_memory_mb": 81920,
        "used_memory_mb": 65536,
        "free_memory_mb": 16384,
        "memory_utilization": 0.8,
        "gpu_utilization": 0.65,
        "temperature": 55.0
      }
    ]
  }
}
```

### 模型重载响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "success": true,
    "message": "Model reloaded successfully",
    "model_name": "Qwen3-32B",
    "reload_time_ms": 12345.67
  }
}
```

---

## 统一响应格式

所有接口返回统一的 JSON 格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误码说明

| code | 说明 |
|------|------|
| 0 | 成功 |
| 1001 | 参数验证失败 |
| 2001 | 模型未加载 |
| 2002 | 模型推理失败 |
| 5001 | 内部服务错误 |

### 错误响应示例

```json
{
  "code": 2001,
  "message": "Async engine does not support synchronous requests. Please use streaming mode (stream=true) for async engine.",
  "data": null
}
```

---

## 使用示例

### 单轮图像识别（非流式）
```json
POST /v1/vision/completions
{
  "messages": [
    {
      "role": "system",
      "content": "你是一个专业的停车场检测智能体。"
    },
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "请识别图中所有车辆 /think"},
        {"type": "image_url", "image_url": {"url": "<图片base64>"}}
      ]
    }
  ],
  "max_tokens": 400
}
```

### 流式输出示例
```json
POST /v1/vision/completions
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "描述这张图片"},
        {"type": "image_url", "image_url": {"url": "<图片base64>"}}
      ]
    }
  ],
  "stream": true,
  "stream_options": {
    "mode": "token"
  }
}
```

### 多图时序分析
```json
POST /v1/vision/completions
{
  "messages": [
    {
      "role": "system",
      "content": "分析停车场变化趋势"
    },
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "按顺序描述停车场状态变化："},
        {"type": "image_url", "image_url": {"url": "<图片1>"}},
        {"type": "image_url", "image_url": {"url": "<图片2>"}},
        {"type": "image_url", "image_url": {"url": "<图片3>"}}
      ]
    }
  ],
  "max_tokens": 600
}
```

### 快速图片描述
```json
POST /v1/vision/analyze
{
  "image": "<图片base64>",
  "prompt": "请描述这张图片"
}
```

---

## LLM 使用示例

### 简单对话
```json
POST /v1/chat/completions
{
  "messages": [
    {"role": "user", "content": "你好，请介绍一下你自己"}
  ],
  "max_tokens": 256
}
```

### 带系统提示的多轮对话
```json
POST /v1/chat/completions
{
  "messages": [
    {"role": "system", "content": "你是一个专业的编程助手，擅长 Python 开发。"},
    {"role": "user", "content": "如何用 Python 读取 JSON 文件？"},
    {"role": "assistant", "content": "可以使用 json 模块..."},
    {"role": "user", "content": "如果文件很大怎么办？"}
  ],
  "max_tokens": 512,
  "temperature": 0.7
}
```

### LLM 流式输出
```json
POST /v1/chat/completions
{
  "messages": [
    {"role": "user", "content": "写一首关于春天的诗"}
  ],
  "stream": true,
  "stream_options": {
    "mode": "token"
  },
  "max_tokens": 256
}
```

### 文本补全
```json
POST /v1/completions
{
  "prompt": "人工智能的三大核心技术是：",
  "max_tokens": 200,
  "temperature": 0.8
}
```

---

## Embedding 使用示例

### 单条文本向量化
```json
POST /v1/embeddings
{
  "input": "这是一段需要转换为向量的文本"
}
```

### 批量文本向量化
```json
POST /v1/embeddings
{
  "input": [
    "文档1：人工智能的发展历程",
    "文档2：机器学习的基本概念",
    "文档3：深度学习的应用场景"
  ]
}
```

### 相似度计算示例（客户端代码）
```python
import numpy as np
import requests

# 获取两段文本的向量
response = requests.post(
    "http://localhost:8800/v1/embeddings",
    json={"input": ["文本A", "文本B"]}
)
data = response.json()["data"]["data"]
vec_a = np.array(data[0]["embedding"])
vec_b = np.array(data[1]["embedding"])

# 计算余弦相似度
similarity = np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
print(f"相似度: {similarity:.4f}")
```

---
