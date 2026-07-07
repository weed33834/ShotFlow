# 常见问题

[English](./TROUBLESHOOTING.md) | 中文（当前）

> 本文件汇总使用 ShotFlow 过程中可能遇到的问题及解决方案。

---

## 环境部署

### Q: `deploy_comfyui.sh` 运行失败

**可能原因**：
- 没有 NVIDIA GPU 或驱动未安装；
- Git 未安装或网络不通；
- Python 版本低于 3.10。

**解决**：
- 确认 GPU 和驱动：`nvidia-smi`；
- 确认 Python 版本：`python3 --version`；
- 检查网络，必要时使用 HuggingFace 镜像或预下载模型。

---

### Q: `preflight_check.py` 报告 GPU 不可用

**可能原因**：
- 当前机器没有 CUDA；
- PyTorch 安装了 CPU 版本。

**解决**：
- 有 GPU：重新安装 CUDA 版 PyTorch，参考 https://pytorch.org；
- 无 GPU：改用云端 API 方案，只运行脚本和后期流程。

---

## 角色一致性

### Q: 艾娃在不同镜头里长得不一样

**解决**：
- 检查角色圣经是否固定了所有锚点；
- 确认 IPAdapter 参考图包含正/侧/背多角度；
- 提高 IPAdapter weight 到 0.8–1.0；
- 在负面提示词中加入 `inconsistent hairstyle, wrong clothing`；
- 做盲测，不达标的镜头重跑。

---

### Q: 关键帧出现多手指、畸形面部

**解决**：
- 负面提示词加入 `extra fingers, mutated hands, deformed face`；
- 降低 CFG 或增加采样步数；
- 使用 ADetailer 或类似节点做局部修复。

---

## 视频生成

### Q: 视频闪烁严重

**解决**：
- 检查关键帧与视频提示词是否一致；
- 使用 Wan2.2 Low Noise 专家修复崩坏帧；
- 降低运动幅度提示词；
- 输出后用 Topaz 或 FFmpeg 做时域降噪。

---

### Q: 可灵 API 调用失败

**解决**：
- 确认 `.env` 中 `KLING_API_KEY` 已配置；
- 检查 API 额度是否充足；
- 查看可灵官方文档，确认 API 版本和参数格式。

---

## 后期与音频

### Q: ElevenLabs 配音情绪不对

**解决**：
- 更换 voice ID，选择更贴近角色设定的声音；
- 调整 stability 和 similarity 参数；
- 在台词中加入情绪标注，如 `[whisper]`、`[angry]`。

---

### Q: Suno 生成音乐风格不符

**解决**：
- 在提示词中明确风格、情绪、乐器；
- 使用参考音频功能；
- 多生成几首挑选。

---

## 仓库与协作

### Q: `sync_repos.sh` 推送失败

**解决**：
- 确认 `.git/config` 中远程仓库 URL 不含硬编码 Token（安全做法：使用 SSH 或 Git 凭据管理器）；
  - HTTPS + 凭据管理器：`git config --global credential.helper store`（首次输入后自动保存）
  - SSH：`git remote set-url github git@github.com:MS33834/ShotFlow.git`
- 对于 GitCode，URL 保持 `https://gitcode.com/badhope/ShotFlow.git`，Token 由凭据管理器提供；
- 检查网络连接。

---

### Q: 不小心把 API 密钥提交到仓库

**解决**：
- 立即撤销该密钥；
- 使用 `git filter-repo` 或 BFG 清理历史记录；
- 重新生成密钥并写入 `.env`。

---

## 其他

### Q: 项目可以用 CPU 跑吗？

**回答**：可以跑脚本和后期流程，但视频生成会非常慢。建议至少使用 RTX 3090 24GB 或云端 API。

---

> 如果以上没有解决你的问题，欢迎提交 Issue。
