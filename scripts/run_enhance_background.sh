#!/bin/bash
# 后台运行 AI 增强处理（从新到久）
# Usage: nohup ./scripts/run_enhance_background.sh > enhance.log 2>&1 &

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 激活虚拟环境
source "$PROJECT_DIR/.venv/bin/activate"

# 设置环境变量
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.deepseek.com/v1}"
export MODEL_NAME="${MODEL_NAME:-deepseek-chat}"
export LANGUAGE="${LANGUAGE:-Chinese}"
export MAX_WORKERS="${MAX_WORKERS:-4}"

# 检查 API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "错误: 未设置 OPENAI_API_KEY"
    exit 1
fi

echo "======================================"
echo "开始 AI 增强处理"
echo "时间: $(date)"
echo "API: $OPENAI_BASE_URL"
echo "模型: $MODEL_NAME"
echo "语言: $LANGUAGE"
echo "并发数: $MAX_WORKERS"
echo "处理顺序: 从新到久"
echo "======================================"

# 运行处理（从新到久）
cd "$PROJECT_DIR"
python3 scripts/batch_ai_enhance.py \
    --reverse \
    --max-workers "$MAX_WORKERS" \
    --language "$LANGUAGE"

echo "======================================"
echo "处理完成"
echo "时间: $(date)"
echo "======================================"
