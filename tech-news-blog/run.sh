#!/bin/bash
#
# Tech News Blog - 每日科技新闻聚合
# 使用方式: ./run.sh [选项]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

# 加载 shell 配置以获取环境变量
for rc in ~/.zshrc ~/.bashrc ~/.bash_profile; do
    if [ -f "$rc" ] && [ -r "$rc" ]; then
        source "$rc" 2>/dev/null || true
        break
    fi
done

cd "$SCRIPT_DIR"

# 显示帮助
show_help() {
    cat << 'EOF'
使用方法: ./run.sh [选项]

选项:
    --output-only       仅输出生成的Markdown内容（默认）
    --save <路径>       保存Markdown到指定文件
    --sources <源列表>  指定新闻源（如：hackernews github-trending）
    --count <数量>      每源抓取数量（默认：15）
    --limit <数量>      最终精选数量（默认：10）
    --max-images <数量> 最大图片数（默认：10）
    --no-images         不处理图片
    --help              显示此帮助

示例:
    ./run.sh                                # 默认执行
    ./run.sh --output-only                  # 仅输出生成的内容
    ./run.sh --save ~/news.md               # 保存到文件
    ./run.sh --sources hackernews lobsters  # 指定源
    ./run.sh --no-images                    # 不处理图片

环境变量:
    ANTHROPIC_API_KEY  或  OPENAI_API_KEY   # 用于翻译（必需）
    R2_UPLOAD_CONFIG                        # R2配置文件路径（用于图片上传）
EOF
}

# 检查 Python
if ! command -v "$PYTHON" &> /dev/null; then
    echo "错误: 未找到 Python ($PYTHON)"
    exit 1
fi

# 检查依赖
if [ ! -f "$SCRIPT_DIR/scripts/generate.py" ]; then
    echo "错误: 未找到 generate.py 脚本"
    exit 1
fi

# 默认参数
ARGS=("--output-only")

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --output-only)
            # 默认行为，无需额外处理
            shift
            ;;
        --save|--sources|--count|--limit|--max-images|--no-images)
            ARGS+=("$1")
            if [[ $2 != --* ]] && [[ -n $2 ]]; then
                ARGS+=("$2")
                shift 2
            else
                shift
            fi
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# 执行主脚本
echo "启动科技新闻聚合..."
echo "================================"
"$PYTHON" "$SCRIPT_DIR/scripts/generate.py" "${ARGS[@]}"
