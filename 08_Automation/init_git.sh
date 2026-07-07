#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# ShotFlow — Git 仓库初始化脚本
# 用法: cd /workspace/ShotFlow && bash 08_Automation/init_git.sh

set -e

echo "========================================="
echo "  ShotFlow — Git 初始化"
echo "========================================="

# 检查 git 是否安装
if ! command -v git &> /dev/null; then
    echo "[ERROR] 未安装 git，请先安装。"
    exit 1
fi

# 初始化仓库
if [ -d ".git" ]; then
    echo "[SKIP] Git 仓库已存在"
else
    git init
    echo "[OK] Git 仓库已初始化"
fi

# 配置 Git LFS（如可用）
if git lfs version &> /dev/null; then
    echo "[OK] Git LFS 已安装"
    git lfs install

    # 追踪大文件类型
    git lfs track "*.png"
    git lfs track "*.jpg"
    git lfs track "*.jpeg"
    git lfs track "*.wav"
    git lfs track "*.mp3"
    git lfs track "*.safetensors"
    git lfs track "*.ckpt"
    git lfs track "*.pt"
    git lfs track "*.bin"
    echo "[OK] LFS 追踪规则已添加"
else
    echo "[WARN] Git LFS 未安装，大文件将无法正常管理"
    echo "       安装: sudo apt install git-lfs"
fi

echo ""
echo "[OK] Git 初始化完成"
echo ""
echo "下一步:"
echo "  git add .gitignore .gitattributes"
echo "  git add ."
echo "  git commit -m 'init: ShotFlow 项目初始化'"
echo "  git tag v0.1.0-init"
