# AI Voice Inputer

**Ubuntu 24.04 AI 语音输入法**

按住 `Win + Ctrl` 在任意界面唤醒语音输入，松开按键后文字自动输入到光标位置。

## ✨ 特性

- 🎙️ **全局热键唤醒** - 按住 Win+Ctrl 开始录音，松开自动识别输入
- 🧠 **本地 AI 识别** - 使用 faster-whisper，离线运行，隐私安全
- 🇨🇳 **中文优化** - 专为中文语音识别优化
- ⚡ **低延迟** - 识别延迟 < 500ms
- 🔧 **可配置** - 支持模型切换、热键自定义、LLM 增强
- 📦 **开箱即用** - 一键安装，无需复杂配置

## 📋 系统要求

- **操作系统**: Ubuntu 24.04 (或其他基于 Debian 的 Linux)
- **Python**: 3.10+
- **显示服务器**: X11 (Wayland 需要额外配置)
- **GPU** (可选): NVIDIA GPU + CUDA 可大幅提升识别速度

### 硬件推荐

| 配置 | 推荐模型 | 识别速度 |
|------|----------|----------|
| 无 GPU | `small` | ~1.5x 实时 |
| GTX 1060+ | `medium` | ~5x 实时 |
| RTX 3060+ | `large-v3` | ~10x 实时 |

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/ai-voice-inputer.git
cd ai-voice-inputer
```

### 2. 安装

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

安装脚本会自动：
- 安装系统依赖 (xdotool, ffmpeg, portaudio 等)
- 创建 Python 虚拟环境
- 安装 Python 包
- 创建启动脚本和桌面快捷方式

### 3. 运行

```bash
./run.sh
```

或使用应用菜单中的 "AI Voice Inputer" 启动。

### 4. 使用

1. 将光标放到任意输入框
2. 按住 `Win + Ctrl` 键
3. 开始说话
4. 松开按键，文字自动输入

## ⚙️ 配置

配置文件位置: `~/.config/ai-voice-inputer/config.yaml`

### 模型选择

```yaml
asr:
  # 可选: tiny, base, small, medium, large-v3
  model: "medium"
  device: "auto"  # auto, cpu, cuda
  language: "zh"
```

### 热键配置

```yaml
hotkey:
  keys:
    - "ctrl"
    - "cmd"  # Win/Super 键
```

### LLM 增强 (可选)

启用大模型对识别结果进行纠错：

```yaml
llm:
  enabled: true
  api_url: "http://localhost:8000/v1/chat/completions"
  model: "qwen2.5-7b"
```

## 📁 项目结构

```
ai-voice-inputer/
├── config/
│   └── config.yaml       # 默认配置文件
├── scripts/
│   ├── install.sh        # 安装脚本
│   ├── test.sh           # 测试脚本
│   └── ai-voice-inputer.service  # systemd 服务
├── src/
│   ├── __init__.py
│   ├── main.py           # 主程序
│   ├── config_manager.py # 配置管理
│   ├── asr_service.py    # 语音识别服务
│   ├── audio_recorder.py # 音频录制
│   ├── hotkey_listener.py # 热键监听
│   ├── text_injector.py  # 文字注入
│   ├── llm_enhancer.py   # LLM 增强
│   └── notifier.py       # 桌面通知
├── requirements.txt      # Python 依赖
├── run.sh               # 启动脚本
└── README.md
```

## 🔧 高级配置

### 开机自启

```bash
# 启用
systemctl --user enable ai-voice-inputer

# 启动
systemctl --user start ai-voice-inputer

# 查看状态
systemctl --user status ai-voice-inputer

# 查看日志
journalctl --user -u ai-voice-inputer -f
```

### Wayland 支持

Wayland 环境下需要使用 `ydotool` 替代 `xdotool`：

```bash
# 安装 ydotool
sudo apt install ydotool

# 修改配置
# ~/.config/ai-voice-inputer/config.yaml
input:
  method: "ydotool"
```

### 使用本地 LLM

如果你有本地部署的 vLLM 或 Ollama：

```yaml
llm:
  enabled: true
  api_url: "http://localhost:8000/v1/chat/completions"
  model: "qwen2.5-7b"
```

## 🐛 故障排除

### 1. 没有声音输入

```bash
# 检查麦克风
arecord -l

# 测试录音
arecord -d 5 test.wav && aplay test.wav
```

### 2. xdotool 无法输入中文

```bash
# 确保输入法正在运行
ibus daemon -drx
# 或
fcitx5 &
```

### 3. 识别速度慢

- 使用更小的模型: `small` 或 `base`
- 确保使用 GPU: 检查 CUDA 是否可用

```python
import torch
print(torch.cuda.is_available())
```

### 4. 热键不生效

某些桌面环境可能会拦截 Win+Ctrl 组合键，可以修改为其他热键：

```yaml
hotkey:
  keys:
    - "ctrl"
    - "alt"
```

## 📝 开发计划

- [ ] **Phase 2**: 流式识别 (边说边出字)
- [ ] **Phase 3**: Fcitx5 输入法引擎集成
- [ ] 系统托盘图标
- [ ] 多语言支持
- [ ] 自定义唤醒词

## 🙏 致谢

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - 高效的 Whisper 实现
- [pynput](https://github.com/moses-palmer/pynput) - 键盘监听
- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别模型

## 📄 许可证

MIT License
