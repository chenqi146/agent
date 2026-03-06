#!/bin/bash

# QJZH vLLM Application 启动脚本
# 用法: ./running.sh [配置文件路径]

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 默认配置文件路径
CONFIG_FILE="${1:-$SCRIPT_DIR/../resources/application.yaml}"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件不存在: $CONFIG_FILE"
    exit 1
fi

echo "=================================================="
echo "  QJZH vLLM Application"
echo "=================================================="
echo "配置文件: $CONFIG_FILE"
echo "工作目录: $SCRIPT_DIR"
echo "=================================================="

# 切换到脚本目录
cd "$SCRIPT_DIR"

# 设置环境变量（解决 CUDA/Triton 编译问题）
export VLLM_DISABLE_COMPILE=1
export TORCH_COMPILE_DISABLE=1
export TORCHINDUCTOR_DISABLE=1
export TRITON_DISABLE_COMPILATION=1

# CUDA 库路径
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/lib64/stubs:$LD_LIBRARY_PATH
export LIBRARY_PATH=/usr/local/cuda/lib64/stubs:$LIBRARY_PATH

# 启动应用
# GPU 分配: 0,1,2 给 VLM (32B 三卡并行), 3 给 Reranker + Embedding
export CUDA_VISIBLE_DEVICES=0,1,2,3
python3 main.py -c "$CONFIG_FILE"
