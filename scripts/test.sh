#!/bin/bash
# 快速测试脚本 - 测试各个组件是否正常工作

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================"
echo "  AI Voice Inputer 组件测试"
echo "========================================"
echo ""

# 激活虚拟环境
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
else
    echo -e "${RED}错误: 虚拟环境不存在${NC}"
    exit 1
fi

# 测试 Python 导入
echo "1. 测试 Python 依赖..."
python3 -c "
import sys
tests = [
    ('faster_whisper', 'Faster Whisper'),
    ('sounddevice', 'SoundDevice'),
    ('numpy', 'NumPy'),
    ('pynput', 'Pynput'),
    ('yaml', 'PyYAML'),
    ('requests', 'Requests'),
]

all_ok = True
for module, name in tests:
    try:
        __import__(module)
        print(f'  ✓ {name}')
    except ImportError as e:
        print(f'  ✗ {name}: {e}')
        all_ok = False

sys.exit(0 if all_ok else 1)
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  所有 Python 依赖正常${NC}"
else
    echo -e "${RED}  部分依赖缺失${NC}"
fi
echo ""

# 测试系统命令
echo "2. 测试系统命令..."
commands=("xdotool" "notify-send" "ffmpeg" "sox")
for cmd in "${commands[@]}"; do
    if command -v "$cmd" &> /dev/null; then
        echo -e "  ${GREEN}✓ $cmd${NC}"
    else
        echo -e "  ${RED}✗ $cmd (未安装)${NC}"
    fi
done
echo ""

# 测试音频设备
echo "3. 测试音频设备..."
python3 -c "
import sounddevice as sd
devices = sd.query_devices()
print(f'  可用音频设备: {len(devices)} 个')
default_input = sd.default.device[0]
if default_input is not None:
    device_info = sd.query_devices(default_input)
    print(f'  默认输入设备: {device_info[\"name\"]}')
else:
    print('  警告: 没有找到默认输入设备')
"
echo ""

# 测试 Whisper 模型
echo "4. 测试 Whisper 模型..."
python3 -c "
import os
cache_dir = os.path.expanduser('~/.cache/huggingface/hub')
if os.path.exists(cache_dir):
    models = [d for d in os.listdir(cache_dir) if 'whisper' in d.lower()]
    if models:
        print(f'  已缓存的模型: {len(models)} 个')
        for m in models[:3]:
            print(f'    - {m}')
    else:
        print('  提示: 尚未下载 Whisper 模型，首次运行时会自动下载')
else:
    print('  提示: 尚未下载 Whisper 模型，首次运行时会自动下载')
"
echo ""

# 测试配置文件
echo "5. 测试配置文件..."
config_file="$HOME/.config/ai-voice-inputer/config.yaml"
if [ -f "$config_file" ]; then
    echo -e "  ${GREEN}✓ 用户配置文件存在${NC}"
else
    echo "  提示: 用户配置文件不存在，将使用默认配置"
fi

default_config="$PROJECT_DIR/config/config.yaml"
if [ -f "$default_config" ]; then
    echo -e "  ${GREEN}✓ 默认配置文件存在${NC}"
else
    echo -e "  ${RED}✗ 默认配置文件缺失${NC}"
fi
echo ""

echo "========================================"
echo "  测试完成"
echo "========================================"
