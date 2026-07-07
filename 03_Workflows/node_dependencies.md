# ComfyUI 节点依赖清单

## Flux_Character_Consistency 所需节点

| 节点/插件 | 用途 | 安装方式 |
|-----------|------|----------|
| ComfyUI 本体 | 工作流平台 | 官方 GitHub |
| ComfyUI-Manager | 节点管理 | 官方 GitHub |
| ComfyUI-IPAdapter-Plus | IPAdapter 面部/风格一致性 | ComfyUI-Manager |
| ComfyUI_PuLID_Flux（可选） | Flux 面部 ID 一致性 | ComfyUI-Manager |
| ComfyUI-Core | 原生加载器/采样器 | 随 ComfyUI 自带 |

## Wan22_Dual_Expert_Video 所需节点

| 节点/插件 | 用途 | 安装方式 |
|-----------|------|----------|
| ComfyUI 本体（≥0.3.46） | 工作流平台 | 官方 GitHub |
| ComfyUI-Manager | 节点管理 | 官方 GitHub |
| ComfyUI-WanVideoWrapper 或原生 Wan 节点 | Wan2.2 视频模型加载与采样 | ComfyUI-Manager |
| ComfyUI-VideoHelperSuite | 视频加载/保存/帧合并 | ComfyUI-Manager |

## 模型下载地址

- FLUX.1-Kontext-dev: https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev
- Wan2.2 ComfyUI Repackaged: https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged
- Wan-AI Wan2.2-I2V-A14B: https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B

## 版本记录

| 日期 | 版本 | 变更说明 |
|------|------|----------|
| 2026-06-23 | 0.1 | 初始节点依赖清单 |
