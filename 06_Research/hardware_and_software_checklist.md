# 硬件环境与软件安装检查清单

> 本清单用于 AIGC 视频项目启动前的环境准备。  
> 以 ShotFlow /《奇点回响》为示例，实际项目请按技术栈调整。

---

## 一、硬件环境检查

| 检查项 | 最低要求 | 推荐配置 | 状态 |
|--------|----------|----------|------|
| GPU | NVIDIA RTX 3090 24GB | RTX 4090 24GB × 1–2 | □ |
| 显存 | 24GB | 24GB+ | □ |
| 内存 | 32GB | 64GB+ | □ |
| 系统盘 | 512GB SSD | 1TB NVMe SSD | □ |
| 数据盘 | 2TB HDD | 2TB+ NVMe SSD | □ |
| 操作系统 | Windows 10 / Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 LTS | □ |
| CUDA 版本 | 11.8 | 12.x | □ |
| 网络 | 100Mbps | 500Mbps+（下载大模型） | □ |

### 硬件检查命令

```bash
# 查看 GPU 信息
nvidia-smi

# 查看 CUDA 版本
nvcc --version

# 查看内存
free -h  # Linux
systeminfo | findstr "Total Physical Memory"  # Windows

# 查看磁盘空间
df -h  # Linux
wmic logicaldisk get size,freespace,caption  # Windows
```

---

## 二、软件安装清单

### 2.1 核心生成环境

| 软件 | 版本/来源 | 用途 | 状态 |
|------|-----------|------|------|
| ComfyUI | 最新版 | 图像与视频生成工作流 | □ |
| Python | 3.12 | 运行环境 | □ |
| PyTorch | 2.x (CUDA 版) | 深度学习框架 | □ |
| CUDA Toolkit | 12.x | GPU 加速 | □ |
| Git | 最新版 | 版本控制 | □ |

### 2.2 模型与节点

| 模型/节点 | 存放路径 | 状态 |
|-----------|----------|------|
| FLUX.1-Kontext-dev / FP8 / FP4 | `ComfyUI/models/diffusion_models/` | □ |
| Wan2.2-I2V-A14B FP8 | `ComfyUI/models/diffusion_models/` | □ |
| Wan2.2 VAE | `ComfyUI/models/vae/` | □ |
| umt5_xxl_fp8_e4m3fn_scaled | `ComfyUI/models/text_encoders/` | □ |
| IPAdapter / PuLID 节点与模型 | 按节点要求 | □ |
| ComfyUI-Manager | 自定义节点 | □ |

### 2.3 后期与音频

| 软件 | 版本/来源 | 用途 | 状态 |
|------|-----------|------|------|
| 剪映专业版 | 最新版 | 粗剪 | □ |
| DaVinci Resolve | 18/19 | 精剪、调色、混音 | □ |
| Topaz Video AI | 最新订阅版 | 超分与降噪 | □ |
| After Effects | 2024/2025 | 逐帧修复 | □ |
| Photoshop | 2024/2025 | 静态修复与封面 | □ |
| ElevenLabs | 网页/API | 配音 | □ |
| Suno / Udio | 网页/API | 配乐 | □ |

### 2.4 协作与脚本

| 工具 | 用途 | 状态 |
|------|------|------|
| VS Code / Cursor | 代码编辑 | □ |
| 飞书/钉钉/企业微信 | 团队沟通 | □ |
| 共享云盘 | 资产备份 | □ |
| GitHub / GitCode 账号 | 代码托管 | □ |

---

## 三、环境验证

```bash
# 1. 进入 ComfyUI 目录
cd ~/ComfyUI

# 2. 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 3. 运行预飞行检查
python /workspace/ShotFlow/08_Automation/preflight_check.py

# 4. 运行性能基准测试
python /workspace/ShotFlow/08_Automation/benchmark.py
```

---

## 四、检查结果

| 检查人 | 日期 | 结果 |
|--------|------|------|
| | | □ 通过 / □ 有条件通过 / □ 不通过 |

### 备注

```
（记录发现的问题与解决方案）
```

---

> 本文件为模板，实际项目请按真实硬件配置与软件版本调整。
