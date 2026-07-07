#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# ShotFlow — ComfyUI 环境部署脚本
# 适用系统: Ubuntu 22.04 LTS / Windows 11 (WSL2)
# GPU: NVIDIA RTX 4090 24GB
# 用法: bash deploy_comfyui.sh

set -e

echo "========================================="
echo "  ShotFlow — ComfyUI 部署脚本"
echo "========================================="

# ==================== 配置区 ====================

INSTALL_DIR="${HOME}/ComfyUI"
PYTHON_VERSION="3.12"
VENV_DIR="${INSTALL_DIR}/venv"

# 模型存放路径
MODELS_DIR="${INSTALL_DIR}/models"
DIFFUSION_DIR="${MODELS_DIR}/diffusion_models"
VAE_DIR="${MODELS_DIR}/vae"
TEXT_ENCODER_DIR="${MODELS_DIR}/text_encoders"
IPADAPTER_DIR="${MODELS_DIR}/ipadapter"

# ==================== 前置检查 ====================

echo ""
echo "[1/8] 检查 NVIDIA GPU..."
if ! command -v nvidia-smi &> /dev/null; then
    echo "[ERROR] 未检测到 nvidia-smi，请先安装 NVIDIA 驱动。"
    exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "[OK] GPU 检测通过"

echo ""
echo "[2/8] 检查 Python ${PYTHON_VERSION}..."
if command -v python${PYTHON_VERSION} &> /dev/null; then
    PYTHON_BIN="python${PYTHON_VERSION}"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
else
    echo "[ERROR] 未找到 Python，请先安装 Python ${PYTHON_VERSION}。"
    exit 1
fi
echo "[OK] Python: $($PYTHON_BIN --version)"

# ==================== 安装 ComfyUI ====================

echo ""
echo "[3/8] 克隆 ComfyUI..."
if [ -d "${INSTALL_DIR}/.git" ]; then
    echo "[SKIP] ComfyUI 已存在，执行 git pull..."
    cd "${INSTALL_DIR}"
    git pull
else
    git clone https://github.com/comfyanonymous/ComfyUI.git "${INSTALL_DIR}"
    cd "${INSTALL_DIR}"
fi
echo "[OK] ComfyUI 代码就绪"

# ==================== 创建虚拟环境 ====================

echo ""
echo "[4/8] 创建 Python 虚拟环境..."
if [ ! -d "${VENV_DIR}" ]; then
    $PYTHON_BIN -m venv "${VENV_DIR}"
fi
# 激活虚拟环境
source "${VENV_DIR}/bin/activate"
echo "[OK] 虚拟环境: ${VENV_DIR}"

# ==================== 安装依赖 ====================

echo ""
echo "[5/8] 升级 pip 并安装 PyTorch (CUDA 12.1)..."
pip install --upgrade pip wheel setuptools
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo "[OK] PyTorch 安装完成"

echo ""
echo "[6/8] 安装 ComfyUI 依赖..."
pip install -r requirements.txt
echo "[OK] ComfyUI 依赖安装完成"

# ==================== 安装 ComfyUI-Manager ====================

echo ""
echo "[7/8] 安装 ComfyUI-Manager..."
MANAGER_DIR="${INSTALL_DIR}/custom_nodes/ComfyUI-Manager"
if [ -d "${MANAGER_DIR}/.git" ]; then
    echo "[SKIP] ComfyUI-Manager 已存在"
else
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git "${MANAGER_DIR}"
fi
echo "[OK] ComfyUI-Manager 安装完成"

# ==================== 创建模型目录 ====================

echo ""
echo "[8/8] 创建模型目录结构..."
mkdir -p "${DIFFUSION_DIR}" "${VAE_DIR}" "${TEXT_ENCODER_DIR}" "${IPADAPTER_DIR}"
echo "[OK] 目录结构:"
echo "  ${DIFFUSION_DIR}"
echo "  ${VAE_DIR}"
echo "  ${TEXT_ENCODER_DIR}"
echo "  ${IPADAPTER_DIR}"

# ==================== 下载模型 ====================

echo ""
echo "========================================="
echo "  模型下载（文件较大，请耐心等待）"
echo "  如网络不稳定，可手动下载后放到对应目录"
echo "========================================="

