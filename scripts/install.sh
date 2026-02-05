#!/bin/bash
# AI Voice Inputer 安装脚本
# Ubuntu 24.04

set -e

echo "=========================================="
echo "  AI Voice Inputer 安装脚本"
echo "  Ubuntu 24.04 AI 语音输入法"
echo "=========================================="
echo ""

# 检查是否是 Ubuntu
if [ ! -f /etc/os-release ]; then
    echo "错误: 无法检测操作系统"
    exit 1
fi

source /etc/os-release
echo "检测到系统: $PRETTY_NAME"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "→ $1"; }

# 检查命令是否存在
command_exists() {
    command -v "$1" &> /dev/null
}

# 1. 安装系统依赖
echo ""
echo "1. 安装系统依赖..."
echo "----------------------------------------"

sudo apt update

# 必需的系统包
PACKAGES=(
    "python3"
    "python3-pip"
    "python3-venv"
    "portaudio19-dev"
    "ffmpeg"
    "sox"
    "xdotool"
    "libnotify-bin"
)

for pkg in "${PACKAGES[@]}"; do
    if dpkg -l | grep -q "^ii  $pkg"; then
        print_success "$pkg 已安装"
    else
        print_info "正在安装 $pkg..."
        sudo apt install -y "$pkg"
        print_success "$pkg 安装完成"
    fi
done

# 2. 创建 Python 虚拟环境
echo ""
echo "2. 创建 Python 虚拟环境..."
echo "----------------------------------------"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"

if [ -d "$VENV_DIR" ]; then
    print_warning "虚拟环境已存在: $VENV_DIR"
else
    print_info "创建虚拟环境: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    print_success "虚拟环境创建完成"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

# 3. 安装 Python 依赖
echo ""
echo "3. 安装 Python 依赖..."
echo "----------------------------------------"

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r "$PROJECT_DIR/requirements.txt"

print_success "Python 依赖安装完成"

# 4. 下载 Whisper 模型
echo ""
echo "4. 下载语音识别模型..."
echo "----------------------------------------"

print_info "首次运行会自动下载模型，请稍后..."
print_info "模型将缓存到 ~/.cache/huggingface/"

# 预下载模型 (可选)
read -p "是否现在预下载 Whisper medium 模型? (推荐，约 1.5GB) [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "正在下载模型..."
    python3 -c "
from faster_whisper import WhisperModel
print('正在下载 medium 模型...')
model = WhisperModel('medium', device='auto', compute_type='int8')
print('模型下载完成!')
"
    print_success "模型下载完成"
else
    print_warning "跳过模型下载，首次运行时会自动下载"
fi

# 5. 创建启动脚本
echo ""
echo "5. 创建启动脚本..."
echo "----------------------------------------"

LAUNCHER="$PROJECT_DIR/voice-inputer"
cat > "$LAUNCHER" << EOF
#!/bin/bash
# AI Voice Inputer 启动脚本

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
source "\$SCRIPT_DIR/venv/bin/activate"
python -m src.main "\$@"
EOF

chmod +x "$LAUNCHER"
print_success "启动脚本创建完成: $LAUNCHER"

# 6. 创建桌面快捷方式
echo ""
echo "6. 创建桌面快捷方式..."
echo "----------------------------------------"

DESKTOP_FILE="$HOME/.local/share/applications/ai-voice-inputer.desktop"
mkdir -p "$(dirname "$DESKTOP_FILE")"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=AI Voice Inputer
Comment=Ubuntu AI 语音输入法
Exec=$LAUNCHER
Icon=audio-input-microphone
Terminal=false
Type=Application
Categories=Utility;Accessibility;
Keywords=voice;speech;input;whisper;ai;
EOF

print_success "桌面快捷方式创建完成"

# 7. 创建用户配置目录
echo ""
echo "7. 创建用户配置目录..."
echo "----------------------------------------"

CONFIG_DIR="$HOME/.config/ai-voice-inputer"
LOG_DIR="$HOME/.local/share/ai-voice-inputer/logs"

mkdir -p "$CONFIG_DIR"
mkdir -p "$LOG_DIR"

# 复制默认配置
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cp "$PROJECT_DIR/config/config.yaml" "$CONFIG_DIR/config.yaml"
    print_success "默认配置已复制到: $CONFIG_DIR/config.yaml"
else
    print_warning "配置文件已存在，跳过复制"
fi

# 8. 创建 systemd 用户服务 (可选)
echo ""
echo "8. 创建系统服务 (可选)..."
echo "----------------------------------------"

read -p "是否创建 systemd 用户服务以便开机自启? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SERVICE_DIR"
    
    cat > "$SERVICE_DIR/ai-voice-inputer.service" << EOF
[Unit]
Description=AI Voice Inputer - Ubuntu AI 语音输入法
After=graphical-session.target

[Service]
Type=simple
ExecStart=$LAUNCHER
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    print_success "systemd 服务创建完成"
    print_info "启用开机自启: systemctl --user enable ai-voice-inputer"
    print_info "启动服务: systemctl --user start ai-voice-inputer"
    print_info "查看状态: systemctl --user status ai-voice-inputer"
else
    print_warning "跳过系统服务创建"
fi

# 完成
echo ""
echo "=========================================="
echo "  安装完成!"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  1. 启动: $LAUNCHER"
echo "  2. 按住 Win + Ctrl 开始语音输入"
echo "  3. 松开按键，文字自动输入到光标位置"
echo ""
echo "配置文件: $CONFIG_DIR/config.yaml"
echo "日志目录: $LOG_DIR"
echo ""
print_success "祝您使用愉快!"
