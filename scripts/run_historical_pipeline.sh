#!/bin/bash
# math.AP 历史数据处理统一入口脚本
# Usage: ./scripts/run_historical_pipeline.sh [extract|enhance|all|stats|clean]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="${PROJECT_DIR}/data"
HISTORY_DIR="${PROJECT_DIR}/arxiv_history_metadata"
METADATA_FILE="${HISTORY_DIR}/arxiv-metadata-oai-snapshot.json"
LANGUAGE="${LANGUAGE:-Chinese}"
MAX_WORKERS="${MAX_WORKERS:-4}"
CATEGORIES="${CATEGORIES:-math.AP}"

# 打印帮助信息
show_help() {
    echo "math.AP 历史数据处理脚本"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  extract     从历史 metadata 提取数据（增量模式）"
    echo "  enhance     对提取的数据进行 AI 增强（断点续传）"
    echo "  all         执行完整流程（extract + enhance）"
    echo "  stats       显示处理统计信息"
    echo "  clean       清理进度文件，强制重新处理"
    echo "  help        显示此帮助信息"
    echo ""
    echo "Environment Variables:"
    echo "  OPENAI_API_KEY    API 密钥（必需）"
    echo "  OPENAI_BASE_URL   API 基础 URL（可选）"
    echo "  LANGUAGE          输出语言，默认 Chinese"
    echo "  MAX_WORKERS       AI 增强并发数，默认 4"
    echo "  CATEGORIES        要处理的分类，默认 math.AP"
    echo ""
    echo "Examples:"
    echo "  $0 extract                    # 仅提取数据"
    echo "  $0 enhance                    # 仅 AI 增强"
    echo "  $0 all                        # 完整流程"
    echo "  MAX_WORKERS=8 $0 enhance      # 使用 8 并发进行 AI 增强"
    echo ""
}

# 检查环境
check_env() {
    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误: 未找到 python3${NC}"
        exit 1
    fi
    
    # 检查 metadata 文件
    if [ ! -f "$METADATA_FILE" ]; then
        echo -e "${RED}错误: 未找到 metadata 文件: $METADATA_FILE${NC}"
        echo "请确保 Kaggle 下载的文件放在 arxiv_history_metadata/ 目录下"
        exit 1
    fi
    
    echo -e "${GREEN}✓ 环境检查通过${NC}"
}

# 检查 API 密钥
check_api_key() {
    if [ -z "$OPENAI_API_KEY" ]; then
        echo -e "${RED}错误: 未设置 OPENAI_API_KEY 环境变量${NC}"
        echo "请先设置: export OPENAI_API_KEY=your_key"
        exit 1
    fi
    echo -e "${GREEN}✓ API 密钥已设置${NC}"
}

# 提取数据
cmd_extract() {
    echo -e "${BLUE}=== 步骤 1: 提取历史数据 ===${NC}"
    echo "分类: $CATEGORIES"
    echo "输出目录: $DATA_DIR"
    echo ""
    
    python3 "${SCRIPT_DIR}/extract_historical_data.py" \
        --input "$METADATA_FILE" \
        --output "$DATA_DIR" \
        --categories $CATEGORIES
    
    echo ""
    echo -e "${GREEN}✓ 数据提取完成${NC}"
}

# AI 增强
cmd_enhance() {
    echo -e "${BLUE}=== 步骤 2: AI 增强处理 ===${NC}"
    echo "语言: $LANGUAGE"
    echo "并发数: $MAX_WORKERS"
    echo ""
    
    check_api_key
    
    # 先显示统计
    python3 "${SCRIPT_DIR}/batch_ai_enhance.py" --stats
    echo ""
    
    # 开始处理
    python3 "${SCRIPT_DIR}/batch_ai_enhance.py" \
        --data-dir "$DATA_DIR" \
        --max-workers "$MAX_WORKERS" \
        --language "$LANGUAGE"
    
    echo ""
    echo -e "${GREEN}✓ AI 增强完成${NC}"
}

# 显示统计
cmd_stats() {
    echo -e "${BLUE}=== 处理统计 ===${NC}"
    
    # 数据提取统计
    if [ -f "$METADATA_FILE" ]; then
        echo ""
        echo "历史数据文件:"
        ls -lh "$METADATA_FILE" | awk '{print "  大小:", $5, "  修改时间:", $6, $7, $8}'
    fi
    
    # AI 增强统计
    echo ""
    python3 "${SCRIPT_DIR}/batch_ai_enhance.py" --stats
    
    # 文件统计
    echo ""
    echo "数据目录统计:"
    echo "  原始 JSONL: $(ls -1 ${DATA_DIR}/*.jsonl 2>/dev/null | grep -v "_AI_enhanced_" | wc -l) 个"
    echo "  AI 增强: $(ls -1 ${DATA_DIR}/*_AI_enhanced_*.jsonl 2>/dev/null | wc -l) 个"
    
    # 计算 math.AP 文件数
    local math_ap_count=$(ls -1 ${DATA_DIR}/*.jsonl 2>/dev/null | wc -l)
    if [ "$math_ap_count" -gt 0 ]; then
        echo "  总 JSONL: $math_ap_count 个"
    fi
}

# 清理进度
cmd_clean() {
    echo -e "${YELLOW}=== 清理进度文件 ===${NC}"
    
    read -p "确定要清理进度文件吗？这将导致重新处理所有数据。[y/N] " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 "${SCRIPT_DIR}/batch_ai_enhance.py" --reset-progress
        echo -e "${GREEN}✓ 进度已重置${NC}"
    else
        echo "已取消"
    fi
}

# 完整流程
cmd_all() {
    check_env
    cmd_extract
    echo ""
    cmd_enhance
    echo ""
    echo -e "${GREEN}=== 全部流程完成 ===${NC}"
}

# 主逻辑
main() {
    case "${1:-}" in
        extract)
            check_env
            cmd_extract
            ;;
        enhance)
            check_env
            cmd_enhance
            ;;
        all)
            cmd_all
            ;;
        stats)
            cmd_stats
            ;;
        clean)
            cmd_clean
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            echo "使用 '$0 help' 查看帮助"
            exit 1
            ;;
    esac
}

main "$@"