# --- Flux.1 Kontext [dev] FP8 ---
echo ""
echo "[Download] FLUX.1-Kontext-dev-fp8..."
FLUX_MODEL="${DIFFUSION_DIR}/FLUX.1-Kontext-dev-fp8.safetensors"
if [ ! -f "${FLUX_MODEL}" ]; then
    wget -c "https://huggingface.co/Comfy-Org/flux1-kontext-dev/resolve/main/flux1-kontext-dev-fp8.safetensors" \
        -O "${FLUX_MODEL}"
    echo "[OK] Flux.1 Kontext FP8 下载完成"
else
    echo "[SKIP] Flux.1 Kontext FP8 已存在"
fi

# --- Wan2.2 I2V A14B FP8 (High Noise) ---
echo ""
echo "[Download] Wan2.2 I2V High Noise FP8..."
WAN_HIGH="${DIFFUSION_DIR}/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
if [ ! -f "${WAN_HIGH}" ]; then
    wget -c "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors" \
        -O "${WAN_HIGH}"
    echo "[OK] Wan2.2 High Noise 下载完成"
else
    echo "[SKIP] Wan2.2 High Noise 已存在"
fi

# --- Wan2.2 I2V A14B FP8 (Low Noise) ---
echo ""
echo "[Download] Wan2.2 I2V Low Noise FP8..."
WAN_LOW="${DIFFUSION_DIR}/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
if [ ! -f "${WAN_LOW}" ]; then
    wget -c "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors" \
        -O "${WAN_LOW}"
    echo "[OK] Wan2.2 Low Noise 下载完成"
else
    echo "[SKIP] Wan2.2 Low Noise 已存在"
fi

# --- Wan2.2 VAE ---
echo ""
echo "[Download] Wan2.2 VAE..."
WAN_VAE="${VAE_DIR}/wan2.2_vae.safetensors"
if [ ! -f "${WAN_VAE}" ]; then
    wget -c "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan_2.2_vae.safetensors" \
        -O "${WAN_VAE}"
    echo "[OK] Wan2.2 VAE 下载完成"
else
    echo "[SKIP] Wan2.2 VAE 已存在"
fi

# --- umt5_xxl 文本编码器 ---
echo ""
echo "[Download] umt5_xxl_fp8 文本编码器..."
UMT5_MODEL="${TEXT_ENCODER_DIR}/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
if [ ! -f "${UMT5_MODEL}" ]; then
    wget -c "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
        -O "${UMT5_MODEL}"
    echo "[OK] umt5_xxl 下载完成"
else
    echo "[SKIP] umt5_xxl 已存在"
fi

# ==================== 验证安装 ====================

echo ""
echo "========================================="
echo "  验证安装"
echo "========================================="

echo ""
echo "[Verify] PyTorch CUDA 可用性..."
python -c "
import torch
print(f'PyTorch 版本: {torch.__version__}')
print(f'CUDA 可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
"

echo ""
echo "[Verify] 模型文件检查..."
for f in "${FLUX_MODEL}" "${WAN_HIGH}" "${WAN_LOW}" "${WAN_VAE}" "${UMT5_MODEL}"; do
    if [ -f "$f" ]; then
        SIZE=$(du -h "$f" | cut -f1)
        echo "  [OK] $(basename $f) (${SIZE})"
    else
        echo "  [MISSING] $(basename $f)"
    fi
done

# ==================== 完成 ====================

echo ""
echo "========================================="
echo "  部署完成！"
echo "========================================="
echo ""
echo "启动 ComfyUI:"
echo "  cd ${INSTALL_DIR}"
echo "  source venv/bin/activate"
echo "  python main.py --listen --port 8188"
echo ""
echo "浏览器访问: http://localhost:8188"
echo ""
echo "下一步:"
echo "  1. 在 ComfyUI 中加载 03_Workflows/ 下的 JSON 模板"
echo "  2. 通过 ComfyUI-Manager 安装 IPAdapter-Plus / WanVideoWrapper 等节点"
echo "  3. 参照 04_SOP/sop_shotflow.md 开始生成"
