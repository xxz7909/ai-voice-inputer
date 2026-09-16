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

> 首次启动会从 HuggingFace 下载模型，国内网络建议使用镜像预先下载：
> `HF_ENDPOINT=https://hf-mirror.com ./run.sh`

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
  vad:
    enabled: true
    # VAD 语音判定阈值 (0~1): 越大越严格
    # 识别经常为空/丢字时调小, 环境噪声大时调大
    silence_threshold: 0.3
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

### 桌面通知 (可选)

默认关闭，识别过程中不弹任何提示，只把文字输入到光标处。若需要录音/识别状态提示：

```yaml
notification:
  enabled: true
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

### 5. 启动卡在「正在加载语音识别模型」

程序启动时会先检查模型缓存。如果本地已有缓存但网络无法访问 `huggingface.co`
（国内网络常见），旧版本会一直卡住。当前版本已改为**优先使用本地缓存**，
正常应在 1~2 秒内加载完成。

更换模型（如 `small` → `large-v3`）时需要使用镜像预先下载：

```bash
HF_ENDPOINT=https://hf-mirror.com python -c \
  "from faster_whisper.utils import download_model; print(download_model('large-v3'))"
```

下载完成后再次启动即可离线加载。

### 6. 启动报 DISPLAY / X server 错误

热键监听 (pynput)、文字输入 (xdotool) 和桌面通知都依赖 X11。如果看到
「无法连接 X11 显示器」或「无法加载键盘监听模块」，说明 `DISPLAY` 不可用：

- 程序会自动扫描 `/tmp/.X11-unix` 并切换到可用的显示器，多数情况可自愈；
- 若使用 systemd 自启，`DISPLAY`/`XAUTHORITY` 会由 `install.sh` 按安装时的
  会话写入。切换登录会话后失效可执行：

```bash
systemctl --user import-environment DISPLAY XAUTHORITY
systemctl --user restart ai-voice-inputer
```

### 7. 不说话也会自动上屏一段文字

Whisper 在静音或纯噪声上会产生幻觉文本（例如「字幕by索兰娅」）。程序默认先做
三层判断，任何一层判定"没有语音"就不会上屏：音频长度需超过 `min_speech_duration`、
Silero VAD 需检出人声、识别片段的 `no_speech_prob` 需低于阈值。

注意 VAD 只做"有没有人声"的判断，**不会裁剪音频**：裁剪会切掉弱读音节，导致
识别丢字。

如果识别结果经常为空或丢字（多见于麦克风电平偏低），可放宽 VAD：

```yaml
asr:
  vad:
    enabled: true
    silence_threshold: 0.25   # 默认 0.3, 调小更宽松
```

如果环境噪声大、容易误识别，则调大该值（如 `0.5`）。

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
