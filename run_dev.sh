#!/bin/bash
# SupportPilot 开发服务器启动脚本
# 用法: bash run_dev.sh

set -e

# 激活虚拟环境
source venv/bin/activate

# 检查 .env
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，使用默认配置"
fi

# 创建日志目录
mkdir -p logs

# 设置环境变量（修复 macOS CoreML 错误）
export ORT_DISABLE_COREML=1

echo "🚀 启动 SupportPilot 开发服务器..."
echo "📍 http://localhost:5000"

# 启动开发服务器
python wsgi.py
