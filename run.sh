#!/bin/bash
# AI Voice Inputer 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查虚拟环境
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "错误: 虚拟环境不存在，请先运行安装脚本"
    echo "  ./scripts/install.sh"
    exit 1
fi

# 激活虚拟环境
source "$SCRIPT_DIR/venv/bin/activate"

# 运行主程序
python -m src.main "$@"
