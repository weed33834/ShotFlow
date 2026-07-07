#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# ShotFlow — 双仓库同步脚本
# 用法: bash 08_Automation/sync_repos.sh "提交信息"
#
# 功能:
#   1. git add -A
#   2. git commit -m "提交信息"
#   3. git push origin main      (GitHub:  MS33834/ShotFlow)
#   4. git push gitcode main     (GitCode: badhope/ShotFlow)
#
# 安全提示: 不要在 .git/config 或本脚本中硬编码令牌。
#   令牌从环境变量读取，避免泄露到仓库。
#   使用方法:
#     export GITHUB_TOKEN=ghp_xxx
#     export GITCODE_TOKEN=xxx
#     bash 08_Automation/sync_repos.sh "提交信息"
#   或在 ~/.git-credentials 中配置（权限 600）。
# 仓库地址:
#   GitHub:  https://github.com/MS33834/ShotFlow
#   GitCode: https://gitcode.com/badhope/ShotFlow

set -e

cd "$(dirname "$0")/.."

COMMIT_MSG="${1:-update: 同步更新项目进度}"

# GitHub / GitCode 令牌（从环境变量读取，不硬编码到仓库）
GH_TOKEN="${GITHUB_TOKEN:?请设置 GITHUB_TOKEN 环境变量}"
GC_TOKEN="${GITCODE_TOKEN:?请设置 GITCODE_TOKEN 环境变量}"

# 构建临时 credential store 文件（token 不出现在 URL/命令行中，避免 ps 泄露）
_cred_file=$(mktemp)
printf 'https://MS33834:%s@github.com\n' "$GH_TOKEN" > "$_cred_file"
printf 'https://badhope:%s@gitcode.com\n' "$GC_TOKEN" >> "$_cred_file"
trap 'rm -f "$_cred_file"' EXIT
chmod 600 "$_cred_file"

# 0. 校验必要的 git remote 已配置
for remote in origin gitcode; do
    if ! git remote get-url "$remote" >/dev/null 2>&1; then
        echo "[FAIL] Git remote '$remote' 未配置。"
        echo "       请先添加: git remote add $remote <url>"
        echo "       期望地址:"
        echo "         origin  -> https://github.com/MS33834/ShotFlow.git"
        echo "         gitcode -> https://gitcode.com/badhope/ShotFlow.git"
        exit 1
    fi
done

echo "========================================="
echo "  ShotFlow — 双仓库同步"
echo "========================================="
echo ""

# 1. 检查是否有变更
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "[INFO] 没有变更需要提交"
    # 即使没有变更也尝试推送（可能有本地未推送的 commit）
else
    # 2. 暂存所有变更
    echo "[1/4] 暂存变更..."
    git add -A
    echo "  已暂存文件:"
    git status --short | head -20
    echo ""

    # 3. 提交
    echo "[2/4] 提交..."
    git commit -m "$COMMIT_MSG"
    echo ""
fi

# 4. 推送到 GitHub（用临时 credential store 文件，token 不出现在 URL 中）
echo "[3/4] 推送到 GitHub (MS33834/ShotFlow)..."
if git -c "credential.helper=store --file=$_cred_file" push origin main 2>&1; then
    echo "  [OK] GitHub 推送成功"
else
    echo "  [FAIL] GitHub 推送失败"
    exit 1
fi
echo ""

# 5. 推送到 GitCode
echo "[4/4] 推送到 GitCode (badhope/ShotFlow)..."
if git -c "credential.helper=store --file=$_cred_file" push gitcode main 2>&1; then
    echo "  [OK] GitCode 推送成功"
else
    echo "  [FAIL] GitCode 推送失败"
    exit 1
fi

echo ""
echo "========================================="
echo "  同步完成!"
echo "  GitHub:  https://github.com/MS33834/ShotFlow"
echo "  GitCode: https://gitcode.com/badhope/ShotFlow"
echo "========================================="
